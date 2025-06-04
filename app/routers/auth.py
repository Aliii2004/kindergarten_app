# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app import crud, schemas, models, security
from app.database import get_db
from app.config import settings
from app.logging_utils import log_action
from app.utils import create_initial_data

router = APIRouter(
    prefix=settings.API_V1_STR + "/auth",
    tags=["Authentication"],
)


@router.post("/token", response_model=schemas.Token, summary="Foydalanuvchi uchun kirish tokenini olish")
async def login_for_access_token(
        response: Response,
        request: Request, # Request obyektini argument sifatida qabul qilish
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """
    Foydalanuvchi nomi va parol bilan tizimga kirish va JWT token olish.
    Token javobda va HTTPOnly cookie sifatida qaytariladi.
    """
    user = crud.get_active_user_by_username(db, username=form_data.username)

    if not user or not security.verify_password(form_data.password, user.password_hash):
        # Login muvaffaqiyatsiz bo'lganini loglash
        log_action(
            db=db,
            request=request,
            current_user=None, # Login fail bo'lganda user noma'lum
            action_name="LOGIN_ATTEMPT",
            status="FAILURE",
            details=f"Login attempt failed for username: {form_data.username}."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi nomi yoki parol noto'g'ri",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username, "scopes": [user.role.name]},
        expires_delta=access_token_expires
    )

    user_info_for_token = schemas.User.model_validate(user)

    cookie_max_age = int(access_token_expires.total_seconds())
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=cookie_max_age,
        expires=cookie_max_age,
        samesite="Lax",
        secure=settings.APP_ENV == "production",
        path="/"
    )

    crud.update_user_last_login(db, user.id)
    # db.commit() # Agar update_user_last_login o'zi commit qilmasa

    # Muvaffaqiyatli loginni loglash
    log_action(
        db=db,
        request=request,
        current_user=user, # Muvaffaqiyatli loginda user ma'lum
        action_name="LOGIN_SUCCESS",
        status="SUCCESS",
        target_entity_type="User",
        target_entity_id=user.id,
        details=f"User '{user.username}' logged in successfully."
    )
    # log_action o'zi commit qiladi, shuning uchun bu yerdagi commit shart emas, agar update_user_last_login ham commit qilmasa
    # Agar update_user_last_login commit qilmasa, unda log_action dan keyin yoki oldin bitta commit kerak.
    # Hozirgi log_action implementatsiyasi har bir log yozuvini commit qiladi.
    # update_user_last_login ham commit qilishi kerak yoki bu yerda bitta umumiy commit bo'lishi kerak.
    # Keling, crud.update_user_last_login o'zi commit qiladi deb hisoblaymiz, yoki log_action dan keyin db.commit() chaqiramiz.
    # Yaxshiroq yechim:
    db.commit() # Oxirgi kirish va log yozuvlari uchun yagona commit

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_info": user_info_for_token
    }


@router.post("/logout", summary="Tizimdan chiqish")
async def logout(
    response: Response,
    request: Request, # Request obyektini olish
    db: Session = Depends(get_db), # DB sessiyasini olish
    # Logout uchun current_user kerak, kim logout qilganini bilish uchun
    # Agar token cookie orqali o'chirilayotgan bo'lsa, uni o'qib, user ni olish mumkin
    # Yoki oddiyroq, agar faqat cookie o'chirish bo'lsa, current_user shart emas
    current_user: models.User = Depends(security.get_current_active_user) # Kim logout qilayotganini bilish uchun
):
    """
    Foydalanuvchini tizimdan chiqaradi (access_token cookiesini o'chiradi).
    """
    response.delete_cookie(key="access_token", path="/")

    # Logoutni loglash
    log_action(
        db=db,
        request=request,
        current_user=current_user, # Kim tizimdan chiqqani
        action_name="LOGOUT_SUCCESS",
        status="SUCCESS",
        target_entity_type="User",
        target_entity_id=current_user.id,
        details=f"User '{current_user.username}' logged out successfully."
    )
    # log_action ichida commit bor.

    return {"message": "Muvaffaqiyatli tizimdan chiqdingiz"}


@router.get("/me", response_model=schemas.User, summary="Joriy foydalanuvchi ma'lumotlari")
async def read_users_me(
        # request: Request, # Agar /me so'rovini ham loglash kerak bo'lsa
        # db: Session = Depends(get_db), # Agar /me so'rovini ham loglash kerak bo'lsa
        current_user: models.User = Depends(security.get_current_active_user)
):
    """
    Joriy autentifikatsiyalangan va faol foydalanuvchi ma'lumotlarini olish.
    Odatda /me so'rovlari loglanmaydi, lekin agar kerak bo'lsa, qo'shish mumkin.
    """
    # Agar /me ni loglash kerak bo'lsa:
    # log_action(
    #     db=db,
    #     request=request,
    #     current_user=current_user,
    #     action_name="GET_CURRENT_USER_INFO",
    #     status="SUCCESS",
    #     target_entity_type="User",
    #     target_entity_id=current_user.id,
    #     details=f"User '{current_user.username}' requested their info."
    # )
    return current_user


@router.post(
    "/setup-initial-data",
    summary="Boshlang'ich ma'lumotlarni sozlash (Faqat Admin)",
    include_in_schema=settings.APP_ENV == "development"
)
async def setup_initial_data_endpoint(
        request: Request, # Request obyektini olish
        db: Session = Depends(get_db),
        current_admin: models.User = Depends(security.get_current_admin_user)
):
    """
    (Faqat Admin uchun) Boshlang'ich ma'lumotlarni yaratadi.
    """
    action_details = "Attempting to set up initial system data (roles, admin user, units, notification types)."
    try:
        create_initial_data(db)
        log_action(
            db=db,
            request=request,
            current_user=current_admin,
            action_name="SETUP_INITIAL_DATA",
            status="SUCCESS",
            details="Initial system data setup process completed successfully."
        )
        return {"message": "Boshlang'ich ma'lumotlarni sozlash jarayoni yakunlandi. Server loglarini tekshiring."}
    except Exception as e:
        error_detail_log = f"Error during initial data setup: {str(e)}"
        print(f"ERROR in setup_initial_data_endpoint: {e}") # Konsolga ham chiqarish
        log_action(
            db=db,
            request=request,
            current_user=current_admin,
            action_name="SETUP_INITIAL_DATA",
            status="ERROR",
            details=error_detail_log
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Boshlang'ich ma'lumotlarni sozlashda xatolik yuz berdi: {str(e)}"
        )


