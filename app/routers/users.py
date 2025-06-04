# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Security, Request
from sqlalchemy.orm import Session
from typing import List

from app import crud, schemas, models, security
from app.database import get_db
from app.config import settings
from app.logging_utils import log_action

router = APIRouter(
    prefix=settings.API_V1_STR + "/users",
    tags=["Users Management"],
    dependencies=[Security(security.get_current_admin_user)]
)


# --- Foydalanuvchilarni Boshqarish ---
@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED,
             summary="Yangi foydalanuvchi yaratish")
def create_new_user(
        request: Request,
        user_in: schemas.UserCreate,
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_admin_user)
):
    """
    1 - admin
    2 - menejer
    3 - oshpaz
    """
    db_user_by_username = crud.get_user_by_username(db, username=user_in.username)
    if db_user_by_username:
        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="CREATE_USER_ATTEMPT", status="FAILURE",
            details=f"User creation failed by admin '{current_user_from_dep.username}'. Username '{user_in.username}' already exists.",
            changes_after={"username": user_in.username, "full_name": user_in.full_name, "role_id": user_in.role_id}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{user_in.username}' nomli foydalanuvchi allaqachon mavjud."
        )

    db_role = crud.get_role(db, role_id=user_in.role_id)
    if not db_role:
        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="CREATE_USER_ATTEMPT", status="FAILURE",
            details=f"User creation failed by admin '{current_user_from_dep.username}'. Role ID {user_in.role_id} not found.",
            changes_after={"username": user_in.username, "full_name": user_in.full_name, "role_id": user_in.role_id}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={user_in.role_id} bo'lgan rol topilmadi."
        )
    try:
        created_user = crud.create_user(db=db, user=user_in)
        # Parolni loglamaymiz
        user_data_for_log = {"username": created_user.username, "full_name": created_user.full_name, "role_id": created_user.role_id, "is_active": created_user.is_active}
        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="CREATE_USER", status="SUCCESS",
            target_entity_type="User", target_entity_id=created_user.id,
            details=f"User '{created_user.username}' (ID: {created_user.id}) created by admin '{current_user_from_dep.username}'.",
            changes_after=user_data_for_log
        )
        return created_user
    except Exception as e:
        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="CREATE_USER_ATTEMPT", status="ERROR",
            details=f"Unexpected error during user creation by admin '{current_user_from_dep.username}': {str(e)}",
            changes_after={"username": user_in.username, "full_name": user_in.full_name, "role_id": user_in.role_id}
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Foydalanuvchi yaratishda kutilmagan xatolik: {str(e)}")


# @router.get("/", response_model=List[schemas.User], summary="Barcha foydalanuvchilar ro'yxati")
# def read_all_users(
#         skip: int = Query(0, ge=0), # Query ni import qilish kerak bo'lishi mumkin, agar hali import qilinmagan bo'lsa
#         limit: int = Query(100, ge=1, le=200),
#         db: Session = Depends(get_db)
# ):
#     users = crud.get_users(db, skip=skip, limit=limit)
#     return users


@router.get("/", response_model=List[schemas.User], summary="Barcha foydalanuvchilar ro'yxati")
def read_all_users(
        # request: Request,
        skip: int = 0,  # Query olib tashlandi, faqat default qiymat
        limit: int = 100, # Query olib tashlandi, faqat default qiymat
        db: Session = Depends(get_db)
        # current_admin_from_dep: models.User = Depends(security.get_current_admin_user)
):
    """
    Barcha (o'chirilmagan) foydalanuvchilar ro'yxatini olish (Faqat Admin).

    Query parametrlari:
    - skip: O'tkazib yuboriladigan yozuvlar soni (standart: 0). Minimal qiymat: 0.
    - limit: Qaytariladigan yozuvlar soni (standart: 100). Minimal qiymat: 1, Maksimal qiymat: 200.
    """
    # Backendda validatsiya qilish (agar Query ishlamasa)
    if not (0 <= skip):
        raise HTTPException(status_code=422, detail="Skip parametri 0 dan kichik bo'lishi mumkin emas.")
    if not (1 <= limit <= 200):
        raise HTTPException(status_code=422, detail="Limit parametri 1 va 200 oralig'ida bo'lishi kerak.")

    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=schemas.User, summary="ID bo'yicha foydalanuvchini olish")
def read_user_by_id(
        user_id: int,
        db: Session = Depends(get_db)
):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi")
    return db_user


