"""
Endpoints para autenticación con Supabase
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.dependencies import require_role
from app.core.exceptions import DuplicateEntityError, InvalidCredentialsError
from app.domain.entities.supabase_user import SupabaseUser, UserRole
from app.domain.use_cases.auth import (
    LoginUserSupabaseUseCase,
    RegisterUserSupabaseUseCase,
)
from app.infrastructure.database.repositories.supabase_user_repository_impl import (
    SupabaseUserRepositoryImpl,
)
from app.presentation.api.v1.schemas.auth import RefreshTokenRequest, TokenResponse
from app.presentation.api.v1.schemas.supabase_auth import (
    AuthResponse,
    RegisterRequest,
    UserResponse,
)
from app.presentation.middleware.rate_limit import limiter

router = APIRouter(tags=["auth"])


def get_supabase_user_repository() -> SupabaseUserRepositoryImpl:
    """
    Obtener repositorio de usuarios con Supabase

    Returns:
        Repositorio de usuarios
    """
    return SupabaseUserRepositoryImpl()


def get_register_use_case(
    repository: SupabaseUserRepositoryImpl = Depends(get_supabase_user_repository),
) -> RegisterUserSupabaseUseCase:
    """
    Obtener caso de uso para registro de usuarios

    Args:
        repository: Repositorio de usuarios

    Returns:
        Caso de uso para registro de usuarios
    """
    return RegisterUserSupabaseUseCase(repository)


def get_login_use_case(
    repository: SupabaseUserRepositoryImpl = Depends(get_supabase_user_repository),
) -> LoginUserSupabaseUseCase:
    """
    Obtener caso de uso para login de usuarios

    Args:
        repository: Repositorio de usuarios

    Returns:
        Caso de uso para login de usuarios
    """
    return LoginUserSupabaseUseCase(repository)


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit(
    "5/minute"
)  # SECURITY: Limitar a 5 intentos/minuto para prevenir ataques de registro masivo
async def register(
    request: Request,
    register_data: RegisterRequest,
    use_case: RegisterUserSupabaseUseCase = Depends(get_register_use_case),
) -> AuthResponse:
    """
    Registrar un nuevo usuario

    - **email**: Email del usuario
    - **password**: Contraseña del usuario (mínimo 8 caracteres)
    - **full_name**: Nombre completo del usuario (opcional)
    """
    try:
        # TESTING: Permitir rol personalizado en entorno no-production
        # En producción, siempre usar UserRole.USER por seguridad
        from app.core.config import settings

        # Intentar obtener el rol de la solicitud (solo para tests/dev)
        # En producción, esto siempre será UserRole.USER
        role = UserRole.USER
        if settings.ENVIRONMENT != "production" and hasattr(register_data, 'role') and register_data.role:
            role = register_data.role

        # Registrar usuario
        user = await use_case.execute(
            email=register_data.email,
            password=register_data.password,
            full_name=register_data.full_name,
            role=role,
        )

        # NOTA: Con la eliminación de auto-confirmación de email,
        # el usuario debe confirmar su email antes de poder autenticarse.
        # Por lo tanto, NO intentamos autenticar inmediatamente después del registro.

        # Devolver respuesta indicando que debe confirmar email
        return AuthResponse(
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
            ),
            access_token="",  # Sin token hasta confirmar email
            refresh_token="",
            message="Usuario registrado exitosamente. Por favor, confirma tu email antes de iniciar sesión.",
        )
    except DuplicateEntityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except Exception as e:
        import logging

        logger = logging.getLogger("app.presentation.api.v1.endpoints.supabase_auth")
        logger.error(f"Error en registro: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/login", response_model=AuthResponse)
@limiter.limit(
    "5/minute"
)  # SECURITY: Limitar a 5 intentos/minuto para prevenir ataques de fuerza bruta
async def login(
    request: Request,
    login_data: RegisterRequest,
    use_case: LoginUserSupabaseUseCase = Depends(get_login_use_case),
) -> AuthResponse:
    """
    Autenticar un usuario

    - **email**: Email del usuario
    - **password**: Contraseña del usuario
    """
    try:
        # Autenticar usuario
        user, access_token, refresh_token = await use_case.execute(
            email=login_data.email,
            password=login_data.password,
        )

        # Crear respuesta
        return AuthResponse(
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
            ),
            access_token=access_token,
            refresh_token=refresh_token,
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(
    "10/minute"
)  # SECURITY: 10 intentos/minuto es suficiente para refresh tokens (menos crítico que login)
async def refresh_token(
    request: Request, refresh_data: RefreshTokenRequest
) -> TokenResponse:
    """
    Refrescar token de acceso usando Supabase Auth

    - **refresh_token**: Token de refresco de Supabase
    """
    try:
        from app.infrastructure.external.supabase import supabase_client

        # Refrescar sesión con Supabase
        client = await supabase_client.client
        refresh_response = await client.auth.refresh_session(refresh_data.refresh_token)

        if not refresh_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido o expirado",
            )

        return TokenResponse(
            access_token=refresh_response.session.access_token,
            refresh_token=refresh_response.session.refresh_token,
            token_type="bearer",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error al refrescar token: {str(e)}",
        ) from e


@router.post("/logout")
@limiter.limit("20/minute")  # SECURITY: Logout es menos crítico, permitir 20/min
async def logout(
    request: Request,
    current_user: Annotated[SupabaseUser, Depends(require_role("USER"))],
) -> dict[str, str]:
    """
    Cerrar sesión con revocación de token en Supabase

    Este endpoint revoca la sesión activa del usuario en Supabase,
    invalidando el token actual.
    """
    try:
        from app.infrastructure.external.supabase import supabase_client

        # Obtener el token del header Authorization
        authorization: str = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autorización no proporcionado",
            )

        # Revocar la sesión en Supabase (sign out)
        client = await supabase_client.client
        await client.auth.sign_out()

        return {"message": "Sesión cerrada exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        # No fallar si hay error al revocar, ya que el cliente puede eliminar el token
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Error al revocar sesión en logout: {e}")
        return {"message": "Sesión cerrada exitosamente"}
