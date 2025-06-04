# app/utils.py
from sqlalchemy.orm import Session
from app import crud, schemas, models
from app.config import settings


def create_initial_data(db: Session):
    """
    Ilova uchun boshlang'ich ma'lumotlarni (rollar, admin foydalanuvchisi,
    birliklar, bildirishnoma turlari) yaratadi.
    Bu funksiya ilova birinchi marta ishga tushganda yoki
    /api/auth/setup-initial-data endpointi orqali chaqirilishi mumkin.
    Funksiya idempotent bo'lishi kerak (qayta chaqirilganda xatolik bermasligi yoki
    mavjud ma'lumotlarni buzmasligi kerak).
    """
    print("INFO:     Checking and creating initial data if necessary...")

    # 1. Rollarni yaratish
    roles_to_create = [
        schemas.RoleCreate(name=settings.ADMIN_ROLE_NAME, description="Tizim administratori, barcha huquqlarga ega."),
        schemas.RoleCreate(name=settings.MANAGER_ROLE_NAME,
                           description="Omborxona menejeri, mahsulotlar, ovqatlar va hisobotlarni boshqaradi."),
        schemas.RoleCreate(name=settings.CHEF_ROLE_NAME,
                           description="Oshpaz, ovqat berish va mavjud ovqatlarni ko'rish huquqiga ega."),
    ]
    created_roles_map = {}  # Nomi bo'yicha ID sini saqlash uchun
    for role_data in roles_to_create:
        role = crud.get_role_by_name(db, name=role_data.name)
        if not role:
            role = crud.create_role(db, role_data)
            print(f"INFO:     Role '{role.name}' created.")
        # else:
        # print(f"INFO:     Role '{role.name}' already exists.")
        created_roles_map[role.name] = role.id

    # 2. Admin foydalanuvchisini yaratish (agar yo'q bo'lsa)
    admin_username = "admin"  # Buni ham configdan olish mumkin
    admin_default_password = "adminpassword"  # DIQQAT: Bu parolni o'zgartirish kerak!

    admin_user = crud.get_user_by_username(db, username=admin_username)  # Aktiv yoki noaktivligini tekshirmaydi
    if not admin_user:
        admin_role_id = created_roles_map.get(settings.ADMIN_ROLE_NAME)
        if admin_role_id:
            admin_schema = schemas.UserCreate(
                username=admin_username,
                full_name="Tizim Bosh Admini",
                password=admin_default_password,
                role_id=admin_role_id
            )
            crud.create_user(db, admin_schema)
            print(
                f"INFO:     Admin user '{admin_username}' with default password '{admin_default_password}' created. PLEASE CHANGE THE PASSWORD!")
        else:
            print(f"WARNING:  Could not create admin user because '{settings.ADMIN_ROLE_NAME}' role ID was not found.")
    # else:
    # print(f"INFO:     Admin user '{admin_username}' already exists.")

    # 3. Asosiy o'lchov birliklarini yaratish
    units_to_create = [
        schemas.UnitCreate(name="gramm", short_name="gr"),
        schemas.UnitCreate(name="kilogramm", short_name="kg"),
        schemas.UnitCreate(name="litr", short_name="l"),
        schemas.UnitCreate(name="millilitr", short_name="ml"),
        schemas.UnitCreate(name="dona", short_name="dona"),
        schemas.UnitCreate(name="qoshiq", short_name="qoshiq"),
        schemas.UnitCreate(name="stakan", short_name="stakan"),
    ]
    for unit_data in units_to_create:
        unit = crud.get_unit_by_name(db, name=unit_data.name)
        if not unit:
            # Qisqa nomi bo'yicha ham tekshirish (agar unique bo'lsa)
            unit_by_short_name = db.query(models.Unit).filter(models.Unit.short_name == unit_data.short_name).first()
            if not unit_by_short_name:
                crud.create_unit(db, unit_data)
                print(f"INFO:     Unit '{unit_data.name}' ({unit_data.short_name}) created.")
        # else:
        # print(f"INFO:     Unit '{unit_data.name}' already exists.")

    # 4. Asosiy bildirishnoma turlarini yaratish
    # crud.py da aniqlangan nomlardan foydalanish
    notification_types_to_create = [
        schemas.NotificationTypeCreate(name=crud.MIN_QUANTITY_NOTIFICATION_TYPE_NAME,
                                       description="Mahsulot miqdori minimal darajadan kamayganda yuboriladi."),
        schemas.NotificationTypeCreate(name=crud.SUSPICIOUS_REPORT_NOTIFICATION_TYPE_NAME,
                                       description="Oylik hisobotda katta farq (shubhali holat) aniqlanganda yuboriladi."),
        schemas.NotificationTypeCreate(name="info", description="Umumiy ma'lumot va axborot uchun."),
        schemas.NotificationTypeCreate(name="meal_served_event",
                                       description="Yangi ovqat berilganligi haqida WebSocket uchun hodisa (DBga yozilmasligi mumkin)."),
        # Bu DBga yozilmasligi ham mumkin
        schemas.NotificationTypeCreate(name="stock_update_event",
                                       description="Ombor yangilanganligi haqida WebSocket uchun hodisa."),
        schemas.NotificationTypeCreate(name="new_feature_announcement",
                                       description="Tizimga yangi funksiya qo'shilganligi haqida e'lon."),
    ]
    for nt_data in notification_types_to_create:
        nt = crud.get_notification_type_by_name(db, name=nt_data.name)
        if not nt:
            crud.create_notification_type(db, nt_data)
            print(f"INFO:     Notification type '{nt_data.name}' created.")
        # else:
        # print(f"INFO:     Notification type '{nt_data.name}' already exists.")

    print("INFO:     Initial data setup process finished.")

