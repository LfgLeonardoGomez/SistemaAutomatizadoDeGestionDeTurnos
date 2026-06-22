"""Telegram bot service layer."""

import asyncio
import logging
from collections import defaultdict
from datetime import date, time
from typing import Any

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

# Bot instance (lazy initialized)
_bot: Bot | None = None


def _get_bot(settings: Settings | None = None) -> Bot:
    global _bot
    if _bot is None:
        cfg = settings or Settings()
        _bot = Bot(token=cfg.telegram_bot_token)
    return _bot


def _reset_bot() -> None:
    """Reset the bot instance (useful for tests)."""
    global _bot
    _bot = None


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

async def enviar_mensaje(chat_id: int, text: str, reply_markup: Any | None = None) -> None:
    """Send a message to a Telegram chat via run_in_threadpool."""
    bot = _get_bot()
    try:
        await run_in_threadpool(
            bot.send_message,
            chat_id=chat_id,
            text=text,
            parse_mode="MarkdownV2",
            reply_markup=reply_markup,
        )
    except Exception as exc:
        logger.error(f"Error enviando mensaje a {chat_id}: {exc}")


async def responder_callback_query(callback_query_id: str) -> None:
    """Answer a callback query to remove the loading spinner."""
    bot = _get_bot()
    try:
        await run_in_threadpool(bot.answer_callback_query, callback_query_id)
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
        lines.append(f"• {escape_markdown_v2(slot['hora_inicio'])} \\- {escape_markdown_v2(slot['hora_fin'])}")
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


# ---------------------------------------------------------------------------
# Business actions
# ---------------------------------------------------------------------------

