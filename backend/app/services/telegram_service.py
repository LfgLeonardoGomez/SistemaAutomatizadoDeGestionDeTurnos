"""Telegram bot service layer."""

import asyncio
import logging
from collections import defaultdict
from datetime import date, time, timedelta
from typing import Any

from sqlalchemy import and_, func, select

from fastapi.concurrency import run_in_threadpool
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import escape_markdown

from app.config import Settings
from app.dependencies import _get_sessionmaker
from app.schemas.paciente import PacienteCreate
from app.services.availability_service import calcular_disponibilidad
from app.services.paciente_service import crear_o_obtener_paciente
from app.services.turno_service import reservar_turno, confirmar_turno, reprogramar_turno, cancelar_turno, confirmar_asistencia_turno
from app.exceptions import TurnoNoDisponibleError, TurnoYaCanceladoError
logger = logging.getLogger(__name__)

# Session factory for background tasks (overridable in tests)
_session_factory = _get_sessionmaker

# In-memory conversation state (v1)
_conversation_states: dict[int, dict[str, Any]] = {}
_conversation_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


def _get_bot(token: str) -> Bot:
    return Bot(token=token)


def _reset_state() -> None:
    """Reset conversation state (useful for tests)."""
    global _conversation_states, _conversation_locks
    _conversation_states = {}
    _conversation_locks = defaultdict(asyncio.Lock)


def _set_session_factory(factory):
    global _session_factory
    _session_factory = factory


def _reset_session_factory():
    global _session_factory
    _session_factory = _get_sessionmaker


def _get_state(chat_id: int) -> dict[str, Any]:
    if chat_id not in _conversation_states:
        _conversation_states[chat_id] = {
            "estado": "idle",
            "turno_temporal_id": None,
            "datos_paciente": None,
            "fecha_seleccionada": None,
            "turno_a_reprogramar_id": None,
            "nueva_fecha_seleccionada": None,
            "config_paso": None,
            "config_data": None,
        }
    return _conversation_states[chat_id]


def _parse_callback_data(data: str) -> tuple[str, str]:
    """Parse callback_data string like 'fecha:2026-06-15' into (tipo, valor)."""
    if ":" in data:
        tipo, valor = data.split(":", 1)
        return tipo, valor
    return data, ""


def _extract_chat_id(update: dict[str, Any]) -> int | None:
    if "message" in update and update["message"]:
        return update["message"]["chat"]["id"]
    if "callback_query" in update and update["callback_query"]:
        return update["callback_query"]["message"]["chat"]["id"]
    return None


def _extract_text(update: dict[str, Any]) -> str | None:
    if "message" in update and update["message"]:
        return update["message"].get("text")
    return None


def _extract_callback_data(update: dict[str, Any]) -> str | None:
    if "callback_query" in update and update["callback_query"]:
        return update["callback_query"].get("data")
    return None


def _extract_callback_query_id(update: dict[str, Any]) -> str | None:
    if "callback_query" in update and update["callback_query"]:
        return update["callback_query"].get("id")
    return None


# ---------------------------------------------------------------------------
# Message sending helpers
# ---------------------------------------------------------------------------

async def enviar_mensaje(chat_id: int, text: str, bot_token: str, reply_markup: Any | None = None) -> bool:
    """Send a message to a Telegram chat.

    Returns True if Telegram accepted the message, False otherwise.
    Callers decide whether to retry, log, or surface the failure.

    NOTE: ``python-telegram-bot`` v20+ expone los métodos del ``Bot`` como
    ``async`` nativos (NO sync). Por eso se hace ``await bot.send_message(...)``
    directamente, sin ``run_in_threadpool`` (que es para funciones sync y
    rompe el flow con un ``RuntimeWarning: coroutine ... was never awaited``
    si le pasás una coroutine ya construida por error).
    """
    bot = _get_bot(bot_token)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="MarkdownV2",
            reply_markup=reply_markup,
        )
        return True
    except Exception as exc:
        logger.error(f"Error enviando mensaje a {chat_id}: {exc}")
        return False

async def enviar_mensaje_con_log(
    chat_id: int,
    text: str,
    bot_token: str,
    context: str,
    reply_markup: Any | None = None,
) -> bool:
    """Send a Telegram message and log on failure.

    `context` should describe the caller flow (e.g., "config_dias",
    "reprogramar_turno", "dashboard_turnos_hoy") so failures are traceable.
    """
    ok = await enviar_mensaje(chat_id, text, bot_token, reply_markup)
    if not ok:
        logger.error(f"Fallo envío de mensaje a chat_id {chat_id} (contexto: {context})")
    return ok


async def responder_callback_query(callback_query_id: str, bot_token: str) -> None:
    """Answer a callback query to remove the loading spinner."""
    bot = _get_bot(bot_token)
    try:
        # C-24 fix: ``Bot.answer_callback_query`` es async nativo en
        # python-telegram-bot v20+ — ``await`` directo, sin ``run_in_threadpool``.
        await bot.answer_callback_query(callback_query_id)
    except Exception as exc:
        logger.error(f"Error respondiendo callback query {callback_query_id}: {exc}")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

MAX_MESSAGE_LENGTH = 4096


