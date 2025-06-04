# app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_
from datetime import datetime, timedelta, date
from typing import List, Optional, Tuple, Dict, Any, Type
import math

from app import models, schemas
from app.config import settings
from app.models import MonthlyReport, Notification


# --- Role CRUD  ---
def get_role(db: Session, role_id: int) -> Optional[models.Role]:
    return db.query(models.Role).filter(models.Role.id == role_id).first()


def get_role_by_name(db: Session, name: str) -> Optional[models.Role]:
    return db.query(models.Role).filter(models.Role.name == name).first()


def get_roles(db: Session, skip: int = 0, limit: int = 100) -> List[models.Role]:
    return db.query(models.Role).offset(skip).limit(limit).all()


def create_role(db: Session, role: schemas.RoleCreate) -> models.Role:
    db_role = models.Role(name=role.name, description=role.description)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


# --- Unit CRUD ---
def get_unit(db: Session, unit_id: int) -> Optional[models.Unit]:
    return db.query(models.Unit).filter(models.Unit.id == unit_id).first()


def get_unit_by_name(db: Session, name: str) -> Optional[models.Unit]:
    return db.query(models.Unit).filter(models.Unit.name == name).first()


def get_units(db: Session, skip: int = 0, limit: int = 100) -> list[Type[models.Unit]]:
    return db.query(models.Unit).offset(skip).limit(limit).all()


def create_unit(db: Session, unit: schemas.UnitCreate) -> models.Unit:
    db_unit = models.Unit(name=unit.name, short_name=unit.short_name)
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return db_unit



# --- User CRUD (Parol xeshlash security.py da) ---
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id, models.User.deleted_at == None).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username, models.User.deleted_at == None).first()


def get_active_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(
        models.User.username == username,
        models.User.is_active == True,
        models.User.deleted_at == None
    ).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[Type[models.User]]:
    return db.query(models.User).filter(models.User.deleted_at == None).order_by(models.User.id).offset(skip).limit(
        limit).all()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    from app.security import get_password_hash
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        full_name=user.full_name,
        password_hash=hashed_password,
        role_id=user.role_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    from app.security import get_password_hash  # Import

    update_data = user_update.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:  # Parol None yoki bo'sh emasligini tekshirish
        hashed_password = get_password_hash(update_data["password"])
        db_user.password_hash = hashed_password

    update_data.pop("password", None)

    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def soft_delete_user(db: Session, user_id: int) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if db_user:
        db_user.deleted_at = datetime.now()
        db_user.is_active = False
        db.commit()
        db.refresh(db_user)
    return db_user


def update_user_last_login(db: Session, user_id: int):
    db_user = get_user(db, user_id)  # deleted_at == None bo'lganlarni oladi
    if db_user and db_user.is_active:  # Faqat aktiv user uchun
        db_user.last_login = datetime.now()
        db.commit()


# --- Product CRUD ---
def get_product(db: Session, product_id: int) -> Optional[models.Product]:
    return db.query(models.Product).filter(models.Product.id == product_id, models.Product.deleted_at == None).first()


def get_product_by_name(db: Session, name: str) -> Optional[models.Product]:
    return db.query(models.Product).filter(models.Product.name == name, models.Product.deleted_at == None).first()



def create_product(db: Session, product: schemas.ProductCreate, user_id: int) -> models.Product:
    db_product = models.Product(**product.model_dump(), created_by=user_id)
    db.add(db_product)
    # db.commit()
    db.flush()
    db.refresh(db_product)
    return db_product


def update_product(db: Session, product_id: int, product_update: schemas.ProductUpdate) -> Optional[models.Product]:
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    update_data = product_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
    db_product.updated_at = datetime.now()
    # db.commit()
    db.refresh(db_product)
    return db_product


def soft_delete_product(db: Session, product_id: int) -> Optional[models.Product]:
    db_product = get_product(db, product_id)
    if db_product:
        db_product.deleted_at = datetime.now()
        # db.commit()
        db.refresh(db_product)
    return db_product


# app/crud.py ichida
from sqlalchemy.orm import selectinload # Import

# --- ProductDelivery CRUD ---
def get_product_delivery(db: Session, delivery_id: int) -> Optional[models.ProductDelivery]:
    return db.query(models.ProductDelivery).filter(models.ProductDelivery.id == delivery_id).first()


