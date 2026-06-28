from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbDep, CurrentProfesionalDep
from app.schemas.lista_espera import ListaEsperaCreate, ListaEsperaResponse
from app.services.lista_espera_service import registrar_en_lista_espera, eliminar_de_lista_espera
from app.exceptions import TurnoNoEncontradoError

router = APIRouter(prefix="/lista-espera", tags=["lista-espera"])


@router.post("", response_model=ListaEsperaResponse, status_code=status.HTTP_201_CREATED)
async def create_lista_espera(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    data: ListaEsperaCreate,
    response: Response,
) -> ListaEsperaResponse:
    """Register a patient in the waiting list for a specific date. Patrón A."""
    try:
        registro = await registrar_en_lista_espera(
            db,
            profesional_id=profesional.id,
            paciente_id=data.paciente_id,
            fecha_solicitada=data.fecha_solicitada,
            telegram_chat_id=data.telegram_chat_id,
        )
        await db.commit()
    except TurnoNoEncontradoError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    return ListaEsperaResponse.model_validate(registro)


@router.delete("/{lista_espera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lista_espera(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    lista_espera_id: int,
) -> None:
    """Remove a patient from the waiting list. Patrón A."""
    try:
        await eliminar_de_lista_espera(db, profesional_id=profesional.id, lista_espera_id=lista_espera_id)
        await db.commit()
    except TurnoNoEncontradoError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