def escape_markdown_v2(text: str) -> str:
    return escape_markdown(text, version=2)


def split_message(text: str) -> list[str]:
    """Split a long message into chunks under MAX_MESSAGE_LENGTH."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]
    chunks = []
    while text:
        chunk = text[:MAX_MESSAGE_LENGTH]
        text = text[MAX_MESSAGE_LENGTH:]
        chunks.append(chunk)
    return chunks


def format_fechas_keyboard(fechas: list[str]) -> InlineKeyboardMarkup:
    """Build inline keyboard for date selection."""
    buttons = [
        [InlineKeyboardButton(fecha, callback_data=f"fecha:{fecha}")]
        for fecha in fechas
    ]
    buttons.append([InlineKeyboardButton("Cancelar", callback_data="cancelar_accion")])
    return InlineKeyboardMarkup(buttons)


def format_horas_keyboard(horas: list[str]) -> InlineKeyboardMarkup:
    """Build inline keyboard for time selection."""
    buttons = [
        [InlineKeyboardButton(hora, callback_data=f"hora:{hora}")]
        for hora in horas
    ]
    buttons.append([InlineKeyboardButton("Cancelar", callback_data="cancelar_accion")])
    return InlineKeyboardMarkup(buttons)


def format_confirmacion_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard for confirmation."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Confirmar", callback_data="confirmar_datos")],
        [InlineKeyboardButton("Cancelar", callback_data="cancelar_accion")],
    ])


def format_disponibilidad(fecha: str, slots: list[dict[str, Any]]) -> str:
    """Format availability message with MarkdownV2."""
    lines = [f"*Fecha:* {escape_markdown_v2(fecha)}", "*Horarios disponibles:*", ""]
    for slot in slots:
        lines.append(f"• {escape_markdown_v2(slot['hora_inicio'])} \- {escape_markdown_v2(slot['hora_fin'])}")
    return "\n".join(lines)


def format_confirmacion(turno: dict[str, Any], paciente: dict[str, Any]) -> str:
    """Format confirmation message."""
    lines = [
        "✅ *Turno confirmado*",
        "",
        f"*Fecha:* {escape_markdown_v2(str(turno.get('fecha', '')))}",
        f"*Hora:* {escape_markdown_v2(str(turno.get('hora_inicio', '')))}",
        f"*Paciente:* {escape_markdown_v2(paciente.get('nombre', ''))} {escape_markdown_v2(paciente.get('apellido', ''))}",
    ]
    return "\n".join(lines)


def format_error(mensaje: str) -> str:
    return f"❌ *Error*\n\n{escape_markdown_v2(mensaje)}"


def format_turnos_hoy(turnos: list[dict[str, Any]]) -> str:
    """Format today's confirmed appointments with MarkdownV2."""
    if not turnos:
        return "📅 *Turnos de hoy*\n\n_No hay turnos confirmados para hoy_"
    lines = ["📅 *Turnos de hoy*", ""]
    for t in turnos:
        hora = escape_markdown_v2(str(t.get("hora_inicio", "")))
        paciente = t.get("paciente", {}) or {}
        nombre = escape_markdown_v2(paciente.get("nombre", ""))
        apellido = escape_markdown_v2(paciente.get("apellido", ""))
        lines.append(f"• {hora} \- {nombre} {apellido}")
    return "\n".join(lines)


def format_metricas(metricas: dict[str, Any]) -> str:
    """Format metrics summary with MarkdownV2."""
    turnos_hoy = metricas.get("turnos_hoy", 0)
    tasa_conf = metricas.get("tasa_confirmacion_30d", 0.0)
    tasa_canc = metricas.get("tasa_cancelacion_30d", 0.0)
    conf_pct = int(tasa_conf * 100)
    canc_pct = int(tasa_canc * 100)
    lines = [
        "📊 *Métricas*",
        "",
        f"*Turnos hoy:* {turnos_hoy}",
        f"*Confirmación 30d:* {conf_pct}%",
        f"*Cancelación 30d:* {canc_pct}%",
    ]
    return "\n".join(lines)


def format_config_summary(config: dict[str, Any]) -> str:
    """Format pending configuration changes with MarkdownV2."""
    dias = ", ".join(config.get("dias_atencion", []))
    lines = [
        "⚙️ *Resumen de cambios*",
        "",
        f"*Inicio:* {escape_markdown_v2(config.get('horario_inicio', ''))}",
        f"*Fin:* {escape_markdown_v2(config.get('horario_fin', ''))}",
        f"*Días:* {escape_markdown_v2(dias)}",
        f"*Duración:* {config.get('duracion_turno', 0)} min",
        "",
        "¿Confirmás los cambios?",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Config wizard keyboards
# ---------------------------------------------------------------------------

_DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def format_dias_keyboard(dias_seleccionados: list[str]) -> InlineKeyboardMarkup:
    """Build inline keyboard for day selection with toggles."""
    buttons: list[list[InlineKeyboardButton]] = []
    for dia in _DIAS_SEMANA:
        label = f"{dia} ✅" if dia in dias_seleccionados else dia
        buttons.append([InlineKeyboardButton(label, callback_data=f"config:dia:{dia}")])
    buttons.append([InlineKeyboardButton("Confirmar días", callback_data="config:confirmar_dias")])
    return InlineKeyboardMarkup(buttons)


def format_config_confirm_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard for config confirmation."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Confirmar", callback_data="config:confirmar")],
        [InlineKeyboardButton("Cancelar", callback_data="config:cancelar")],
    ])


