from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import CurrentSuperAdminDep, DbDep, SettingsDep, require_https
from app.schemas.auth import TokenResponse
from app.schemas.profesional import ProfesionalCreateRequest, ProfesionalCreateResponse
from app.schemas.super_admin import (
    GlobalMetricsResponse,
    ProfesionalAdminResponse,
    SuperAdminLoginRequest,
)
from app.services.auth_service import create_super_admin_access_token
from app.services import super_admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/auth/login", response_model=TokenResponse)
async def admin_login(
    data: SuperAdminLoginRequest,
    db: DbDep,
    settings: SettingsDep,
) -> TokenResponse:
    admin = await super_admin_service.authenticate_super_admin(
        db, data.email, data.password
    )
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_super_admin_access_token(admin.id, admin.email, settings)
    return TokenResponse(access_token=token)


@router.post(
    "/profesionales",
    response_model=ProfesionalCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_profesional(
    data: ProfesionalCreateRequest,
    _admin: CurrentSuperAdminDep,
    db: DbDep,
    _https: None = Depends(require_https),
) -> ProfesionalCreateResponse:
    profesional, api_key, telegram_secret_token = (
        await super_admin_service.create_profesional(db, data)
    )
    return ProfesionalCreateResponse(
        id=profesional.id,
        nombre=profesional.nombre,
        email=profesional.email,
        especialidad=profesional.especialidad,
        is_active=profesional.is_active,
        duracion_turno=profesional.duracion_turno,
        horario_inicio=profesional.horario_inicio,
        horario_fin=profesional.horario_fin,
        dias_atencion=profesional.dias_atencion,
        api_key=api_key,
        telegram_secret_token=telegram_secret_token,
    )


@router.get(
    "/profesionales",
    response_model=list[ProfesionalAdminResponse],
)
async def admin_list_profesionales(
    _admin: CurrentSuperAdminDep,
    db: DbDep,
    skip: int = 0,
    limit: int = 100,
) -> list[ProfesionalAdminResponse]:
    profesionales = await super_admin_service.list_profesionales(db, skip, limit)
    return [ProfesionalAdminResponse.model_validate(p) for p in profesionales]


@router.get(
    "/profesionales/{profesional_id}",
    response_model=ProfesionalAdminResponse,
)
async def admin_get_profesional(
    profesional_id: int,
    _admin: CurrentSuperAdminDep,
    db: DbDep,
) -> ProfesionalAdminResponse:
    profesional = await super_admin_service.get_profesional(db, profesional_id)
    if profesional is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profesional no encontrado",
        )
    return ProfesionalAdminResponse.model_validate(profesional)


@router.put(
    "/profesionales/{profesional_id}/activar",
    response_model=ProfesionalAdminResponse,
)
async def admin_activate_profesional(
    profesional_id: int,
    _admin: CurrentSuperAdminDep,
    db: DbDep,
) -> ProfesionalAdminResponse:
    profesional = await super_admin_service.activate_profesional(db, profesional_id)
    if profesional is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profesional no encontrado",
        )
    return ProfesionalAdminResponse.model_validate(profesional)


@router.put(
    "/profesionales/{profesional_id}/desactivar",
    response_model=ProfesionalAdminResponse,
)
async def admin_deactivate_profesional(
    profesional_id: int,
    _admin: CurrentSuperAdminDep,
    db: DbDep,
) -> ProfesionalAdminResponse:
    profesional = await super_admin_service.deactivate_profesional(db, profesional_id)
    if profesional is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profesional no encontrado",
        )
    return ProfesionalAdminResponse.model_validate(profesional)


@router.get("/metricas", response_model=GlobalMetricsResponse)
async def admin_get_metricas(
    _admin: CurrentSuperAdminDep,
    db: DbDep,
) -> GlobalMetricsResponse:
    return await super_admin_service.compute_global_metrics(db)
