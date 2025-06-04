# app/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError  # TokenPayload validatsiyasi uchun
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User as UserModel, Role as RoleModel
from app.schemas import TokenPayload, User as UserSchema  # User sxemasini ham olamiz

# --- Parol xeshlash ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# --- JWT Token sozlamalari ---
# Token olish uchun endpointni configdan olish mumkin yoki to'g'ridan-to'g'ri yozish
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token",
    scopes={  # Bu OpenAPI hujjatlari uchun
        settings.ADMIN_ROLE_NAME: "Administrator huquqlari: Barcha amallar.",
        settings.MANAGER_ROLE_NAME: "Menejer huquqlari: Ombor, ovqatlar, hisobotlar.",
        settings.CHEF_ROLE_NAME: "Oshpaz huquqlari: Ovqat berish, mavjud ovqatlarni ko'rish.",
    }
)


# --- Token yaratish ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- Tokenni tekshirish va foydalanuvchini olish ---
def get_user_by_username_for_auth(db: Session, username: str) -> Optional[UserModel]:
    # Bu funksiya faqat aktiv va o'chirilmagan userlarni qaytarishi kerak
    return db.query(UserModel).filter(
        UserModel.username == username,
        UserModel.is_active == True,  # Faqat aktiv
        UserModel.deleted_at == None  # O'chirilmagan
    ).first()


async def get_current_user(
        security_scopes: SecurityScopes,  # Endpoint uchun talab qilingan rollar
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception

        # Token ichidagi rollarni olish
        token_scopes = payload.get("scopes", [])  # Bu ro'yxat bo'lishi kerak

        # Pydantic orqali payloadni validatsiya qilish (ixtiyoriy, lekin yaxshi amaliyot)
        try:
            token_data = TokenPayload(sub=username, scopes=token_scopes, exp=payload.get("exp"))
        except ValidationError:
            raise credentials_exception

    except JWTError:  # Token yaroqsiz, muddati o'tgan yoki boshqa JWT xatoliklari
        raise credentials_exception

    user = get_user_by_username_for_auth(db, username=token_data.sub)
    if user is None:  # Foydalanuvchi topilmadi, aktiv emas yoki o'chirilgan
        raise credentials_exception

    # --- Rol tekshiruvi (SecurityScopes) ---
    # Agar endpoint uchun maxsus rollar (scopes) talab qilinsa
    if security_scopes.scopes:
        # Foydalanuvchining roli token ichidagi scopes bilan mos kelishi kerak
        # Yoki DBdagi roli bilan
        user_role_name = user.role.name  # DBdagi haqiqiy rol

        # Token ichidagi scopes (rollar) ham to'g'ri bo'lishi kerak
        # Bu qismni kuchaytirish mumkin: token scopes DBdagi rolga mos keladimi?
        # Hozircha, DBdagi rolni endpoint scopes bilan tekshiramiz.

        is_authorized = False
        for required_scope in security_scopes.scopes:
            if user_role_name == required_scope:
                is_authorized = True
                break

        if not is_authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required role(s): {', '.join(security_scopes.scopes)}. Your role: {user_role_name}",
                headers={"WWW-Authenticate": f"Bearer scope='{' '.join(security_scopes.scopes)}'"},
            )

    return user


# --- Faol foydalanuvchini olish (rol tekshiruvisiz, faqat autentifikatsiya) ---
# Bu asosan /auth/me kabi endpointlar uchun ishlatiladi
async def get_current_active_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    # get_current_user ichida is_active allaqachon get_user_by_username_for_auth orqali tekshirilgan.
    # Agar get_user_by_username_for_auth is_active ni tekshirmasa, bu yerda qo'shimcha tekshiruv kerak.
    # Hozirgi holatda, bu funksiya deyarli ortiqcha, lekin aniqlik uchun qoldiramiz.
    if not current_user.is_active:  # Bu holat bo'lmasligi kerak, agar get_user_by_username_for_auth to'g'ri ishlasa
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


# --- Maxsus rollar uchun Dependency lar ---
# Bu dependency'lar SecurityScopes dan foydalanib, get_current_user ni chaqiradi
# va qo'shimcha qulaylik yaratadi.

def require_role(required_roles: Union[str, List[str]]):
    """
    Decorator yoki Dependency yaratuvchi funksiya, kerakli rollarni tekshiradi.
    Misol: Depends(require_role(settings.ADMIN_ROLE_NAME))
           Depends(require_role([settings.MANAGER_ROLE_NAME, settings.ADMIN_ROLE_NAME]))
    """
    if isinstance(required_roles, str):
        required_roles_list = [required_roles]
    else:
        required_roles_list = required_roles

    async def role_checker(
            current_user_for_role_check: UserModel = Depends(get_current_user)):  # security_scopes bu yerda kerak emas
        # get_current_user ichida scopes tekshirilmaydi, faqat token validatsiyasi va user mavjudligi
        # Rolni bu yerda alohida tekshiramiz
        user_role_name = current_user_for_role_check.role.name
        if user_role_name not in required_roles_list:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required role(s): {', '.join(required_roles_list)}. Your role: {user_role_name}."
            )
        if not current_user_for_role_check.is_active:  # Yana bir bor ishonch hosil qilish
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user.")
        return current_user_for_role_check

    return role_checker


async def get_current_admin_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    # get_current_user endpoint uchun kerakli scopes bilan chaqirilishi kerak
    # Buni routerda `dependencies=[Security(get_current_user, scopes=[settings.ADMIN_ROLE_NAME])]`
    # orqali qilish mumkin. Yoki bu yerda qo'lda tekshirish:
    if current_user.role.name != settings.ADMIN_ROLE_NAME:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin role required. Your role: {current_user.role.name}"
        )
    return current_user  # is_active allaqachon get_current_user da tekshirilgan


async def get_current_manager_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    # Admin ham menejer ishlarini qila oladi
    if current_user.role.name not in [settings.MANAGER_ROLE_NAME, settings.ADMIN_ROLE_NAME]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Manager or Admin role required. Your role: {current_user.role.name}"
        )
    return current_user


async def get_current_chef_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    # Admin ham oshpaz ishlarini qila oladi (agar kerak bo'lsa)
    # Yoki qat'iyroq: current_user.role.name == settings.CHEF_ROLE_NAME
    if current_user.role.name not in [settings.CHEF_ROLE_NAME, settings.ADMIN_ROLE_NAME,
                                      settings.MANAGER_ROLE_NAME]:  # Menejer ham ovqat berishi mumkinmi? Talabga qarab. Hozircha yo'q.
        # Talabda "Oshpaz: Faqat ovqat berish imkoniyati." deyilgan. Admin hamma narsani qila oladi.
        # Demak, faqat Oshpaz va Admin.
        if current_user.role.name not in [settings.CHEF_ROLE_NAME, settings.ADMIN_ROLE_NAME]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Chef or Admin role required for this action. Your role: {current_user.role.name}"
            )
    return current_user


# --- Token orqali foydalanuvchi ma'lumotlarini olish (WebSocket uchun yordamchi) ---
# Bu funksiya Depends siz ishlatiladi, shuning uchun xatoliklarni o'zi handle qilishi kerak
def get_user_from_token(db: Session, token: str) -> Optional[UserModel]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if not username:
            return None
        user = get_user_by_username_for_auth(db, username=username)  # Aktiv va o'chirilmagan
        return user
    except JWTError:
        return None
    except Exception:  # Boshqa kutilmagan xatoliklar
        return None