# ---------------------------------------------------------------------------
# Professional dashboard actions
# ---------------------------------------------------------------------------

async def accion_turnos_hoy(db, chat_id: int, profesional_id: int) -> str:
    """Query today's confirmed appointments and format response."""
    from app.models.turno import Turno
    hoy = date.today()
    result = await db.execute(
        select(Turno)
        .where(Turno.fecha == hoy, Turno.estado == "CONFIRMADO", Turno.profesional_id == profesional_id)
        .order_by(Turno.hora_inicio)
    )
    turnos = result.scalars().all()
    turnos_data = []
    for t in turnos:
        p = t.paciente
        turnos_data.append({
            "hora_inicio": t.hora_inicio,
            "paciente": {
                "nombre": p.nombre if p else "",
                "apellido": p.apellido if p else "",
            },
        })
    return format_turnos_hoy(turnos_data)


async def accion_metricas(db, chat_id: int, profesional_id: int) -> str:
    """Query metrics and format response."""
    from app.models.turno import Turno
    hoy = date.today()
    inicio_30d = hoy - timedelta(days=30)

    result_hoy = await db.execute(
        select(func.count()).where(
            and_(Turno.fecha == hoy, Turno.estado == "CONFIRMADO", Turno.profesional_id == profesional_id)
        )
    )
    turnos_hoy = result_hoy.scalar_one() or 0

    result_total = await db.execute(
        select(func.count()).where(
            and_(Turno.fecha >= inicio_30d, Turno.fecha <= hoy, Turno.profesional_id == profesional_id)
        )
    )
    total_30d = result_total.scalar_one() or 0

    if total_30d == 0:
        metricas = {"turnos_hoy": turnos_hoy, "tasa_confirmacion_30d": 0.0, "tasa_cancelacion_30d": 0.0}
        return format_metricas(metricas)

    result_conf = await db.execute(
        select(func.count()).where(
            and_(Turno.fecha >= inicio_30d, Turno.fecha <= hoy, Turno.estado == "CONFIRMADO", Turno.profesional_id == profesional_id)
        )
    )
    confirmados_30d = result_conf.scalar_one() or 0

    result_canc = await db.execute(
        select(func.count()).where(
            and_(Turno.fecha >= inicio_30d, Turno.fecha <= hoy, Turno.estado == "CANCELADO", Turno.profesional_id == profesional_id)
        )
    )
    cancelados_30d = result_canc.scalar_one() or 0

    metricas = {
        "turnos_hoy": turnos_hoy,
        "tasa_confirmacion_30d": round(confirmados_30d / total_30d, 2),
        "tasa_cancelacion_30d": round(cancelados_30d / total_30d, 2),
    }
    return format_metricas(metricas)