@router.put("/{user_id}", response_model=schemas.User, summary="Foydalanuvchini yangilash")
def update_existing_user(
        request: Request, # <<--- BIRINCHI O'RINGA O'TKAZILDI
        user_id: int,
        user_in: schemas.UserUpdate,
        db: Session = Depends(get_db),
        current_admin_from_dep: models.User = Depends(security.get_current_admin_user)
):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        log_action(
            db=db, request=request, current_user=current_admin_from_dep,
            action_name="UPDATE_USER_ATTEMPT", status="NOT_FOUND",
            target_entity_type="User", target_entity_id=user_id,
            details=f"User ID {user_id} not found for update by admin '{current_admin_from_dep.username}'."
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yangilash uchun foydalanuvchi topilmadi")

    old_user_data_for_log = {
        "username": db_user.username, "full_name": db_user.full_name,
        "role_id": db_user.role_id, "is_active": db_user.is_active
    }
    # Parol o'zgarishini alohida loglash mumkin (parolni o'zini loglamasdan)
    password_changed_detail = " Password will be updated." if user_in.password else ""

    if user_id == current_admin_from_dep.id and user_in.is_active is False:
        details_log = f"Admin '{current_admin_from_dep.username}' attempted to deactivate their own account."
        log_action(db=db, request=request, current_user=current_admin_from_dep, action_name="UPDATE_USER_ATTEMPT", status="FAILURE", target_entity_type="User", target_entity_id=user_id, details=details_log, changes_before=old_user_data_for_log, changes_after=user_in.model_dump(exclude_unset=True, exclude={"password"}))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin o'zining 'is_active' statusini o'zgartira olmaydi.")
    if user_id == current_admin_from_dep.id and user_in.role_id and user_in.role_id != current_admin_from_dep.role_id:
        details_log = f"Admin '{current_admin_from_dep.username}' attempted to change their own role."
        log_action(db=db, request=request, current_user=current_admin_from_dep, action_name="UPDATE_USER_ATTEMPT", status="FAILURE", target_entity_type="User", target_entity_id=user_id, details=details_log, changes_before=old_user_data_for_log, changes_after=user_in.model_dump(exclude_unset=True, exclude={"password"}))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin o'zining rolini o'zgartira olmaydi.")

    if user_in.username and user_in.username != db_user.username:
        existing_user_with_new_username = crud.get_user_by_username(db, username=user_in.username)
        if existing_user_with_new_username:
            log_action(db=db, request=request, current_user=current_admin_from_dep, action_name="UPDATE_USER_ATTEMPT", status="FAILURE", target_entity_type="User", target_entity_id=user_id, details=f"Update user failed. New username '{user_in.username}' already exists.", changes_before=old_user_data_for_log, changes_after=user_in.model_dump(exclude_unset=True, exclude={"password"}))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"'{user_in.username}' nomli foydalanuvchi allaqachon mavjud.")

    if user_in.role_id:
        db_role = crud.get_role(db, role_id=user_in.role_id)
        if not db_role:
            log_action(db=db, request=request, current_user=current_admin_from_dep, action_name="UPDATE_USER_ATTEMPT", status="FAILURE", target_entity_type="User", target_entity_id=user_id, details=f"Update user failed. Role ID {user_in.role_id} not found.", changes_before=old_user_data_for_log, changes_after=user_in.model_dump(exclude_unset=True, exclude={"password"}))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ID={user_in.role_id} bo'lgan rol topilmadi.")
    try:
        updated_user = crud.update_user(db=db, user_id=user_id, user_update=user_in)
        if updated_user is None: # Bu holat deyarli bo'lmasligi kerak
            log_action(db=db, request=request, current_user=current_admin_from_dep, action_name="UPDATE_USER_ATTEMPT", status="ERROR", target_entity_type="User", target_entity_id=user_id, details="User update returned None unexpectedly.", changes_before=old_user_data_for_log, changes_after=user_in.model_dump(exclude_unset=True, exclude={"password"}))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Foydalanuvchini yangilashda noma'lum xatolik.")

        # Parolni loglamasdan, faqat o'zgargan maydonlarni loglash
        changes_after_log = user_in.model_dump(exclude_unset=True, exclude={"password"})
        if user_in.password:
            changes_after_log["password_changed"] = True

        log_action(
            db=db, request=request, current_user=current_admin_from_dep,
            action_name="UPDATE_USER", status="SUCCESS",
            target_entity_type="User", target_entity_id=updated_user.id,
            details=f"User '{updated_user.username}' (ID: {user_id}) updated by admin '{current_admin_from_dep.username}'.{password_changed_detail}",
            changes_before=old_user_data_for_log,
            changes_after=changes_after_log
        )
        return updated_user
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        log_action(db=db, request=request, current_user=current_admin_from_dep, action_name="UPDATE_USER_ATTEMPT", status="ERROR", target_entity_type="User", target_entity_id=user_id, details=f"Unexpected error updating user ID {user_id} by admin '{current_admin_from_dep.username}': {str(e)}", changes_before=old_user_data_for_log, changes_after=user_in.model_dump(exclude_unset=True, exclude={"password"}))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Foydalanuvchini yangilashda kutilmagan server xatoligi: {str(e)}")


