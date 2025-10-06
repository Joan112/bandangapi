"""
Endpoints para autenticación con Supabase
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.exceptions import DuplicateEntityError, InvalidCredentialsError
from app.domain.entities.supabase_user import UserRole
from app.domain.use_cases.auth import LoginUserSupabaseUseCase, RegisterUserSupabaseUseCase
from app.infrastructure.database.repositories.supabase_user_repository_impl import (
    SupabaseUserRepositoryImpl,
)
from app.presentation.api.v1.schemas.auth import RefreshTokenRequest, TokenResponse
from app.presentation.api.v1.schemas.supabase_auth import (
    AuthResponse,
    RegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/supabase", tags=["supabase-auth"])


def get_supabase_user_repository():
    """
    Obtener repositorio de usuarios con Supabase
    
    Returns:
        Repositorio de usuarios
    """
    return SupabaseUserRepositoryImpl()


def get_register_use_case(
    repository=Depends(get_supabase_user_repository),
):
    """
    Obtener caso de uso para registro de usuarios
    
    Args:
        repository: Repositorio de usuarios
        
    Returns:
        Caso de uso para registro de usuarios
    """
    return RegisterUserSupabaseUseCase(repository)


def get_login_use_case(
    repository=Depends(get_supabase_user_repository),
):
    """
    Obtener caso de uso para login de usuarios
    
    Args:
        repository: Repositorio de usuarios
        
    Returns:
        Caso de uso para login de usuarios
    """
    return LoginUserSupabaseUseCase(repository)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    use_case: RegisterUserSupabaseUseCase = Depends(get_register_use_case),
):
    """
    Registrar un nuevo usuario
    
    - **email**: Email del usuario
    - **password**: Contraseña del usuario (mínimo 8 caracteres)
    - **full_name**: Nombre completo del usuario (opcional)
    """
    try:
        # Registrar usuario
        user = await use_case.execute(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role=UserRole.USER,
        )
        
        try:
            # Autenticar usuario
            login_use_case = LoginUserSupabaseUseCase(get_supabase_user_repository())
            user, access_token, refresh_token = await login_use_case.execute(
                email=request.email,
                password=request.password,
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
        except InvalidCredentialsError:
            # Si falla la autenticación inmediata, devolvemos solo la información del usuario
            # Esto puede ocurrir si Supabase tiene un retraso en la propagación del usuario
            import logging
            logger = logging.getLogger("app.presentation.api.v1.endpoints.supabase_auth")
            logger.warning(f"Usuario creado pero no se pudo autenticar inmediatamente: {user.email}")
            
            # Generar tokens manualmente
            from app.core.security import create_access_token, create_refresh_token
            access_token = create_access_token({"sub": str(user.id)})
            refresh_token = create_refresh_token({"sub": str(user.id)})
            
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
    except DuplicateEntityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        import logging
        logger = logging.getLogger("app.presentation.api.v1.endpoints.supabase_auth")
        logger.error(f"Error en registro: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: RegisterRequest,
    use_case: LoginUserSupabaseUseCase = Depends(get_login_use_case),
):
    """
    Autenticar un usuario
    
    - **email**: Email del usuario
    - **password**: Contraseña del usuario
    """
    try:
        # Autenticar usuario
        user, access_token, refresh_token = await use_case.execute(
            email=request.email,
            password=request.password,
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
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refrescar token de acceso
    
    - **refresh_token**: Token de refresco
    """
    # Esta funcionalidad se implementaría utilizando el token de refresco de Supabase
    # Por ahora, devolvemos un error
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Funcionalidad no implementada",
    )