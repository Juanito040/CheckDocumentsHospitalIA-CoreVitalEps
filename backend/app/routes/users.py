"""
Endpoints para gestión de usuarios (Admin)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.models.user import User
from app.core.dependencies import get_current_admin_user
from app.services.auth_service import AuthService
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Listar todos los usuarios del sistema

    Solo accesible para administradores
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Crear nuevo usuario

    Solo accesible para administradores
    """
    try:
        user = AuthService.create_user(db, user_data)
        logger.info(f"Usuario creado por admin {current_admin.email}: {user.email}")
        return user

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error al crear usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear usuario"
        )


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Actualizar usuario existente

    Solo accesible para administradores
    """
    # Buscar usuario
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Actualizar campos proporcionados
    update_data = user_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "password" and value:
            # Hash de nueva contraseña
            setattr(user, "password_hash", get_password_hash(value))
        elif field != "password":
            setattr(user, field, value)

    db.commit()
    db.refresh(user)

    logger.info(f"Usuario actualizado por admin {current_admin.email}: {user.email}")

    return user


@router.delete("/{user_id}")
def deactivate_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Desactivar usuario (no se elimina físicamente)

    Solo accesible para administradores
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # No permitir que el admin se desactive a sí mismo
    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propia cuenta"
        )

    user.activo = False
    db.commit()

    logger.info(f"Usuario desactivado por admin {current_admin.email}: {user.email}")

    return {
        "message": "Usuario desactivado exitosamente",
        "user_id": user_id
    }


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Obtener detalles de un usuario específico

    Solo accesible para administradores
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    return user