@router.delete("/{user_id}", response_model=schemas.User, summary="Foydalanuvchini \"soft delete\" qilish")
def soft_delete_existing_user(
        request: Request, # <<--- BIRINCHI O'RINGA O'TKAZILDI
        user_id: int,
        db: Session = Depends(get_db),
        current_admin_from_dep: models.User = Depends(security.get_current_admin_user)
):
    if user_id == current_admin_from_dep.id:
        details_log = f"Admin '{current_admin_from_dep.username}' attempted to delete their own account."
        log_action(db=db, request=request, current_user=current_admin_from_dep, action_name="DELETE_USER_ATTEMPT", status="FAILURE", target_entity_type="User", target_entity_id=user_id, details=details_log)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin o'zini o'chira olmaydi.")

    db_user_to_delete = crud.get_user(db, user_id=user_id)
    if db_user_to_delete is None:
        log_action(db=db, request=request, current_user=current_admin_from_dep, action_name="DELETE_USER_ATTEMPT", status="NOT_FOUND", target_entity_type="User", target_entity_id=user_id, details=f"User ID {user_id} not found for deletion by admin '{current_admin_from_dep.username}'.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="O'chirish uchun foydalanuvchi topilmadi")

    # old_user_data_for_log = schemas.User.model_validate(db_user_to_delete).model_dump(exclude={"password_hash"})
    try:
        deleted_user = crud.soft_delete_user(db=db, user_id=user_id)
        if deleted_user is None: # Bu holat bo'lmasligi kerak
            log_action(db=db, request=request, current_user=current_admin_from_dep, action_name="DELETE_USER_ATTEMPT", status="ERROR", target_entity_type="User", target_entity_id=user_id, details=f"Soft delete for user ID {user_id} returned None unexpectedly.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Foydalanuvchini o'chirishda noma'lum xatolik.")

        log_action(
            db=db, request=request, current_user=current_admin_from_dep,
            action_name="DELETE_USER", status="SUCCESS",
            target_entity_type="User", target_entity_id=deleted_user.id,
            details=f"User '{deleted_user.username}' (ID: {user_id}) soft deleted by admin '{current_admin_from_dep.username}'."
            # changes_before=old_user_data_for_log # Agar kerak bo'lsa
        )
        return deleted_user
    except Exception as e:
        log_action(db=db, request=request, current_user=current_admin_from_dep, action_name="DELETE_USER_ATTEMPT", status="ERROR", target_entity_type="User", target_entity_id=user_id, details=f"Unexpected error deleting user ID {user_id} by admin '{current_admin_from_dep.username}': {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Foydalanuvchini o'chirishda kutilmagan server xatoligi: {str(e)}")


# --- Rollarni Boshqarish (Admin uchun) ---
# Rol amallari uchun log yozish hozircha qo'shilmadi, lekin kerak bo'lsa, xuddi shunday qo'shish mumkin.
@router.post("/roles/", response_model=schemas.Role, status_code=status.HTTP_201_CREATED, summary="Yangi rol yaratish")
def create_new_role(
        # request: Request, # Agar loglash kerak bo'lsa
        role_in: schemas.RoleCreate,
        db: Session = Depends(get_db)
        # current_admin_from_dep: models.User = Depends(security.get_current_admin_user) # Agar loglash kerak bo'lsa
):
    db_role = crud.get_role_by_name(db, name=role_in.name)
    if db_role:
        # log_action(...)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{role_in.name}' nomli rol allaqachon mavjud."
        )
    created_role = crud.create_role(db=db, role=role_in)
    # log_action(...)
    return created_role


@router.get("/roles/", response_model=List[schemas.Role], summary="Barcha rollar ro'yxati")
def read_all_roles(
        skip: int = 0,  # Query olib tashlandi, faqat default qiymat
        limit: int = 20, # Query olib tashlandi, faqat default qiymat
        db: Session = Depends(get_db)
):
    """
    Tizimdagi barcha mavjud rollar ro'yxatini olish (Faqat Admin).

    Query parametrlari:
    - skip: O'tkazib yuboriladigan yozuvlar soni (standart: 0). Minimal qiymat: 0.
    - limit: Qaytariladigan yozuvlar soni (standart: 20). Minimal qiymat: 1, Maksimal qiymat: 200 (yoki boshqa).
    """
    # Backendda validatsiya qilish (agar Query ishlamasa)
    if not (0 <= skip):
        raise HTTPException(status_code=422, detail="Skip parametri 0 dan kichik bo'lishi mumkin emas.")
    if not (1 <= limit <= 200): # Maksimal limitni o'zingiz belgilang
        raise HTTPException(status_code=422, detail="Limit parametri 1 va 200 oralig'ida bo'lishi kerak.")

    roles = crud.get_roles(db, skip=skip, limit=limit)
    return roles


@router.get("/roles/{role_id}", response_model=schemas.Role, summary="ID bo'yicha rolni olish")
def read_role_by_id(
        role_id: int,
        db: Session = Depends(get_db)
):
    db_role = crud.get_role(db, role_id=role_id)
    if db_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol topilmadi")
    return db_role