async def accion_configurar(db, chat_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
    """Start the configuration wizard."""
    state = _get_state(chat_id)
    state["estado"] = "config_esperando_hora_inicio"
    state["config_paso"] = "hora_inicio"
    state["config_data"] = {}
    texto = "⚙️ *Configurar agenda*\n\nIngresá el horario de inicio en formato HH:MM"
    return texto, None


async def _handle_config_callback(db, chat_id: int, valor: str, state: dict[str, Any], bot_token: str, profesional_id: int) -> None:
    """Handle configuration wizard inline callbacks."""
    if valor.startswith("dia:"):
        dia = valor.split(":", 1)[1]
        dias = state.get("config_data", {}).get("dias_atencion", [])
        if dia in dias:
            dias.remove(dia)
        else:
            dias.append(dia)
        state["config_data"]["dias_atencion"] = dias
        keyboard = format_dias_keyboard(dias)
        await enviar_mensaje_con_log(chat_id, "Seleccioná los días de atención:", bot_token, "config:dias_seleccion", keyboard)
        return

    if valor == "confirmar_dias":
        state["estado"] = "config_esperando_duracion"
        await enviar_mensaje_con_log(chat_id, "Ingresá la duración del turno en minutos \\(número positivo\\)", bot_token, "config:duracion")
        return

    if valor == "confirmar":
        await _persist_config(db, chat_id, state, bot_token, profesional_id)
        return

    if valor == "cancelar":
        state["estado"] = "idle"
        state["config_paso"] = None
        state["config_data"] = None
        await enviar_mensaje_con_log(chat_id, "Configuración cancelada\. No se guardaron cambios\.", bot_token, "config:cancelar")
        return


async def _persist_config(db, chat_id: int, state: dict[str, Any], bot_token: str, profesional_id: int) -> None:
    """Persist configuration changes to the database."""
    from app.models.profesional import Profesional

    config = state.get("config_data", {})
    result = await db.execute(select(Profesional).where(Profesional.id == profesional_id))
    profesional = result.scalar_one_or_none()
    if profesional is None:
        await enviar_mensaje_con_log(chat_id, format_error("No se encontró el profesional"), bot_token, "config:profesional_no_encontrado")
        return

    if config.get("horario_inicio") is not None:
        profesional.horario_inicio = config["horario_inicio"]
    if config.get("horario_fin") is not None:
        profesional.horario_fin = config["horario_fin"]
    if config.get("dias_atencion") is not None:
        profesional.dias_atencion = config["dias_atencion"]
    if config.get("duracion_turno") is not None:
        profesional.duracion_turno = config["duracion_turno"]

    await db.commit()
    await db.refresh(profesional)

    state["estado"] = "idle"
    state["config_paso"] = None
    state["config_data"] = None
    await enviar_mensaje_con_log(chat_id, "✅ *Configuración guardada*\n\nLos cambios fueron aplicados exitosamente\.", bot_token, "config:guardada")


# ---------------------------------------------------------------------------
# Business actions
# ---------------------------------------------------------------------------

async def mostrar_disponibilidad(
    db, profesional_id: int, fecha: date | None = None
) -> tuple[str, InlineKeyboardMarkup | None]:
    """Query availability and format response."""
    from app.services.turno_service import consultar_disponibilidad

    if fecha is None:
        # For v1, show a few upcoming dates
        hoy = date.today()
        fechas = [(hoy + __import__("datetime").timedelta(days=i)).isoformat() for i in range(1, 8)]
        texto = "*Seleccioná una fecha:*"
        keyboard = format_fechas_keyboard(fechas)
        return texto, keyboard

    slots = await consultar_disponibilidad(db, profesional_id, fecha)
    if not slots:
        return f"No hay horarios disponibles para el {escape_markdown_v2(str(fecha))}", None

    texto = format_disponibilidad(str(fecha), slots)
    horas = [s["hora_inicio"] for s in slots]
    keyboard = format_horas_keyboard(horas)
    return texto, keyboard


async def accion_reservar_temporal(db, chat_id: int, fecha: str, hora: str, profesional_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
    """Create a temporary reservation for the selected slot."""
    try:
        fecha_dt = date.fromisoformat(fecha)
        hora_dt = time.fromisoformat(hora)
        # C-23 TAREA 6: propagar el chat_id del update de Telegram como
        # destinatario TELEGRAM del turno. El bot conoce el chat_id del
        # mensaje que disparó la reserva; sin pasarlo, el recordatorio del
        # turno queda sin destinatario.
        turno = await reservar_turno(
            db,
            profesional_id=profesional_id,
            fecha=fecha_dt,
            hora_inicio=hora_dt,
            telegram_chat_id=str(chat_id),
        )
        state = _get_state(chat_id)
        state["turno_temporal_id"] = turno.id
        texto = (
            f"Reserva temporal creada para el {escape_markdown_v2(fecha)} a las {escape_markdown_v2(hora)}\n\n"
            "*Ingresá tus datos:*\nNombre, Apellido, DNI, Teléfono \(separados por comas\)"
        )
        return texto, None
    except Exception as exc:
        logger.exception("Error reservando turno temporal")
        return format_error(str(exc)), None


async def accion_confirmar_turno(db, chat_id: int, datos: dict[str, str], profesional_id: int) -> str:
    """Confirm the temporary reservation with patient data."""
    state = _get_state(chat_id)
    turno_id = state.get("turno_temporal_id")
    if turno_id is None:
        return format_error("No hay una reserva para confirmar")

    # C-23 TAREA 7.5: garantizar que el chat_id del update de Telegram
    # viaje en paciente_data para que ``confirmar_turno`` registre el
    # destinatario TELEGRAM del turno. El parser de ``esperando_datos`` ya
    # lo incluye, pero este fallback cubre el caso de un ``datos`` provisto
    # por otro path (o por un test que llama a ``accion_confirmar_turno``
    # directamente).
    datos = dict(datos)  # copia defensiva: no mutar el state
    datos.setdefault("telegram_chat_id", str(chat_id))

    try:
        turno = await confirmar_turno(db, profesional_id=profesional_id, turno_id=turno_id, paciente_data=datos)
        state["estado"] = "idle"
        state["turno_temporal_id"] = None
        state["datos_paciente"] = None
        state["fecha_seleccionada"] = None
        return format_confirmacion(
            turno={"fecha": turno.fecha, "hora_inicio": turno.hora_inicio},
            paciente=datos,
        )
    except Exception as exc:
        logger.exception("Error confirmando turno")
        return format_error(str(exc))


async def accion_cancelar_turno(db, chat_id: int) -> str:
    """Cancel the current flow and reset state."""
    state = _get_state(chat_id)
    state["estado"] = "idle"
    state["turno_temporal_id"] = None
    state["datos_paciente"] = None
    state["fecha_seleccionada"] = None
    return "Operación cancelada\. Volvé a empezar con /start"


async def accion_iniciar_reprogramacion(db, chat_id: int, turno_id: int, profesional_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
    """Inicia el flujo de reprogramación guardando el turno_id y mostrando fechas."""
    state = _get_state(chat_id)
    state["estado"] = "reprogramando_esperando_fecha"
    state["turno_a_reprogramar_id"] = turno_id
    texto, keyboard = await mostrar_disponibilidad(db, profesional_id)
    return texto, keyboard


async def accion_reprogramar_turno(db, chat_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
    """Placeholder for reschedule flow triggered by text message."""
    return "Reprogramar turno \(próximamente\)", None


async def notificar_expiracion(chat_id: int, turno_id: int) -> str:
    """Format expiration notification."""
    return f"⚠️ Tu reserva temporal \(turno {turno_id}\) ha expirado\. Volvé a intentar con /start"


def format_recordatorio_mensaje(turno: dict, paciente: dict) -> str:
    """Format reminder message with MarkdownV2."""
    fecha = escape_markdown_v2(str(turno.get("fecha", "")))
    hora = escape_markdown_v2(str(turno.get("hora_inicio", "")))
    nombre = escape_markdown_v2(paciente.get("nombre", ""))
    apellido = escape_markdown_v2(paciente.get("apellido", ""))
    return (
        f"📅 *Recordatorio de turno*\n\n"
        f"*Fecha:* {fecha}\n"
        f"*Hora:* {hora}\n"
        f"*Paciente:* {nombre} {apellido}\n\n"
        f"¿Confirmás tu asistencia?"
    )


def format_recordatorio_keyboard(turno_id: int) -> InlineKeyboardMarkup:
    """Build inline keyboard for reminder actions."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Confirmar asistencia", callback_data=f"reminder:confirmar:{turno_id}")],
        [InlineKeyboardButton("Cancelar", callback_data=f"reminder:cancelar:{turno_id}")],
        [InlineKeyboardButton("Reprogramar", callback_data=f"reminder:reprogramar:{turno_id}")],
    ])


def format_lista_espera_keyboard(turno_id: int) -> InlineKeyboardMarkup:
    """Build inline keyboard for waiting list accept/reject."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Aceptar", callback_data=f"lista_espera:aceptar:{turno_id}"),
            InlineKeyboardButton("Rechazar", callback_data=f"lista_espera:rechazar:{turno_id}"),
        ],
    ])