def get_product_deliveries(db: Session, product_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> list[
    Type[models.ProductDelivery]]:
    query = db.query(models.ProductDelivery)
    if product_id:
        query = query.filter(models.ProductDelivery.product_id == product_id)
    return query.order_by(models.ProductDelivery.delivery_date.desc()).offset(skip).limit(limit).all()


def create_product_delivery(db: Session, delivery: schemas.ProductDeliveryCreate,
                            user_id: int) -> models.ProductDelivery:

    db_delivery = models.ProductDelivery(
        product_id=delivery.product_id,
        quantity=delivery.quantity,
        delivery_date=delivery.delivery_date,  # Bu schemas.ProductDeliveryCreate dan keladi
        supplier=delivery.supplier,
        price=delivery.price,
        received_by=user_id

    )
    db.add(db_delivery)
    db.flush()
    db.refresh(db_delivery)
    return db_delivery

# --- Ombordagi mahsulot miqdorini hisoblash ---
def get_product_current_quantity(db: Session, product_id: int) -> float:
    total_delivered = db.query(func.sum(models.ProductDelivery.quantity)).filter(
        models.ProductDelivery.product_id == product_id
    ).scalar() or 0.0
    total_used = db.query(func.sum(models.ServingDetail.quantity_used)).filter(
        models.ServingDetail.product_id == product_id
    ).scalar() or 0.0
    return total_delivered - total_used


def get_all_products_with_current_quantity(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        name_filter: Optional[str] = None,
        low_stock_only: Optional[bool] = False
) -> List[schemas.ProductWithQuantity]:
    products_orm = get_products(db, name_filter=name_filter,
                                limit=10000)

    products_with_quantity_list = []
    for p_orm in products_orm:
        current_quantity = get_product_current_quantity(db, p_orm.id)

        if low_stock_only and current_quantity >= p_orm.min_quantity:
            continue

        try:
            product_schema = schemas.Product.model_validate(p_orm)
        except Exception as e:
            print(f"DEBUG: Error validating product ORM to schema for product ID {p_orm.id}: {e}")
            # Agar unit yuklanmagan bo'lsa, uni alohida yuklashga harakat qilish
            if not hasattr(p_orm, 'unit') or p_orm.unit is None:
                # Bu holatda p_orm.unit ni alohida yuklash kerak, lekin bu N+1 muammosiga olib keladi.
                # Eng yaxshisi get_products da selectinload ishlatish.
                # Hozircha, xatolik bo'lsa, unit=None qilib o'tkazib yuboramiz (noto'g'ri, lekin vaqtinchalik)
                print(f"WARN: Unit not loaded for product {p_orm.name}. Consider using selectinload in get_products.")
                # Vaqtincha, agar unit yuklanmagan bo'lsa, sxemani unitsiz yaratamiz (bu ham xato)
                # To'g'ri yechim: get_products() da options(selectinload(models.Product.unit))
                # Hozirgi kodda get_products da selectinload yo'q.
                # Keling, get_products ni o'zgartiramiz.
            pass  # Xatolikni o'tkazib yuborish (yaxshi emas)
            # Yoki sxemani yaratishda xatolik bo'lsa, bu productni o'tkazib yuboramiz
            # continue

        products_with_quantity_list.append(
            schemas.ProductWithQuantity(
                **product_schema.model_dump(),  # Bu `unit` ni ham o'z ichiga oladi
                current_quantity=current_quantity
                # Bu qatorni olib tashlaymiz:
                # unit=schemas.Unit.model_validate(p_orm.unit) if p_orm.unit else None
            )
        )

    # Skip va limitni filterlangan ro'yxatga qo'llash
    return products_with_quantity_list[skip: skip + limit]


# `get_products` funksiyasiga `selectinload` qo'shish:
def get_products(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        name_filter: Optional[str] = None,
) -> list[Type[models.Product]]:
    query = db.query(models.Product).options(
        selectinload(models.Product.unit),  # `unit` relationshipini oldindan yuklash
        selectinload(models.Product.created_by_user)  # Agar `created_by_user` ham kerak bo'lsa
    ).filter(models.Product.deleted_at == None)

    if name_filter:
        query = query.filter(models.Product.name.ilike(f"%{name_filter}%"))
    return query.order_by(models.Product.name).offset(skip).limit(limit).all()

def get_meal(db: Session, meal_id: int) -> Optional[models.Meal]:
    return db.query(models.Meal).options(
        selectinload(models.Meal.ingredients).selectinload(models.MealIngredient.product).selectinload(
            models.Product.unit),
        selectinload(models.Meal.ingredients).selectinload(models.MealIngredient.unit)
    ).filter(models.Meal.id == meal_id, models.Meal.deleted_at == None).first()



def get_meal_by_name(db: Session, name: str) -> Optional[models.Meal]:
    return db.query(models.Meal).filter(models.Meal.name == name, models.Meal.deleted_at == None).first()


def get_meals(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        active_only: Optional[bool] = None,  # None - hammasi, True - faqat aktiv, False - faqat noaktiv
        name_filter: Optional[str] = None
) -> list[Type[models.Meal]]:
    query = db.query(models.Meal).filter(models.Meal.deleted_at == None)
    if active_only is not None:  # Agar None bo'lmasa
        query = query.filter(models.Meal.is_active == active_only)
    if name_filter:
        query = query.filter(models.Meal.name.ilike(f"%{name_filter}%"))
    return query.order_by(models.Meal.name).offset(skip).limit(limit).all()


def create_meal(db: Session, meal_data: schemas.MealCreate, user_id: int) -> models.Meal:
    db_meal = models.Meal(
        name=meal_data.name,
        description=meal_data.description,
        is_active=meal_data.is_active,
        created_by=user_id
    )
    db.add(db_meal)
    db.flush()
    for ingredient_data in meal_data.ingredients:
        db_ingredient = models.MealIngredient(
            meal_id=db_meal.id,
            product_id=ingredient_data.product_id,
            quantity_per_portion=ingredient_data.quantity_per_portion,
            unit_id=ingredient_data.unit_id
        )
        db.add(db_ingredient)
    # db.commit()
    db.refresh(db_meal)
    return db_meal


def update_meal(db: Session, meal_id: int, meal_update_data: schemas.MealUpdate, user_id: int) -> Optional[models.Meal]:
    db_meal = get_meal(db, meal_id)
    if not db_meal:
        return None
    update_data = meal_update_data.model_dump(exclude_unset=True, exclude={"ingredients"})
    for key, value in update_data.items():
        setattr(db_meal, key, value)
    db_meal.updated_at = datetime.now()

    if meal_update_data.ingredients is not None:  # Agar ingredientlar yuborilgan bo'lsa (bo'sh ro'yxat ham bo'lishi mumkin)
        # Eskilarini o'chirish
        db.query(models.MealIngredient).filter(models.MealIngredient.meal_id == meal_id).delete(
            synchronize_session=False)
        # Yangilarini qo'shish
        for ingredient_data in meal_update_data.ingredients:
            db_ingredient = models.MealIngredient(
                meal_id=db_meal.id,
                product_id=ingredient_data.product_id,
                quantity_per_portion=ingredient_data.quantity_per_portion,
                unit_id=ingredient_data.unit_id
            )
            db.add(db_ingredient)
    # db.commit()
    db.refresh(db_meal)

    return get_meal(db, meal_id)  # Yangilangan mealni qaytarish (ingredientlar bilan)


def soft_delete_meal(db: Session, meal_id: int) -> Optional[models.Meal]:
    db_meal = get_meal(db, meal_id)
    if db_meal:
        db_meal.deleted_at = datetime.now()
        db_meal.is_active = False
        # db.commit()
        db.refresh(db_meal)
    return db_meal


def create_meal_serving(db: Session, serving_data: schemas.MealServingCreate, user_id: int) -> Tuple[
    Optional[models.MealServing], Optional[str]]:
    db_meal = get_meal(db, serving_data.meal_id)  # Bu ingredientlarni va ularning unit/product.unitlarini yuklaydi
    if not db_meal:
        return None, "Ovqat topilmadi."
    if not db_meal.is_active:
        return None, f"'{db_meal.name}' ovqati hozirda faol emas."
    if not db_meal.ingredients:
        return None, f"'{db_meal.name}' ovqati uchun ingredientlar retseptda belgilanmagan."

    # Bu dictionaryda mahsulot ID sini kalit, ombordan olinadigan jami miqdorni
    # (mahsulotning ombordagi ASOSIY BIRLIGIDA) qiymat sifatida saqlaymiz.
    product_consumption_in_base_units: Dict[int, float] = {}

    for ingredient_in_recipe in db_meal.ingredients:
        product_in_db = ingredient_in_recipe.product
        ingredient_unit_in_recipe = ingredient_in_recipe.unit

        if not (product_in_db and product_in_db.unit and ingredient_unit_in_recipe):
            # Bu holat get_meal to'g'ri selectinload qilgan bo'lsa, yuzaga kelmasligi kerak
            product_name_debug = product_in_db.name if product_in_db else f"(Product ID: {ingredient_in_recipe.product_id})"
            return None, f"'{db_meal.name}' ovqatining ('{product_name_debug}') ingredienti uchun mahsulot yoki birlik ma'lumotlari to'liq emas. Iltimos, retseptni tekshiring."

        quantity_per_portion_recipe = ingredient_in_recipe.quantity_per_portion
        unit_short_recipe = ingredient_unit_in_recipe.short_name
        unit_short_product_base = product_in_db.unit.short_name

        if quantity_per_portion_recipe <= 0:  # Porsiyaga sarf 0 yoki manfiy bo'lsa
            print(
                f"INFO: CRUD_SERVING - Ingredient '{product_in_db.name}' in meal '{db_meal.name}' has non-positive quantity per portion. Skipping.")
            continue  # Bu ingredientni hisobga olmaymiz

        total_quantity_needed_recipe_unit = quantity_per_portion_recipe * serving_data.portions_served

        # Kerakli miqdorni mahsulotning ombordagi asosiy birligiga konvertatsiya qilish
        total_quantity_needed_product_base_unit = _convert_units_for_comparison(
            total_quantity_needed_recipe_unit,
            unit_short_recipe,
            unit_short_product_base
        )

        if total_quantity_needed_product_base_unit is None:
            # Konvertatsiya qilinmadi (birliklar mos kelmadi)
            return None, (f"'{product_in_db.name}' uchun birliklar mos kelmaydi: "
                          f"Retseptda '{ingredient_unit_in_recipe.name}' ishlatilgan, lekin omborda asosiy birlik "
                          f"'{product_in_db.unit.name}'. Bu birliklar o'rtasida avtomatik konvertatsiya yo'q.")

        current_stock_in_product_base_unit = get_product_current_quantity(db,
                                                                          product_in_db.id)  # Ombordagi miqdor (asosiy birlikda)

        print(f"SERVING_DEBUG: Product: {product_in_db.name} (ID: {product_in_db.id})")
        print(f"SERVING_DEBUG:   Recipe demands: {total_quantity_needed_recipe_unit:.3f} {unit_short_recipe}")
        print(
            f"SERVING_DEBUG:   Converted demand (in base unit): {total_quantity_needed_product_base_unit:.3f} {unit_short_product_base}")
        print(
            f"SERVING_DEBUG:   Stock has (in base unit): {current_stock_in_product_base_unit:.3f} {unit_short_product_base}")

        if current_stock_in_product_base_unit < total_quantity_needed_product_base_unit:
            return None, (f"'{product_in_db.name}' mahsuloti yetarli emas. "
                          f"Kerak: {total_quantity_needed_product_base_unit:.3f} {unit_short_product_base}, "
                          f"Mavjud: {current_stock_in_product_base_unit:.3f} {unit_short_product_base}")

        # Agar shu mahsulot bir necha marta (turli birliklarda) retseptda uchrasa, ularni yig'ish kerak
        product_consumption_in_base_units[product_in_db.id] = \
            product_consumption_in_base_units.get(product_in_db.id, 0.0) + total_quantity_needed_product_base_unit

    # Tranzaksiyani boshlash va DBga yozish
    if not product_consumption_in_base_units and db_meal.ingredients:
        # Bu holat agar barcha ingredientlar quantity_per_portion <= 0 bo'lsa yuzaga kelishi mumkin
        print(f"WARN: CRUD_SERVING - No ingredients to consume for meal '{db_meal.name}'. Check recipe quantities.")
        # Yoki xatolik qaytarish mumkin, agar ovqatda ingredient bo'lishi shart bo'lsa.
        # Hozircha, ovqat berildi deb hisoblaymiz (agar ingredientlar 0 sarf bilan belgilangan bo'lsa).

    try:
        db_serving = models.MealServing(
            meal_id=serving_data.meal_id,
            portions_served=serving_data.portions_served,
            served_by=user_id,
            notes=serving_data.notes,
            served_at=datetime.now()
        )
        db.add(db_serving)
        db.flush()

        for product_id_key, quantity_to_consume in product_consumption_in_base_units.items():
            db_serving_detail = models.ServingDetail(
                serving_id=db_serving.id,
                product_id=product_id_key,
                quantity_used=quantity_to_consume
            )
            db.add(db_serving_detail)

        # db.commit()
        return get_meal_serving_with_details(db, db_serving.id), None  # To'liq ma'lumot bilan qaytarish
    except Exception as e:
        db.rollback()
        print(f"ERROR: CRUD_SERVING - Exception during database transaction: {str(e)}")
        return None, f"Ovqat berishni ma'lumotlar bazasiga yozishda xatolik yuz berdi."


def get_meal_serving(db: Session, serving_id: int) -> Optional[models.MealServing]:
    return db.query(models.MealServing).filter(models.MealServing.id == serving_id).first()


def get_meal_serving_with_details(db: Session, serving_id: int) -> Optional[models.MealServing]:
    # Bu serving_details va product/unit larni ham yuklaydi
    return db.query(models.MealServing).options(
        selectinload(models.MealServing.serving_details).selectinload(models.ServingDetail.product).selectinload(models.Product.unit),
        selectinload(models.MealServing.meal),
        selectinload(models.MealServing.served_by_user).selectinload(models.User.role)
    ).filter(models.MealServing.id == serving_id).first()


def get_meal_servings(
        db: Session, skip: int = 0, limit: int = 100, meal_id: Optional[int] = None,
        user_id: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None
) -> list[Type[models.MealServing]]:
    query = db.query(models.MealServing)
    if meal_id:
        query = query.filter(models.MealServing.meal_id == meal_id)
    if user_id:
        query = query.filter(models.MealServing.served_by == user_id)
    if start_date:
        query = query.filter(models.MealServing.served_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(models.MealServing.served_at <= datetime.combine(end_date, datetime.max.time()))
    return query.order_by(models.MealServing.served_at.desc()).offset(skip).limit(limit).all()


def get_serving_details_for_serving(db: Session, serving_id: int) -> list[Type[models.ServingDetail]]:
    return db.query(models.ServingDetail).filter(models.ServingDetail.serving_id == serving_id).all()


# --- Porsiya hisoblash (PossibleMeals) ---
# Bu funksiyalar WS yubormaydi, Celery taski o'zi Redisga yozadi yoki API endpoint WS yuboradi

def calculate_possible_portions_for_meal(db: Session, meal_id: int) -> Tuple[int, Optional[int]]:
    meal = get_meal(db, meal_id)  # Bu ingredientlarni va ularning unit/product.unitlarini yuklaydi
    if not meal: return 0, None  # Ovqat topilmadi
    if not meal.is_active: return 0, None  # Faol bo'lmagan ovqat uchun hisoblamaymiz
    if not meal.ingredients: return 0, None  # Ingredientlarsiz ovqatdan 0 porsiya (yoki cheksiz, talabga qarab)

    min_possible_portions = float('inf')
    limiting_product_id_val: Optional[int] = None

    if not meal.ingredients:  # Agar ingredientlar ro'yxati bo'sh bo'lsa
        return 0, None  # Yoki juda katta son (cheksiz deb hisoblash uchun), lekin hozircha 0

    for ingredient_in_recipe in meal.ingredients:
        product_in_db = ingredient_in_recipe.product
        ingredient_unit_in_recipe = ingredient_in_recipe.unit

        if not (product_in_db and product_in_db.unit and ingredient_unit_in_recipe):
            print(
                f"WARN: CRUD_PORTION_CALC - Ingredient data incomplete for meal '{meal.name}', product_id {ingredient_in_recipe.product_id}. Cannot calculate portions for this meal accurately.")
            return 0, ingredient_in_recipe.product_id  # Bu mahsulot muammoli, 0 porsiya

        quantity_per_portion_recipe = ingredient_in_recipe.quantity_per_portion

        if quantity_per_portion_recipe <= 1e-9:  # Juda kichik yoki nol qiymat (bo'lish xatoligini oldini olish)
            # Bu ingredient deyarli sarflanmaydi, porsiyani cheklamaydi
            continue

        unit_short_recipe = ingredient_unit_in_recipe.short_name
        unit_short_product_base = product_in_db.unit.short_name

        # 1 porsiya uchun kerakli miqdorni mahsulotning ombordagi asosiy birligiga konvertatsiya qilish
        qty_per_portion_in_product_base_unit = _convert_units_for_comparison(
            quantity_per_portion_recipe,
            unit_short_recipe,
            unit_short_product_base
        )

        if qty_per_portion_in_product_base_unit is None:
            # Birliklar mos kelmadi va konvertatsiya qilinmadi.
            # Bu ovqatni tayyorlab bo'lmaydi, shu ingredient tufayli.
            print(
                f"WARN: CRUD_PORTION_CALC - Cannot convert units for {product_in_db.name} ({unit_short_recipe} to {unit_short_product_base}) in meal '{meal.name}'. Assuming 0 portions possible for this meal.")
            return 0, product_in_db.id  # Shu mahsulot cheklovchi deb belgilanadi

        if qty_per_portion_in_product_base_unit <= 1e-9:  # Konvertatsiyadan keyin ham juda kichik
            print(
                f"INFO: CRUD_PORTION_CALC - Ingredient '{product_in_db.name}' in meal '{meal.name}' has near-zero quantity per portion after conversion. Skipping as a limiting factor.")
            continue

        current_stock_in_product_base_unit = get_product_current_quantity(db, product_in_db.id)

        if current_stock_in_product_base_unit <= 1e-9:  # Agar omborda shu mahsulot umuman yo'q bo'lsa
            min_possible_portions = 0
            limiting_product_id_val = product_in_db.id
            break  # Darhol 0 porsiya, boshqa ingredientlarni tekshirish shart emas

        # Agar bir porsiyaga kerakli miqdor ombordagidan ko'p bo'lsa (bu tekshiruv yuqorida qilingan)
        # if current_stock_in_product_base_unit < qty_per_portion_in_product_base_unit:
        #     min_possible_portions = 0
        #     limiting_product_id_val = product_in_db.id
        #     break

        portions_for_this_ingredient = math.floor(
            current_stock_in_product_base_unit / qty_per_portion_in_product_base_unit)

        if portions_for_this_ingredient < min_possible_portions:
            min_possible_portions = portions_for_this_ingredient
            limiting_product_id_val = product_in_db.id

    # Agar birorta ham ingredient porsiyani cheklamasa (masalan, hamma ingredientlar uchun qty_per_portion <=0 bo'lsa)
    # unda min_possible_portions float('inf') ligicha qoladi. Bunday holatda 0 qaytaramiz.
    final_portions = int(min_possible_portions) if min_possible_portions != float('inf') else 0

    # Agar porsiya 0 bo'lsa-yu, lekin limiting_product_id_val None bo'lsa (masalan, ingredientlar ro'yxati bo'sh bo'lsa)
    # Unda limiting_product_id_val ni None qilib qoldiramiz.
    # Agar porsiya > 0 bo'lsa, limiting_product_id_val None bo'lishi mumkin emas (agar ingredientlar bor bo'lsa).
    # Agar ingredientlar bo'sh bo'lsa, limiting_product_id_val None bo'ladi.

    if final_portions > 0 and limiting_product_id_val is None and meal.ingredients:
        # Bu g'alati holat, agar porsiya musbat bo'lsa, cheklovchi ingredient bo'lishi kerak.
        # Ehtimol, barcha ingredientlar cheksiz miqdorda mavjud deb hisoblangan.
        # Yoki faqat bitta ingredient bor va u yetarli. Bu holatda limiting_product_id_val None bo'lmaydi.
        # Bu shartga tushmasligi kerak.
        print(
            f"WARN: CRUD_PORTION_CALC - Calculated {final_portions} portions for meal '{meal.name}' but no limiting product identified. This might be an issue in logic if ingredients exist.")

    return final_portions, limiting_product_id_val


def update_all_possible_meal_portions(db: Session):
    active_meals = get_meals(db, active_only=True, limit=10000)

    # Avval barcha PossibleMeals yozuvlarini o'chirish yoki meal_id bo'yicha topib yangilash
    # Hozircha, mavjudlarini topib, yangilaymiz, yo'qlarini qo'shamiz.
    # Noaktiv bo'lib qolgan ovqatlar uchun PossibleMeals ni o'chiramiz.

    all_possible_meal_entries = {pm.meal_id: pm for pm in db.query(models.PossibleMeals).all()}
    active_meal_ids = {m.id for m in active_meals}

    for meal in active_meals:
        possible_portions, limiting_product_id = calculate_possible_portions_for_meal(db, meal.id)

        if meal.id in all_possible_meal_entries:  # Update existing
            existing_pm = all_possible_meal_entries[meal.id]
            existing_pm.possible_portions = possible_portions
            existing_pm.limiting_product_id = limiting_product_id
            existing_pm.calculated_at = datetime.now()
        else:  # Create new
            db_possible_meal = models.PossibleMeals(
                meal_id=meal.id,
                possible_portions=possible_portions,
                limiting_product_id=limiting_product_id,
                calculated_at=datetime.now()
            )
            db.add(db_possible_meal)

    # Remove entries for meals that are no longer active or deleted
    for meal_id_in_pm, pm_entry in all_possible_meal_entries.items():
        if meal_id_in_pm not in active_meal_ids:
            db.delete(pm_entry)

    db.commit()


def get_possible_meal_portions_list(db: Session, limit: int = 50) -> List[schemas.MealPortionInfo]:
    possible_meals_data = db.query(models.PossibleMeals) \
        .join(models.Meal, models.PossibleMeals.meal_id == models.Meal.id) \
        .filter(models.Meal.is_active == True, models.Meal.deleted_at == None) \
        .order_by(models.PossibleMeals.possible_portions.asc()) \
        .limit(limit).all()

    result = []
    for pm in possible_meals_data:
        limiting_product_name = pm.limiting_product.name if pm.limiting_product else None
        limiting_product_unit = pm.limiting_product.unit.short_name if pm.limiting_product and pm.limiting_product.unit else None
        result.append(schemas.MealPortionInfo(
            meal_id=pm.meal.id, meal_name=pm.meal.name,
            possible_portions=pm.possible_portions,
            limiting_ingredient_name=limiting_product_name,
            limiting_ingredient_unit=limiting_product_unit
        ))
    return result


# --- NotificationType CRUD ---
MIN_QUANTITY_NOTIFICATION_TYPE_NAME = "low_stock"
SUSPICIOUS_REPORT_NOTIFICATION_TYPE_NAME = "suspicious_report"


def get_notification_type(db: Session, type_id: int) -> Optional[models.NotificationType]:
    return db.query(models.NotificationType).filter(models.NotificationType.id == type_id).first()


def get_notification_type_by_name(db: Session, name: str) -> Optional[models.NotificationType]:
    return db.query(models.NotificationType).filter(models.NotificationType.name == name).first()


def get_notification_types(db: Session, skip: int = 0, limit: int = 100) -> list[Type[models.NotificationType]]:
    return db.query(models.NotificationType).offset(skip).limit(limit).all()


def create_notification_type(db: Session, nt_type: schemas.NotificationTypeCreate) -> models.NotificationType:
    db_nt_type = models.NotificationType(**nt_type.model_dump())
    db.add(db_nt_type)
    db.commit()
    db.refresh(db_nt_type)
    return db_nt_type


# --- Notification CRUD ---
def create_notification(db: Session, notification_data: schemas.NotificationCreate) -> models.Notification:
    db_notification = models.Notification(**notification_data.model_dump())
    db.add(db_notification)
    db.commit()  # Darhol commit qilish
    db.refresh(db_notification)
    return db_notification


def get_notifications_for_user(db: Session, user_id: int, skip: int = 0, limit: int = 20, unread_only: bool = False) -> \
        list[Type[Notification]]:
    query = db.query(models.Notification).filter(
        or_(models.Notification.user_id == user_id, models.Notification.user_id == None)
    )
    if unread_only:
        query = query.filter(models.Notification.is_read == False)
    return query.order_by(models.Notification.created_at.desc()).offset(skip).limit(limit).all()


def mark_notification_as_read(db: Session, notification_id: int, user_id: int) -> Optional[models.Notification]:
    db_notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        or_(models.Notification.user_id == user_id, models.Notification.user_id == None)
    ).first()
    if db_notification and not db_notification.is_read:
        db_notification.is_read = True
        db.commit()
        db.refresh(db_notification)
    return db_notification


def mark_all_notifications_as_read_for_user(db: Session, user_id: int) -> int:
    updated_count = db.query(models.Notification).filter(
        or_(models.Notification.user_id == user_id, models.Notification.user_id == None),
        models.Notification.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()
    return updated_count


# --- Ogohlantirishlar uchun DB yozuvlarini yaratish (WS yuborish Celery taskida bo'ladi) ---
def create_low_stock_db_notification(db: Session, product: models.Product, current_quantity: float) -> None | Notification | \
                                                                                                       Type[
                                                                                                           Notification]:
    nt_type = get_notification_type_by_name(db, MIN_QUANTITY_NOTIFICATION_TYPE_NAME)
    if not nt_type: return None
    message_text = f"Mahsulot miqdori kam qoldi: '{product.name}'. Minimal: {product.min_quantity} {product.unit.short_name}, Joriy: {current_quantity:.2f} {product.unit.short_name}."

    # Bu xabar uchun allaqachon o'qilmagan umumiy notification bormi?
    existing_notification = db.query(models.Notification).filter(
        models.Notification.notification_type_id == nt_type.id,
        models.Notification.message.like(f"%'{product.name}'%"),  # Aniqroq qidirish kerak bo'lishi mumkin
        models.Notification.is_read == False,
        models.Notification.user_id == None
    ).first()
    if not existing_notification:
        return create_notification(db, schemas.NotificationCreate(message=message_text, notification_type_id=nt_type.id,
                                                                  user_id=None))
    return existing_notification  # Mavjudini qaytarish (agar logikaga mos kelsa)


def create_suspicious_report_db_notifications(db: Session, report: models.MonthlyReport) -> List[models.Notification]:
    nt_type = get_notification_type_by_name(db, SUSPICIOUS_REPORT_NOTIFICATION_TYPE_NAME)
    if not nt_type: return []

    message_text = f"Shubhali oylik hisobot: {report.report_month.strftime('%Y-%m')}. Farq: {report.difference_percentage}%."

    created_notifications = []
    admin_role = get_role_by_name(db, settings.ADMIN_ROLE_NAME)
    if admin_role:
        admins = db.query(models.User).filter(models.User.role_id == admin_role.id, models.User.is_active == True).all()
        for admin in admins:
            # Har bir admin uchun alohida notification yaratish (agar allaqachon o'qilmagani bo'lmasa)
            existing_notif = db.query(models.Notification).filter(
                models.Notification.notification_type_id == nt_type.id,
                models.Notification.user_id == admin.id,
                models.Notification.message == message_text,  # Yoki report_id ga bog'lash
                models.Notification.is_read == False
            ).first()
            if not existing_notif:
                notif = create_notification(db, schemas.NotificationCreate(message=message_text,
                                                                           notification_type_id=nt_type.id,
                                                                           user_id=admin.id))
                created_notifications.append(notif)
    return created_notifications

def _convert_units_for_comparison(
        quantity_recipe: float,
        unit_short_recipe: str,
        unit_short_base_product: str
) -> Optional[float]:
    """
    Retseptdagi miqdorni mahsulotning ombordagi asosiy birligiga o'tkazadi.
    - Agar birliklar bir xil bo'lsa (nomi yoki qisqa nomi bo'yicha), miqdorni o'zgartirmaydi.
    - Faqat gramm <-> kilogramm va millilitr <-> litr juftliklarini konvertatsiya qiladi.
    - Boshqa mos kelmaydigan konvertatsiyalar uchun (masalan, "dona" vs "kg") None qaytaradi.
    """
    u_recipe_clean = unit_short_recipe.lower().strip()
    u_base_clean = unit_short_base_product.lower().strip()

    # 1. Agar birliklar bir xil bo'lsa
    if u_recipe_clean == u_base_clean:
        return quantity_recipe

    # 2. Og'irlik konvertatsiyasi (gramm <-> kilogramm)
    # Kengroq aliaslarni ishlatish
    gram_aliases = ["gr", "gramm", "g", "грамм", "гр"]
    kg_aliases = ["kg", "kilogramm", "килограмм", "кг"]

    if u_recipe_clean in gram_aliases and u_base_clean in kg_aliases:
        return quantity_recipe / 1000.0  # Retsept grammda, ombor kg da => kg ga o'tkazamiz
    if u_recipe_clean in kg_aliases and u_base_clean in gram_aliases:
        return quantity_recipe * 1000.0  # Retsept kg da, ombor grammda => grammga o'tkazamiz

    # 3. Hajm konvertatsiyasi (millilitr <-> litr)
    ml_aliases = ["ml", "millilitr", "мл", "миллилитr"]
    l_aliases = ["l", "litr", "литр", "л"]

    if u_recipe_clean in ml_aliases and u_base_clean in l_aliases:
        return quantity_recipe / 1000.0  # Retsept ml da, ombor l da => litrga o'tkazamiz
    if u_recipe_clean in l_aliases and u_base_clean in ml_aliases:
        return quantity_recipe * 1000.0  # Retsept l da, ombor ml da => millilitrga o'tkazamiz

    # 4. Agar yuqoridagi shartlarga tushmasa, birliklar har xil va
    #    biz qo'llab-quvvatlaydigan standart konvertatsiya yo'q.
    #    Bu "dona" vs "kg" kabi holatlarni ham o'z ichiga oladi.
    print(
        f"WARN: CRUD_UNIT_CONVERSION - Cannot convert from '{unit_short_recipe}' to '{unit_short_base_product}'. Units are incompatible or conversion is not supported.")
    return None

# --- Hisobotlar (Bu funksiyalar WS yubormaydi, Celery taski Redisga yozadi) ---
def get_monthly_report(db: Session, report_id: int) -> Optional[models.MonthlyReport]:
    return db.query(models.MonthlyReport).filter(models.MonthlyReport.id == report_id).first()

# def get_monthly_report(db: Session, report_id: int) -> Optional[models.MonthlyReport]:
#     return db.query(models.MonthlyReport).options(
#         selectinload(models.MonthlyReport.report_details).selectinload(models.ReportDetail.meal), # Meal obyektini yuklash
#         selectinload(models.MonthlyReport.report_details).selectinload(models.ReportDetail.product).selectinload(models.Product.unit) # Product va uning unitini yuklash
#     ).filter(models.MonthlyReport.id == report_id).first()

def get_monthly_reports(db: Session, skip: int = 0, limit: int = 100, year: Optional[int] = None,
                        month: Optional[int] = None) -> list[Type[MonthlyReport]]:
    query = db.query(models.MonthlyReport)
    if year: query = query.filter(extract('year', models.MonthlyReport.report_month) == year)
    if month: query = query.filter(extract('month', models.MonthlyReport.report_month) == month)
    return query.order_by(models.MonthlyReport.report_month.desc()).offset(skip).limit(limit).all()


def get_report_details_for_report(db: Session, report_id: int) -> list[Type[models.ReportDetail]]:
    return db.query(models.ReportDetail).filter(models.ReportDetail.report_id == report_id).all()



# --- Vizualizatsiya uchun ma'lumotlar (O'zgarishsiz qoladi) ---
def get_ingredient_consumption_data(db: Session, start_date: date, end_date: date, product_id: Optional[int] = None) -> \
List[schemas.IngredientConsumptionDataPoint]:
    # ... (avvalgi kod)
    query = db.query(
        models.Product.name.label("product_name"),
        func.sum(models.ServingDetail.quantity_used).label("total_consumed"),
        models.Unit.short_name.label("unit_short_name")
    ).join(models.Product, models.ServingDetail.product_id == models.Product.id) \
        .join(models.Unit, models.Product.unit_id == models.Unit.id) \
        .join(models.MealServing, models.ServingDetail.serving_id == models.MealServing.id) \
        .filter(models.MealServing.served_at >= datetime.combine(start_date, datetime.min.time())) \
        .filter(models.MealServing.served_at <= datetime.combine(end_date, datetime.max.time()))
    if product_id: query = query.filter(models.ServingDetail.product_id == product_id)
    query = query.group_by(models.Product.name, models.Unit.short_name) \
        .order_by(func.sum(models.ServingDetail.quantity_used).desc())
    results = query.all()
    return [schemas.IngredientConsumptionDataPoint(
        product_name=r.product_name,
        total_consumed=r.total_consumed or 0.0,
        unit_short_name=r.unit_short_name
    ) for r in results]


def get_product_delivery_trends(db: Session, start_date: date, end_date: date, product_id: Optional[int] = None) -> \
List[schemas.ProductDeliveryDataPoint]:
    # ... (avvalgi kod)
    query = db.query(
        func.date(models.ProductDelivery.delivery_date).label("delivery_day"),
        models.Product.name.label("product_name"),
        func.sum(models.ProductDelivery.quantity).label("total_delivered"),
        models.Unit.short_name.label("unit_short_name")
    ).join(models.Product, models.ProductDelivery.product_id == models.Product.id) \
        .join(models.Unit, models.Product.unit_id == models.Unit.id) \
        .filter(models.ProductDelivery.delivery_date >= datetime.combine(start_date, datetime.min.time())) \
        .filter(models.ProductDelivery.delivery_date <= datetime.combine(end_date, datetime.max.time()))
    if product_id: query = query.filter(models.ProductDelivery.product_id == product_id)
    query = query.group_by(func.date(models.ProductDelivery.delivery_date), models.Product.name, models.Unit.short_name) \
        .order_by(func.date(models.ProductDelivery.delivery_date), models.Product.name)
    results = query.all()
    return [schemas.ProductDeliveryDataPoint(
        delivery_date=r.delivery_day, product_name=r.product_name,
        total_delivered=r.total_delivered or 0.0, unit_short_name=r.unit_short_name
    ) for r in results]


def generate_monthly_report_db_only(db: Session, year: int, month: int, user_id: Optional[int] = None) -> Optional[
    models.MonthlyReport]:
    report_month_date = date(year, month, 1)

    existing_report = db.query(models.MonthlyReport).filter(
        models.MonthlyReport.report_month == report_month_date).first()
    if existing_report:
        print(f"INFO: CRUD - Deleting existing report data for {year}-{month:02d} before regeneration.")
        db.query(models.ReportMealPerformance).filter(
            models.ReportMealPerformance.report_id == existing_report.id).delete(synchronize_session=False)
        db.query(models.ReportDetail).filter(models.ReportDetail.report_id == existing_report.id).delete(
            synchronize_session=False)
        db.query(models.ProductMonthlyBalance).filter(
            models.ProductMonthlyBalance.report_id == existing_report.id).delete(synchronize_session=False)
        db.delete(existing_report)
        db.commit()

    start_of_month_dt = datetime(year, month, 1)
    if month == 12:
        end_of_month_date_obj = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_of_month_date_obj = date(year, month + 1, 1) - timedelta(days=1)
    end_of_month_dt_with_time = datetime.combine(end_of_month_date_obj, datetime.max.time())

    db_report = models.MonthlyReport(
        report_month=report_month_date,
        generated_at=datetime.now(),
        generated_by=user_id,
        total_portions_served_overall=0,
        is_overall_suspicious=False,
        # difference_percentage=0.0,
    )
    db.add(db_report)
    db.flush()

    # --- 1. ReportMealPerformance ---
    served_portions_by_meal_id_q = db.query(
        models.MealServing.meal_id,
        func.sum(models.MealServing.portions_served).label("monthly_served_for_meal")
    ).filter(
        models.MealServing.served_at >= start_of_month_dt,
        models.MealServing.served_at <= end_of_month_dt_with_time
    ).group_by(models.MealServing.meal_id).all()
    served_portions_map = {item.meal_id: item.monthly_served_for_meal for item in served_portions_by_meal_id_q}

    current_possible_meals_q = db.query(models.PossibleMeals).all()
    possible_portions_map = {pm.meal_id: pm.possible_portions for pm in current_possible_meals_q}

    all_meals_in_db = db.query(models.Meal).filter(models.Meal.deleted_at == None).all()

    calculated_total_served_overall_var = 0  # O'zgaruvchi nomini aniqlashtirdim
    at_least_one_meal_suspicious_calc = False

    # for meal_obj_loop in all_meals_in_db:
    #     meal_id_val = meal_obj_loop.id
    #     portions_served = int(served_portions_map.get(meal_id_val, 0))
    #     possible_portions = int(possible_portions_map.get(meal_id_val, 0))
    #     calculated_total_served_overall_var += portions_served
    #
    #     diff_perc_meal = 0.0
    #     is_susp_meal = False
    #     if possible_portions > 0:
    #         difference = possible_portions - portions_served
    #         diff_perc_meal = (abs(difference) / possible_portions) * 100 if possible_portions > 0 else 0
    #         if portions_served > possible_portions:
    #             is_susp_meal = True
    #         elif diff_perc_meal > settings.SUSPICIOUS_DIFFERENCE_PERCENTAGE:
    #             is_susp_meal = True
    #     elif portions_served > 0:
    #         is_susp_meal = True
    #
    #     if is_susp_meal:
    #         at_least_one_meal_suspicious_calc = True
    #
    #     meal_perf_entry = models.ReportMealPerformance(
    #         report_id=db_report.id,
    #         meal_id=meal_id_val,
    #         portions_served_this_meal=portions_served,
    #         possible_portions_at_report_time=possible_portions,
    #         difference_percentage=round(diff_perc_meal, 2) if possible_portions > 0 else (100.0 if portions_served > 0 else 0.0),
    #         is_suspicious=is_susp_meal
    #     )
    #     db.add(meal_perf_entry)

    # Joriy oyni aniqlaymiz (misol uchun)
    current_month = datetime.now().replace(day=1)  # Har oyning boshidan boshlanadi
    last_month = current_month - timedelta(days=30)  # O'tgan oyning hisoblangan boshlanishi

    # `MonthlyReport` jadvalidan ma'lumotlarni olamiz
    current_report = db.query(models.MonthlyReport).filter(
        models.MonthlyReport.report_month == current_month
    ).first()
    last_report = db.query(models.MonthlyReport).filter(
        models.MonthlyReport.report_month == last_month
    ).first()

    if not current_report or not last_report:
        # Agar hisobot mavjud bo'lmasa, kodni to'xtatamiz
        print("Joriy va/yoki o'tgan oy uchun hisobot ma'lumotlari topilmadi!")
    else:
        # Joriy oy ingredient sarflari
        current_ingredients = (
            db.query(models.ReportDetail)
            .filter(models.ReportDetail.report_id == current_report.id)
            .all()
        )

        # O'tgan oy ingredient sarflari
        last_ingredients = (
            db.query(models.ReportDetail)
            .filter(models.ReportDetail.report_id == last_report.id)
            .all()
        )

        # O'tgan oy ingredientlarini dictionary formatida saqlaymiz
        last_ingredients_map = {
            detail.product_id: detail.total_quantity_used for detail in last_ingredients
        }

        # Eng kam shubhali farq (%) chegarasi
        MIN_SUSPICIOUS_PERCENTAGE = 15

        for current_detail in current_ingredients:
            product_id = current_detail.product_id  # Mahsulot ID
            current_quantity = current_detail.total_quantity_used  # Joriy oy miqdori

            # O'tgan oy ingredient ma'lumotlari - agar mavjud bo'lsa
            last_quantity = last_ingredients_map.get(product_id, 0)

            is_suspicious = False  # Har bir ingredient uchun shubhalilik tekshiruvi
            diff_percent = 0.0  # Farq boshlang'ich qiymati

            if last_quantity > 0:
                # Foiz farqni hisoblash
                diff_percent = abs((1 - (current_quantity / last_quantity)) * 100)

                # Agar farq belgilangan foizdan yuqori bo'lsa
                if diff_percent >= MIN_SUSPICIOUS_PERCENTAGE:
                    is_suspicious = True

            elif last_quantity == 0 and current_quantity > 0:
                # Agar o'tgan oyda ishlatilmagan bo'lsa, lekin hozir ishlatilsa
                is_suspicious = True

            if is_suspicious:
                # Agar shubhali bo'lsa, bildirish chiqaramiz
                create_notification(
                    db,
                    schemas.NotificationCreate(
                        message=f"Shubhali ingredient ID {product_id}: Foiz farqi - {round(diff_percent, 2)}%, "
                                f"Joriy oy: {current_quantity}, O'tgan oy: {last_quantity}.",
                        notification_type_id=settings.NOTIFICATION_TYPE_ID
                    )
                )

            # Natijalarni hisobotga yozamiz
            meal_perf_entry = models.ReportMealPerformance(
                report_id=current_report.id,
                meal_id=current_detail.meal_id,
                portions_served_this_meal=current_quantity,
                difference_percentage=diff_percent,
                is_suspicious=is_suspicious
            )
            db.add(meal_perf_entry)


    # --- 2. ReportDetail (Ingredient Sarfi) ---
    ingredient_usage_data = db.query(
        models.MealServing.meal_id,  # Bu MealServing.meal_id
        models.ServingDetail.product_id,
        func.sum(models.ServingDetail.quantity_used).label("total_quantity_used")
    ).join(models.ServingDetail, models.MealServing.id == models.ServingDetail.serving_id) \
        .filter(
        models.MealServing.served_at >= start_of_month_dt,
        models.MealServing.served_at <= end_of_month_dt_with_time
    ).group_by(models.MealServing.meal_id, models.ServingDetail.product_id).all()

    for usage_row in ingredient_usage_data:
        meal_for_detail = db.get(models.Meal, usage_row.meal_id)
        product_for_detail = db.get(models.Product, usage_row.product_id)

        if meal_for_detail and not meal_for_detail.deleted_at and \
                product_for_detail and not product_for_detail.deleted_at:
            ingredient_detail_entry = models.ReportDetail(
                report_id=db_report.id,
                meal_id=usage_row.meal_id,
                product_id=usage_row.product_id,
                total_quantity_used=float(usage_row.total_quantity_used or 0.0)
            )
            db.add(ingredient_detail_entry)

    # --- 3. ProductMonthlyBalance ---
    all_products_for_balance = db.query(models.Product).filter(models.Product.deleted_at == None).all()
    any_product_balance_suspicious = False

    for product_loop_bal in all_products_for_balance:
        initial_stock_val = _get_product_stock_at_date(db, product_loop_bal.id, start_of_month_dt.date())
        total_received_val = db.query(func.sum(models.ProductDelivery.quantity)).filter(
            models.ProductDelivery.product_id == product_loop_bal.id,
            func.date(models.ProductDelivery.delivery_date) >= start_of_month_dt.date(),  # Sanani sanaga solishtirish
            func.date(models.ProductDelivery.delivery_date) <= end_of_month_date_obj
        ).scalar() or 0.0
        total_available_val = initial_stock_val + total_received_val
        actual_consumption_val = db.query(func.sum(models.ServingDetail.quantity_used)).join(
            models.MealServing, models.ServingDetail.serving_id == models.MealServing.id
        ).filter(
            models.ServingDetail.product_id == product_loop_bal.id,
            models.MealServing.served_at >= start_of_month_dt,
            models.MealServing.served_at <= end_of_month_dt_with_time
        ).scalar() or 0.0
        calculated_consumption_val = 0.0
        # ... (calculated_consumption_val hisoblash logikasi o'zgarishsiz) ...
        servings_in_month_for_calc_q = db.query(models.MealServing).filter(
            models.MealServing.served_at >= start_of_month_dt,
            models.MealServing.served_at <= end_of_month_dt_with_time
        ).options(
            selectinload(models.MealServing.meal).selectinload(models.Meal.ingredients).selectinload(
                models.MealIngredient.unit),
            selectinload(models.MealServing.meal).selectinload(models.Meal.ingredients).selectinload(
                models.MealIngredient.product).selectinload(models.Product.unit)
        ).all()

        for serving_item_calc in servings_in_month_for_calc_q:
            if serving_item_calc.meal and serving_item_calc.meal.ingredients:
                for mi_calc in serving_item_calc.meal.ingredients:
                    if mi_calc.product_id == product_loop_bal.id:
                        if mi_calc.unit and product_loop_bal.unit:
                            qty_in_base = _convert_units_for_comparison(mi_calc.quantity_per_portion,
                                                                        mi_calc.unit.short_name,
                                                                        product_loop_bal.unit.short_name)
                            if qty_in_base is not None:
                                calculated_consumption_val += qty_in_base * serving_item_calc.portions_served
        # ... (calculated_consumption_val hisoblash logikasi tugadi) ...
        theoretical_ending_stock_val = total_available_val - calculated_consumption_val
        actual_ending_stock_val = get_product_current_quantity(db, product_loop_bal.id)
        discrepancy_val = theoretical_ending_stock_val - actual_ending_stock_val

        discrepancy_perc = 0.0
        denominator_for_perc = total_available_val  # Yoki initial_stock + total_received
        if abs(denominator_for_perc) > 1e-9:
            discrepancy_perc = (discrepancy_val / denominator_for_perc) * 100
        elif abs(discrepancy_val) > 1e-9:
            discrepancy_perc = 100.0 if discrepancy_val > 0 else -100.0

        is_bal_susp_val = abs(discrepancy_perc) > settings.SUSPICIOUS_DIFFERENCE_PERCENTAGE
        if actual_ending_stock_val < 0 and theoretical_ending_stock_val >= 0:  # Agar haqiqiy qoldiq minus bo'lsa
            is_bal_susp_val = True

        balance_entry = models.ProductMonthlyBalance(
            report_id=db_report.id, product_id=product_loop_bal.id,
            initial_stock=initial_stock_val,
            total_received=total_received_val,
            total_available=total_available_val,
            calculated_consumption=calculated_consumption_val,
            actual_consumption=actual_consumption_val,
            theoretical_ending_stock=theoretical_ending_stock_val,
            actual_ending_stock=actual_ending_stock_val,
            discrepancy=discrepancy_val,
            is_balance_suspicious=is_bal_susp_val
        )
        db.add(balance_entry)
        if is_bal_susp_val:
            any_product_balance_suspicious = True

    db_report.total_portions_served_overall = calculated_total_served_overall_var
    db_report.is_overall_suspicious = at_least_one_meal_suspicious_calc or any_product_balance_suspicious

    db.commit()
    return get_monthly_report_with_all_details(db, db_report.id)


def get_monthly_report_with_all_details(db: Session, report_id: int) -> Optional[models.MonthlyReport]:
    return db.query(models.MonthlyReport).options(
        selectinload(models.MonthlyReport.generated_by_user).selectinload(models.User.role), # User va uning rolini yuklash
        selectinload(models.MonthlyReport.meal_performance_summaries)
            .selectinload(models.ReportMealPerformance.meal_in_performance_summary),
        selectinload(models.MonthlyReport.all_ingredient_usage_details)
            .selectinload(models.ReportDetail.meal_for_ingredient_detail),
        selectinload(models.MonthlyReport.all_ingredient_usage_details)
            .selectinload(models.ReportDetail.product_for_ingredient_detail)
            .selectinload(models.Product.unit),
        selectinload(models.MonthlyReport.product_balance_summaries)
            .selectinload(models.ProductMonthlyBalance.product_in_balance)
            .selectinload(models.Product.unit)
    ).filter(models.MonthlyReport.id == report_id).first()

def get_monthly_reports_list(db: Session, skip: int = 0, limit: int = 100, year: Optional[int] = None, month: Optional[int] = None) -> \
list[Type[models.MonthlyReport]]:
    """
    Oylik hisobotlar ro'yxatini oladi (faqat asosiy MonthlyReport ma'lumotlari bilan, tafsilotlarsiz).
    Tafsilotlar uchun get_monthly_report_with_all_details ni alohida chaqirish kerak.
    """
    query = db.query(models.MonthlyReport)
    if year: query = query.filter(extract('year', models.MonthlyReport.report_month) == year)
    if month: query = query.filter(extract('month', models.MonthlyReport.report_month) == month)
    return query.order_by(models.MonthlyReport.report_month.desc()).options(
        selectinload(models.MonthlyReport.generated_by_user) # Foydalanuvchini yuklash
    ).offset(skip).limit(limit).all()


# --- Oylik Hisobot Generatsiyasi (YANGILANGAN VA KENGAYTIRILGAN) ---
def _get_product_stock_at_date(db: Session, product_id: int, target_date: date) -> float:
    target_datetime_start_of_day = datetime.combine(target_date, datetime.min.time())

    total_delivered_before_target = db.query(func.sum(models.ProductDelivery.quantity)).filter(
        models.ProductDelivery.product_id == product_id,
        models.ProductDelivery.delivery_date < target_datetime_start_of_day
    ).scalar() or 0.0

    total_used_before_target = db.query(func.sum(models.ServingDetail.quantity_used)).join(
        models.MealServing, models.ServingDetail.serving_id == models.MealServing.id
    ).filter(
        models.ServingDetail.product_id == product_id,
        models.MealServing.served_at < target_datetime_start_of_day
    ).scalar() or 0.0
    return total_delivered_before_target - total_used_before_target





# app/crud.py
# ... (boshqa importlar)

def create_audit_log_entry(
    db: Session,
    user_id: Optional[int],
    username: Optional[str],
    action: str,
    status: str = "SUCCESS",
    target_entity_type: Optional[str] = None,
    target_entity_id: Optional[int] = None,
    details: Optional[str] = None,
    changes_before: Optional[Dict[str, Any]] = None,
    changes_after: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> models.AuditLog:
    db_log_entry = models.AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        status=status,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        details=details,
        changes_before=changes_before,
        changes_after=changes_after,
        ip_address=ip_address,
        user_agent=user_agent,
        timestamp=datetime.now() # Har doim joriy vaqt
    )
    db.add(db_log_entry)
    # db.commit() # Har bir log yozuvini alohida commit qilish
    # db.refresh(db_log_entry)
    return db_log_entry
