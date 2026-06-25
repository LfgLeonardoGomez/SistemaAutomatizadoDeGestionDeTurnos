from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.dependencies import DbDep, SettingsDep, get_current_profesional
from app.models.profesional import Profesional
from app.schemas.auth import (
    ApiKeyResponse,
    ProfesionalLoginRequest,
    TokenResponse,
)
from app.services.auth_service import (
    authenticate_profesional,
    create_access_token,
    set_profesional_api_key,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def auth_login(
    data: ProfesionalLoginRequest,
    db: DbDep,
    settings: SettingsDep,
) -> TokenResponse:
    profesional = await authenticate_profesional(db, data.email, data.password)
    if profesional is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(profesional.id, profesional.email, settings)
    return TokenResponse(access_token=token)


@router.post("/api-key", response_model=ApiKeyResponse)
async def auth_api_key(
    db: DbDep,
    profesional: Profesional = Depends(get_current_profesional),
) -> ApiKeyResponse:
    api_key = await set_profesional_api_key(db, profesional)
    return ApiKeyResponse(api_key=api_key)