def format_lista_espera_mensaje(turno: Any) -> str:
    """Format waiting list offer message with MarkdownV2 escape."""
    fecha = escape_markdown_v2(str(turno.fecha))
    hora = escape_markdown_v2(str(turno.hora_inicio))
    return (
        f"📢 *Turno liberado*\n\n"
        f"*Fecha:* {fecha}\n"
        f"*Hora:* {hora}\n\n"
        f"¿Querés tomarlo?"
    )


async def enviar_notificacion_lista_espera(chat_id: str, turno: Any, bot_token: str) -> bool:
    """Send waiting list offer notification with Accept/Reject inline keyboard."""
    texto = format_lista_espera_mensaje(turno)
    keyboard = format_lista_espera_keyboard(turno.id)
    ok = await enviar_mensaje(int(chat_id), texto, bot_token, keyboard)
    if not ok:
        logger.error(f"Error enviando notificación de lista de espera a {chat_id}")
    return ok


async def accion_aceptar_lista_espera(db, chat_id: int, turno_id: int, profesional_id: int) -> str:
    """Accept a waiting-list offered turno."""
    from app.services.lista_espera_service import aceptar_turno_lista_espera
    from sqlalchemy import select
    from app.models.lista_de_espera import ListaDeEspera

    # Find the waiting-list record for this turno and chat
    result = await db.execute(
        select(ListaDeEspera).where(
            ListaDeEspera.turno_ofrecido_id == turno_id,
            ListaDeEspera.notificado == True,
            ListaDeEspera.profesional_id == profesional_id,
        )
    )
    registro = result.scalar_one_or_none()
    if registro is None:
        return format_error("No se encontró una oferta de lista de espera activa para este turno")

    try:
        confirmado = await aceptar_turno_lista_espera(db, profesional_id=profesional_id, lista_espera_id=registro.id)
        texto = (
            f"✅ *Turno confirmado*\n\n"
            f"*Fecha:* {escape_markdown_v2(str(confirmado.fecha))}\n"
            f"*Hora:* {escape_markdown_v2(str(confirmado.hora_inicio))}"
        )
        return texto
    except Exception as exc:
        logger.exception("Error aceptando turno de lista de espera")
        return format_error(str(exc))


async def accion_rechazar_lista_espera(db, chat_id: int, turno_id: int, profesional_id: int) -> str:
    """Reject a waiting-list offered turno."""
    from app.services.lista_espera_service import rechazar_turno_lista_espera
    from sqlalchemy import select
    from app.models.lista_de_espera import ListaDeEspera

    result = await db.execute(
        select(ListaDeEspera).where(
            ListaDeEspera.turno_ofrecido_id == turno_id,
            ListaDeEspera.notificado == True,
            ListaDeEspera.profesional_id == profesional_id,
        )
    )
    registro = result.scalar_one_or_none()
    if registro is None:
        return format_error("No se encontró una oferta de lista de espera activa para este turno")

    try:
        await rechazar_turno_lista_espera(db, profesional_id=profesional_id, lista_espera_id=registro.id, turno_id=turno_id)
        return "Turno rechazado\. Si hay otro paciente en lista de espera se le notificará\."
    except Exception as exc:
        logger.exception("Error rechazando turno de lista de espera")
        return format_error(str(exc))