async def mostrar_disponibilidad(
    db, fecha: date | None = None
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

    slots = await consultar_disponibilidad(db, fecha)
    if not slots:
        return f"No hay horarios disponibles para el {escape_markdown_v2(str(fecha))}", None

    texto = format_disponibilidad(str(fecha), slots)
    horas = [s["hora_inicio"] for s in slots]
    keyboard = format_horas_keyboard(horas)
    return texto, keyboard


async def accion_reservar_temporal(db, chat_id: int, fecha: str, hora: str) -> tuple[str, InlineKeyboardMarkup | None]:
    """Create a temporary reservation for the selected slot."""
    try:
        fecha_dt = date.fromisoformat(fecha)
        hora_dt = time.fromisoformat(hora)
        turno = await reservar_turno(db, fecha=fecha_dt, hora_inicio=hora_dt)
        state = _get_state(chat_id)
        state["turno_temporal_id"] = turno.id
        texto = (
            f"Reserva temporal creada para el {escape_markdown_v2(fecha)} a las {escape_markdown_v2(hora)}\n\n"
            "*Ingresá tus datos:*\nNombre, Apellido, DNI, Teléfono \\(separados por comas\\)"
        )
        return texto, None
    except Exception as exc:
        logger.exception("Error reservando turno temporal")
        return format_error(str(exc)), None


async def accion_confirmar_turno(db, chat_id: int, datos: dict[str, str]) -> str:
    """Confirm the temporary reservation with patient data."""
    state = _get_state(chat_id)
    turno_id = state.get("turno_temporal_id")
    if turno_id is None:
        return format_error("No hay una reserva para confirmar")

    try:
        turno = await confirmar_turno(db, turno_id=turno_id, paciente_data=datos)
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
    return "Operación cancelada\\. Volvé a empezar con /start"


async def accion_iniciar_reprogramacion(db, chat_id: int, turno_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
    """Inicia el flujo de reprogramación guardando el turno_id y mostrando fechas."""
    state = _get_state(chat_id)
    state["estado"] = "reprogramando_esperando_fecha"
    state["turno_a_reprogramar_id"] = turno_id
    texto, keyboard = await mostrar_disponibilidad(db)
    return texto, keyboard


async def accion_reprogramar_turno(db, chat_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
    """Placeholder for reschedule flow triggered by text message."""
    return "Reprogramar turno \\(próximamente\\)", None


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


async def enviar_notificacion_lista_espera(chat_id: str, turno: Any) -> bool:
    """Send waiting list offer notification with Accept/Reject inline keyboard."""
    try:
        texto = format_lista_espera_mensaje(turno)
        keyboard = format_lista_espera_keyboard(turno.id)
        await enviar_mensaje(int(chat_id), texto, keyboard)
        return True
    except Exception as exc:
        logger.error(f"Error enviando notificación de lista de espera a {chat_id}: {exc}")
        return False


async def accion_aceptar_lista_espera(db, chat_id: int, turno_id: int) -> str:
    """Accept a waiting-list offered turno."""
    from app.services.lista_espera_service import aceptar_turno_lista_espera
    from sqlalchemy import select
    from app.models.lista_de_espera import ListaDeEspera

    # Find the waiting-list record for this turno and chat
    result = await db.execute(
        select(ListaDeEspera).where(
            ListaDeEspera.turno_ofrecido_id == turno_id,
            ListaDeEspera.notificado == True,
        )
    )
    registro = result.scalar_one_or_none()
    if registro is None:
        return format_error("No se encontró una oferta de lista de espera activa para este turno")

    try:
        confirmado = await aceptar_turno_lista_espera(db, lista_espera_id=registro.id)
        texto = (
            f"✅ *Turno confirmado*\n\n"
            f"*Fecha:* {escape_markdown_v2(str(confirmado.fecha))}\n"
            f"*Hora:* {escape_markdown_v2(str(confirmado.hora_inicio))}"
        )
        return texto
    except Exception as exc:
        logger.exception("Error aceptando turno de lista de espera")
        return format_error(str(exc))


async def accion_rechazar_lista_espera(db, chat_id: int, turno_id: int) -> str:
    """Reject a waiting-list offered turno."""
    from app.services.lista_espera_service import rechazar_turno_lista_espera
    from sqlalchemy import select
    from app.models.lista_de_espera import ListaDeEspera

    result = await db.execute(
        select(ListaDeEspera).where(
            ListaDeEspera.turno_ofrecido_id == turno_id,
            ListaDeEspera.notificado == True,
        )
    )
    registro = result.scalar_one_or_none()
    if registro is None:
        return format_error("No se encontró una oferta de lista de espera activa para este turno")

    try:
        await rechazar_turno_lista_espera(db, lista_espera_id=registro.id, turno_id=turno_id)
        return "Turno rechazado\. Si hay otro paciente en lista de espera se le notificará\."
    except Exception as exc:
        logger.exception("Error rechazando turno de lista de espera")
        return format_error(str(exc))


# ---------------------------------------------------------------------------
# Background task processor
# ---------------------------------------------------------------------------

async def procesar_update_async(update: dict) -> None:
    """Crea una sesión de DB y procesa el update de Telegram en background."""
    session_maker = _session_factory()
    async with session_maker() as db:
        try:
            await procesar_mensaje(db, update)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------

async def procesar_mensaje(db, update: dict[str, Any]) -> None:
    """Parse a Telegram update and route to the appropriate action."""
    chat_id = _extract_chat_id(update)
    if chat_id is None:
        logger.warning("Update sin chat_id: %s", update)
        return

    async with _conversation_locks[chat_id]:
        state = _get_state(chat_id)
        text = _extract_text(update)
        callback_data = _extract_callback_data(update)
        callback_query_id = _extract_callback_query_id(update)

        if callback_query_id:
            await responder_callback_query(callback_query_id)

        if callback_data:
            tipo, valor = _parse_callback_data(callback_data)

            if tipo == "fecha":
                if state["estado"] == "reprogramando_esperando_fecha":
                    state["estado"] = "reprogramando_esperando_hora"
                    state["nueva_fecha_seleccionada"] = valor
                    texto, keyboard = await mostrar_disponibilidad(db, fecha=date.fromisoformat(valor))
                    await enviar_mensaje(chat_id, texto, keyboard)
                    return
                # Default booking flow
                state["estado"] = "esperando_hora"
                state["fecha_seleccionada"] = valor
                texto, keyboard = await mostrar_disponibilidad(db, fecha=date.fromisoformat(valor))
                await enviar_mensaje(chat_id, texto, keyboard)
                return

            if tipo == "hora":
                if state["estado"] == "reprogramando_esperando_hora":
                    turno_id = state.get("turno_a_reprogramar_id")
                    nueva_fecha = state.get("nueva_fecha_seleccionada")
                    if turno_id and nueva_fecha:
                        try:
                            nuevo_turno = await reprogramar_turno(
                                db,
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
                            await enviar_mensaje(chat_id, texto)
                        except TurnoNoDisponibleError as exc:
                            texto = format_error(f"{exc.message}\\. Seleccioná otra fecha")
                            state["estado"] = "reprogramando_esperando_fecha"
                            await enviar_mensaje(chat_id, texto)
                        except TurnoYaCanceladoError as exc:
                            texto = format_error(f"{exc.message}\\. No se puede reprogramar")
                            state["estado"] = "idle"
                            state["turno_a_reprogramar_id"] = None
                            state["nueva_fecha_seleccionada"] = None
                            await enviar_mensaje(chat_id, texto)
                        except Exception as exc:
                            logger.exception("Error reprogramando turno desde Telegram")
                            texto = format_error(f"Error inesperado: {exc}")
                            state["estado"] = "idle"
                            state["turno_a_reprogramar_id"] = None
                            state["nueva_fecha_seleccionada"] = None
                            await enviar_mensaje(chat_id, texto)
                    return
                # Default booking flow
                state["estado"] = "esperando_datos"
                fecha = state.get("fecha_seleccionada")
                if fecha:
                    texto, keyboard = await accion_reservar_temporal(db, chat_id, fecha, valor)
                    await enviar_mensaje(chat_id, texto, keyboard)
                return

            if callback_data == "confirmar_datos":
                state["estado"] = "esperando_confirmacion"
                # In a real flow, datos_paciente would have been collected earlier
                datos = state.get("datos_paciente") or {"nombre": "", "apellido": "", "dni": "", "telefono": ""}
                texto = await accion_confirmar_turno(db, chat_id, datos)
                await enviar_mensaje(chat_id, texto)
                return

            if callback_data == "cancelar_accion":
                texto = await accion_cancelar_turno(db, chat_id)
                # Also clear reprogramacion state
                state["turno_a_reprogramar_id"] = None
                state["nueva_fecha_seleccionada"] = None
                await enviar_mensaje(chat_id, texto)
                return

            if tipo == "reprogramar":
                turno_id = int(valor)
                texto, keyboard = await accion_iniciar_reprogramacion(db, chat_id, turno_id)
                await enviar_mensaje(chat_id, texto, keyboard)
                return

            if tipo == "lista_espera":
                subtipo, turno_id_str = valor.split(":", 1)
                turno_id = int(turno_id_str)
                if subtipo == "aceptar":
                    texto = await accion_aceptar_lista_espera(db, chat_id, turno_id)
                elif subtipo == "rechazar":
                    texto = await accion_rechazar_lista_espera(db, chat_id, turno_id)
                else:
                    texto = format_error("Acción no reconocida")
                await enviar_mensaje(chat_id, texto)
                return

            if tipo == "reminder":
                subtipo, turno_id_str = valor.split(":", 1)
                turno_id = int(turno_id_str)
                if subtipo == "confirmar":
                    try:
                        await confirmar_asistencia_turno(db, turno_id)
                        texto = (
                            f"✅ *Asistencia confirmada*\n\n"
                            f"Gracias por confirmar\\. Te esperamos en tu turno\\."
                        )
                    except Exception as exc:
                        logger.exception("Error confirmando asistencia desde recordatorio")
                        texto = format_error(str(exc))
                elif subtipo == "cancelar":
                    try:
                        turno_cancelado = await cancelar_turno(db, turno_id)
                        texto = (
                            f"❌ *Turno cancelado*\n\n"
                            f"Fecha: {escape_markdown_v2(str(turno_cancelado.fecha))}\n"
                            f"Hora: {escape_markdown_v2(str(turno_cancelado.hora_inicio))}"
                        )
                    except Exception as exc:
                        logger.exception("Error cancelando turno desde recordatorio")
                        texto = format_error(str(exc))
                elif subtipo == "reprogramar":
                    texto, keyboard = await accion_iniciar_reprogramacion(db, chat_id, turno_id)
                    if keyboard:
                        await enviar_mensaje(chat_id, texto, keyboard)
                        return
                else:
                    texto = format_error("Acción no reconocida")
                await enviar_mensaje(chat_id, texto)
                return

        if text:
            text_lower = text.strip().lower()

            if text_lower in ("/start", "quiero un turno"):
                state["estado"] = "esperando_fecha"
                texto, keyboard = await mostrar_disponibilidad(db)
                await enviar_mensaje(chat_id, texto, keyboard)
                return

            if text_lower == "cancelar":
                texto = await accion_cancelar_turno(db, chat_id)
                await enviar_mensaje(chat_id, texto)
                return

            if text_lower == "reprogramar":
                texto, keyboard = await accion_reprogramar_turno(db, chat_id)
                await enviar_mensaje(chat_id, texto, keyboard)
                return

            # Fallback: unrecognized text
            if state["estado"] == "idle":
                await enviar_mensaje(
                    chat_id,
                    "No entendí tu mensaje\n\nComandos disponibles:\n• /start \\- Quiero un turno\n• Cancelar\n• Reprogramar",
                )
                return

            # If in a flow expecting data, try to parse as patient data
            if state["estado"] == "esperando_datos":
                # Simple CSV parsing: nombre, apellido, dni, telefono
                parts = [p.strip() for p in text.split(",")]
                if len(parts) >= 4:
                    state["datos_paciente"] = {
                        "nombre": parts[0],
                        "apellido": parts[1],
                        "dni": parts[2],
                        "telefono": parts[3],
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
                    await enviar_mensaje(chat_id, texto, format_confirmacion_keyboard())
                else:
                    await enviar_mensaje(
                        chat_id,
                        "Formato incorrecto\n\nIngresá: Nombre, Apellido, DNI, Teléfono",
                    )
                return

        logger.info("Unhandled update for chat_id %s: %s", chat_id, update)