# ---------------------------------------------------------------------------
# Background task processor
# ---------------------------------------------------------------------------

async def procesar_update_async(update: dict, profesional_id: int) -> None:
    """Crea una sesión de DB y procesa el update de Telegram en background."""
    session_maker = _session_factory()
    async with session_maker() as db:
        try:
            await procesar_mensaje(db, update, profesional_id)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------

async def procesar_mensaje(db, update: dict[str, Any], profesional_id: int) -> None:
    """Parse a Telegram update and route to the appropriate action."""
    chat_id = _extract_chat_id(update)
    if chat_id is None:
        logger.warning("Update sin chat_id: %s", update)
        return

    # Get bot token from profesional
    from app.models.profesional import Profesional
    result = await db.execute(select(Profesional).where(Profesional.id == profesional_id))
    profesional = result.scalar_one_or_none()
    if profesional is None or not profesional.telegram_bot_token:
        logger.error(f"Profesional {profesional_id} no tiene telegram_bot_token")
        return
    bot_token = profesional.telegram_bot_token

    async with _conversation_locks[chat_id]:
        state = _get_state(chat_id)
        text = _extract_text(update)
        callback_data = _extract_callback_data(update)
        callback_query_id = _extract_callback_query_id(update)

        if callback_query_id:
            await responder_callback_query(callback_query_id, bot_token)

        if callback_data:
            tipo, valor = _parse_callback_data(callback_data)

            if tipo == "fecha":
                if state["estado"] == "reprogramando_esperando_fecha":
                    state["estado"] = "reprogramando_esperando_hora"
                    state["nueva_fecha_seleccionada"] = valor
                    texto, keyboard = await mostrar_disponibilidad(db, profesional_id, fecha=date.fromisoformat(valor))
                    await enviar_mensaje_con_log(chat_id, texto, bot_token, "reprogramar:seleccion_fecha", keyboard)
                    return
                # Default booking flow
                state["estado"] = "esperando_hora"
                state["fecha_seleccionada"] = valor
                texto, keyboard = await mostrar_disponibilidad(db, profesional_id, fecha=date.fromisoformat(valor))
                await enviar_mensaje_con_log(chat_id, texto, bot_token, "reserva:seleccion_fecha", keyboard)
                return

            if tipo == "hora":
                if state["estado"] == "reprogramando_esperando_hora":
                    turno_id = state.get("turno_a_reprogramar_id")
                    nueva_fecha = state.get("nueva_fecha_seleccionada")
                    if turno_id and nueva_fecha:
                        try:
                            nuevo_turno = await reprogramar_turno(
                                db,
                                profesional_id=profesional_id,
                                turno_id=turno_id,
                                nueva_fecha=date.fromisoformat(nueva_fecha),
                                nueva_hora_inicio=time.fromisoformat(valor),
                            )
                            texto = (
                                f"✅ *Turno reprogramado*\n\n"
                                f"*Fecha:* {escape_markdown_v2(str(nuevo_turno.fecha))}\n"
                                f"*Hora:* {escape_markdown_v2(str(nuevo_turno.hora_inicio))}"
                            )
                            state["estado"] = "idle"
                            state["turno_a_reprogramar_id"] = None
                            state["nueva_fecha_seleccionada"] = None
                            await enviar_mensaje_con_log(chat_id, texto, bot_token, "reprogramar:exitoso")
                        except TurnoNoDisponibleError as exc:
                            texto = format_error(f"{exc.message}\\. Seleccioná otra fecha")
                            state["estado"] = "reprogramando_esperando_fecha"
                            await enviar_mensaje_con_log(chat_id, texto, bot_token, "reprogramar:error_no_disponible")
                        except TurnoYaCanceladoError as exc:
                            texto = format_error(f"{exc.message}\\. No se puede reprogramar")
                            state["estado"] = "idle"
                            state["turno_a_reprogramar_id"] = None
                            state["nueva_fecha_seleccionada"] = None
                            await enviar_mensaje_con_log(chat_id, texto, bot_token, "reprogramar:error_ya_cancelado")
                        except Exception as exc:
                            logger.exception("Error reprogramando turno desde Telegram")
                            texto = format_error(f"Error inesperado: {exc}")
                            state["estado"] = "idle"
                            state["turno_a_reprogramar_id"] = None
                            state["nueva_fecha_seleccionada"] = None
                            await enviar_mensaje_con_log(chat_id, texto, bot_token, "reprogramar:error_inesperado")
                    return
                # Default booking flow
                state["estado"] = "esperando_datos"
                fecha = state.get("fecha_seleccionada")
                if fecha:
                    texto, keyboard = await accion_reservar_temporal(db, chat_id, fecha, valor, profesional_id)
                    await enviar_mensaje_con_log(chat_id, texto, bot_token, "reserva:seleccion_hora", keyboard)
                return

            if callback_data == "confirmar_datos":
                state["estado"] = "esperando_confirmacion"
                # In a real flow, datos_paciente would have been collected earlier
                datos = state.get("datos_paciente") or {"nombre": "", "apellido": "", "dni": "", "telefono": ""}
                # C-23 TAREA 7.5: garantizar que el chat_id del update
                # original viaje en paciente_data para que ``confirmar_turno``
                # registre el destinatario TELEGRAM del turno. El parser del
                # paso ``esperando_datos`` ya lo incluye, pero este fallback
                # cubre el edge case de un ``datos_paciente`` provisto por
                # otro path.
                datos.setdefault("telegram_chat_id", str(chat_id))
                texto = await accion_confirmar_turno(db, chat_id, datos, profesional_id)
                await enviar_mensaje_con_log(chat_id, texto, bot_token, "confirmacion:datos")
                return

            if callback_data == "cancelar_accion":
                texto = await accion_cancelar_turno(db, chat_id)
                # Also clear reprogramacion state
                state["turno_a_reprogramar_id"] = None
                state["nueva_fecha_seleccionada"] = None
                await enviar_mensaje_con_log(chat_id, texto, bot_token, "reserva:cancelar")
                return

            if tipo == "reprogramar":
                turno_id = int(valor)
                texto, keyboard = await accion_iniciar_reprogramacion(db, chat_id, turno_id, profesional_id)
                await enviar_mensaje_con_log(chat_id, texto, bot_token, "reprogramar:inicio", keyboard)
                return

            if tipo == "lista_espera":
                subtipo, turno_id_str = valor.split(":", 1)
                turno_id = int(turno_id_str)
                if subtipo == "aceptar":
                    texto = await accion_aceptar_lista_espera(db, chat_id, turno_id, profesional_id)
                elif subtipo == "rechazar":
                    texto = await accion_rechazar_lista_espera(db, chat_id, turno_id, profesional_id)
                else:
                    texto = format_error("Acción no reconocida")
                await enviar_mensaje_con_log(chat_id, texto, bot_token, "lista_espera:respuesta")
                return

            if tipo == "reminder":
                subtipo, turno_id_str = valor.split(":", 1)
                turno_id = int(turno_id_str)
                if subtipo == "confirmar":
                    try:
                        from app.models.turno import Turno as TurnoModel
                        result = await db.execute(select(TurnoModel).where(TurnoModel.id == turno_id))
                        turno = result.scalar_one_or_none()
                        if turno is None:
                            raise TurnoNoEncontradoError()
                        await confirmar_asistencia_turno(db, profesional_id=turno.profesional_id, turno_id=turno_id)
                        texto = (
                            f"✅ *Asistencia confirmada*\n\n"
                            f"Gracias por confirmar\. Te esperamos en tu turno\."
                        )
                    except Exception as exc:
                        logger.exception("Error confirmando asistencia desde recordatorio")
                        texto = format_error(str(exc))
                elif subtipo == "cancelar":
                    try:
                        from app.models.turno import Turno as TurnoModel
                        result = await db.execute(select(TurnoModel).where(TurnoModel.id == turno_id))
                        turno = result.scalar_one_or_none()
                        if turno is None:
                            raise TurnoNoEncontradoError()
                        turno_cancelado = await cancelar_turno(db, profesional_id=turno.profesional_id, turno_id=turno_id)
                        texto = (
                            f"❌ *Turno cancelado*\n\n"
                            f"Fecha: {escape_markdown_v2(str(turno_cancelado.fecha))}\n"
                            f"Hora: {escape_markdown_v2(str(turno_cancelado.hora_inicio))}"
                        )
                    except Exception as exc:
                        logger.exception("Error cancelando turno desde recordatorio")
                        texto = format_error(str(exc))
                elif subtipo == "reprogramar":
                    texto, keyboard = await accion_iniciar_reprogramacion(db, chat_id, turno_id, profesional_id)
                    if keyboard:
                        await enviar_mensaje_con_log(chat_id, texto, bot_token, "recordatorio:reprogramar", keyboard)
                        return
                else:
                    texto = format_error("Acción no reconocida")
                await enviar_mensaje_con_log(chat_id, texto, bot_token, "recordatorio:accion_no_reconocida")
                return

            if tipo == "config":
                await _handle_config_callback(db, chat_id, valor, state, bot_token, profesional_id)
                return

        if text:
            text_lower = text.strip().lower()

            if text_lower in ("/start", "quiero un turno"):
                state["estado"] = "esperando_fecha"
                texto, keyboard = await mostrar_disponibilidad(db, profesional_id)
                await enviar_mensaje_con_log(chat_id, texto, bot_token, "reserva:inicio", keyboard)
                return

            if text_lower == "cancelar":
                if state["estado"].startswith("config_"):
                    state["estado"] = "idle"
                    state["config_paso"] = None
                    state["config_data"] = None
                    await enviar_mensaje_con_log(chat_id, "Configuración cancelada\. No se guardaron cambios\.", bot_token, "config:cancelar")
                else:
                    texto = await accion_cancelar_turno(db, chat_id)
                    await enviar_mensaje_con_log(chat_id, texto, bot_token, "reserva:cancelar")
                return

            if text_lower == "reprogramar":
                texto, keyboard = await accion_reprogramar_turno(db, chat_id)
                await enviar_mensaje_con_log(chat_id, texto, bot_token, "reprogramar:texto", keyboard)
                return

            if text_lower == "/turnos_hoy":
                texto = await accion_turnos_hoy(db, chat_id, profesional_id)
                await enviar_mensaje_con_log(chat_id, texto, bot_token, "dashboard:turnos_hoy")
                return

            if text_lower == "/metricas":
                texto = await accion_metricas(db, chat_id, profesional_id)
                await enviar_mensaje_con_log(chat_id, texto, bot_token, "dashboard:metricas")
                return

            if text_lower == "/configurar":
                texto, keyboard = await accion_configurar(db, chat_id)
                await enviar_mensaje_con_log(chat_id, texto, bot_token, "config:inicio", keyboard)
                return

            # Fallback: unrecognized text
            if state["estado"] == "idle":
                await enviar_mensaje_con_log(
                    chat_id,
                    "No entendí tu mensaje\n\nComandos disponibles:\n• /start \- Quiero un turno\n• Cancelar\n• Reprogramar",
                    bot_token,
                    "fallback:mensaje_no_entendido",
                )
                return

            # If in a flow expecting data, try to parse as patient data
            if state["estado"] == "esperando_datos":
                # Simple CSV parsing: nombre, apellido, dni, telefono
                parts = [p.strip() for p in text.split(",")]
                if len(parts) >= 4:
                    # C-23 TAREA 7.5: el chat_id del update de Telegram que
                    # disparó la reserva/confirmación viaja como
                    # ``telegram_chat_id`` en el ``paciente_data`` que
                    # ``confirmar_turno`` recibe. Esto permite que el turno
                    # registre el destinatario TELEGRAM a nivel de TURNO (no
                    # de paciente), evitando el bug de cross-contamination
                    # entre chats del mismo DNI.
                    state["datos_paciente"] = {
                        "nombre": parts[0],
                        "apellido": parts[1],
                        "dni": parts[2],
                        "telefono": parts[3],
                        "telegram_chat_id": str(chat_id),
                    }
                    state["estado"] = "esperando_confirmacion"
                    datos = state["datos_paciente"]
                    texto = (
                        f"*Datos ingresados:*\n"
                        f"Nombre: {escape_markdown_v2(datos['nombre'])}\n"
                        f"Apellido: {escape_markdown_v2(datos['apellido'])}\n"
                        f"DNI: {escape_markdown_v2(datos['dni'])}\n"
                        f"Teléfono: {escape_markdown_v2(datos['telefono'])}\n\n"
                        "¿Confirmás?"
                    )
                    await enviar_mensaje_con_log(chat_id, texto, bot_token, "confirmacion:datos_ingresados", format_confirmacion_keyboard())
                else:
                    await enviar_mensaje_con_log(
                        chat_id,
                        "Formato incorrecto\n\nIngresá: Nombre, Apellido, DNI, Teléfono",
                        bot_token,
                        "reserva:datos_invalidos",
                    )
                return

            if state["estado"] == "config_esperando_hora_inicio":
                try:
                    time.fromisoformat(text.strip())
                    state["config_data"]["horario_inicio"] = text.strip()
                    state["estado"] = "config_esperando_hora_fin"
                    await enviar_mensaje_con_log(chat_id, "Ingresá el horario de fin en formato HH:MM", bot_token, "config:hora_inicio_valida")
                except ValueError:
                    await enviar_mensaje_con_log(chat_id, "❌ Horario inválido\. Ingresá en formato HH:MM", bot_token, "config:hora_inicio_invalida")
                return

            if state["estado"] == "config_esperando_hora_fin":
                try:
                    hora_fin = time.fromisoformat(text.strip())
                    hora_inicio = time.fromisoformat(state["config_data"]["horario_inicio"])
                    if hora_fin <= hora_inicio:
                        await enviar_mensaje_con_log(chat_id, "❌ El horario de fin debe ser posterior al de inicio\. Ingresá otro horario:", bot_token, "config:hora_fin_invalida")
                        return
                    state["config_data"]["horario_fin"] = text.strip()
                    state["estado"] = "config_esperando_dias"
                    keyboard = format_dias_keyboard(state["config_data"].get("dias_atencion", []))
                    await enviar_mensaje_con_log(chat_id, "Seleccioná los días de atención:", bot_token, "config:dias_seleccion", keyboard)
                except ValueError:
                    await enviar_mensaje_con_log(chat_id, "❌ Horario inválido\. Ingresá en formato HH:MM", bot_token, "config:hora_fin_invalida")
                return

            if state["estado"] == "config_esperando_duracion":
                try:
                    duracion = int(text.strip())
                    if duracion <= 0:
                        await enviar_mensaje_con_log(chat_id, "❌ La duración debe ser un número positivo\. Ingresá otro valor:", bot_token, "config:duracion_invalida")
                        return
                    state["config_data"]["duracion_turno"] = duracion
                    state["estado"] = "config_confirmar"
                    texto = format_config_summary(state["config_data"])
                    keyboard = format_config_confirm_keyboard()
                    await enviar_mensaje_con_log(chat_id, texto, bot_token, "config:duracion_valida", keyboard)
                except ValueError:
                    await enviar_mensaje_con_log(chat_id, "❌ Valor inválido\. Ingresá un número entero positivo:", bot_token, "config:duracion_invalida")
                return

        logger.info("Unhandled update for chat_id %s: %s", chat_id, update)
