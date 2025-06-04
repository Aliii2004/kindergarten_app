# app/routers/products.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Security, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app import crud, schemas, models, security
from app.database import get_db
from app.config import settings
from app.celery_config import redis_client_for_celery_config as redis_client, \
    WS_MESSAGE_CHANNEL
from app.schemas import WebSocketMessage, ProductDefinitionUpdatedPayload, ProductDeletedPayload, StockItemReceivedPayload # Payload sxemalarini import qiling
from app.tasks.portion_tasks import task_update_all_possible_meal_portions_celery, \
    task_check_product_stock_and_notify_celery
from app.logging_utils import log_action
from datetime import datetime


router = APIRouter(
    prefix=settings.API_V1_STR + "/products",
    tags=["Products & Stock Management"],
)


# --- Birliklar (Units) uchun CRUD (Hozircha logsiz) ---
@router.post(
    "/units/",
    response_model=schemas.Unit,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi o'lchov birligi yaratish",
    dependencies=[Security(security.get_current_manager_user)]
)
def create_new_unit(
        unit_in: schemas.UnitCreate,
        # request: Request, # Agar loglash kerak bo'lsa
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_manager_user) # Agar loglash kerak bo'lsa
):
    db_unit_by_name = crud.get_unit_by_name(db, name=unit_in.name)
    if db_unit_by_name:
        # Log yozish (agar kerak bo'lsa)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"'{unit_in.name}' nomli birlik allaqachon mavjud.")
    db_unit_by_short_name = db.query(models.Unit).filter(models.Unit.short_name == unit_in.short_name).first()
    if db_unit_by_short_name:
        # Log yozish (agar kerak bo'lsa)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"'{unit_in.short_name}' qisqa nomli birlik allaqachon mavjud.")
    created_unit = crud.create_unit(db=db, unit=unit_in)
    # Log yozish (agar kerak bo'lsa)
    # log_action(db, request, current_user_from_dep, "CREATE_UNIT", target_entity_id=created_unit.id, ...)
    return created_unit


@router.get(
    "/units/",
    response_model=List[schemas.Unit],
    summary="Barcha o'lchov birliklari ro'yxati",
    dependencies=[Security(security.get_current_active_user)]
)
def read_all_units(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    units = crud.get_units(db, skip=skip, limit=limit)
    return units


@router.post(
    "/",
    response_model=schemas.Product,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi mahsulot yaratish",
    dependencies=[Security(security.get_current_manager_user)]
)
def create_new_product(
        request: Request, # <<--- BIRINCHI O'RINGA
        product_in: schemas.ProductCreate,
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_manager_user)
):
    db_product_by_name = crud.get_product_by_name(db, name=product_in.name)
    if db_product_by_name:
        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="CREATE_PRODUCT_ATTEMPT", status="FAILURE",
            details=f"Product creation failed. Product name '{product_in.name}' already exists.",
            changes_after=product_in.model_dump(mode='json')
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"'{product_in.name}' nomli mahsulot allaqachon mavjud.")

    db_unit = crud.get_unit(db, unit_id=product_in.unit_id)
    if not db_unit:
        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="CREATE_PRODUCT_ATTEMPT", status="FAILURE",
            details=f"Product creation failed. Unit ID {product_in.unit_id} not found.",
            changes_after=product_in.model_dump(mode='json')
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"ID={product_in.unit_id} bo'lgan o'lchov birligi topilmadi.")

    try:
        # 1. Mahsulotni yaratish (commit qilmasdan)
        created_product_orm = crud.create_product(db=db, product=product_in, user_id=current_user_from_dep.id)
        # crud.create_product endi commit qilmaydi, faqat flush va refresh qiladi

        # 2. Log yozish (bu ham commit qilmasligi kerak)
        # crud.create_audit_log_entry commit qilmaydigan qilib o'zgartirilgan deb hisoblaymiz
        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="CREATE_PRODUCT", status="SUCCESS",
            target_entity_type="Product", target_entity_id=created_product_orm.id, # .id flush dan keyin mavjud bo'ladi
            details=f"Product '{created_product_orm.name}' created successfully.",
            changes_after=schemas.Product.model_validate(created_product_orm).model_dump(mode='json')
        )

        db.commit()

        task_update_all_possible_meal_portions_celery.delay()
        db.refresh(created_product_orm)
        return created_product_orm

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()

        error_log_details = f"Unexpected error during product creation: {str(e)}"
        try:
            log_action(
                db=db, request=request, current_user=current_user_from_dep,
                action_name="CREATE_PRODUCT_ATTEMPT", status="ERROR",
                details=error_log_details,
                changes_after=product_in.model_dump(mode='json')
            )
            db.commit() # Xatolik logini saqlashga urinish
        except Exception as log_e:
            print(f"Failed to write ERROR audit log: {log_e}") # Asosiy xatolik muhimroq

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Mahsulot yaratishda kutilmagan xatolik: {str(e)}")


@router.get(
    "/",
    response_model=List[schemas.ProductWithQuantity],
    summary="Barcha mahsulotlar ro'yxati (ombordagi miqdori bilan)",
    dependencies=[Security(security.get_current_active_user)]
)
def read_all_products_with_stock(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1001),
        name_filter: Optional[str] = Query(None),
        low_stock_only: bool = Query(False),
        db: Session = Depends(get_db)
):
    products_with_qty = crud.get_all_products_with_current_quantity(
        db, skip=skip, limit=limit, name_filter=name_filter, low_stock_only=low_stock_only
    )
    return products_with_qty


@router.get(
    "/{product_id}",
    response_model=schemas.ProductWithQuantity,
    summary="ID bo'yicha mahsulotni olish (ombordagi miqdori bilan)",
    dependencies=[Security(security.get_current_active_user)]
)
def read_product_by_id_with_stock(
        product_id: int,
        db: Session = Depends(get_db)
):
    db_product = crud.get_product(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mahsulot topilmadi")
    current_quantity = crud.get_product_current_quantity(db, product_id)
    product_data_validated = schemas.Product.model_validate(db_product)
    return schemas.ProductWithQuantity(
        **product_data_validated.model_dump(),
        current_quantity=current_quantity
    )


@router.put(
    "/{product_id}",
    response_model=schemas.Product,
    summary="Mavjud mahsulotni yangilash",
    dependencies=[Security(security.get_current_manager_user)]
)
async def update_existing_product(
        request: Request,
        product_id: int,
        product_in: schemas.ProductUpdate,
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_manager_user)
):
    db_product_to_update = crud.get_product(db, product_id=product_id)
    if db_product_to_update is None:

        details_log = f"Product ID {product_id} not found for update by user '{current_user_from_dep.username}'."
        log_action(db=db, request=request, current_user=current_user_from_dep, action_name="UPDATE_PRODUCT_ATTEMPT",
                   status="NOT_FOUND", target_entity_type="Product", target_entity_id=product_id, details=details_log)

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yangilash uchun mahsulot topilmadi")

    old_product_data_for_log = schemas.Product.model_validate(db_product_to_update).model_dump(mode='json')

    if product_in.name and product_in.name != db_product_to_update.name:
        existing_product_with_new_name = crud.get_product_by_name(db, name=product_in.name)
        if existing_product_with_new_name and existing_product_with_new_name.id != product_id:
            details_log = f"Update product by user '{current_user_from_dep.username}' failed. New name '{product_in.name}' already exists."
            log_action(db=db, request=request, current_user=current_user_from_dep, action_name="UPDATE_PRODUCT_ATTEMPT",
                       status="FAILURE", target_entity_type="Product", target_entity_id=product_id, details=details_log,
                       changes_before=old_product_data_for_log,
                       changes_after=product_in.model_dump(exclude_unset=True, mode='json'))
            # Bu log ham commit qilinmaydi
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"'{product_in.name}' nomli mahsulot allaqachon mavjud.")

    if product_in.unit_id and product_in.unit_id != db_product_to_update.unit_id:
        db_unit = crud.get_unit(db, unit_id=product_in.unit_id)
        if not db_unit:
            details_log = f"Update product by user '{current_user_from_dep.username}' failed. Unit ID {product_in.unit_id} not found."
            log_action(db=db, request=request, current_user=current_user_from_dep, action_name="UPDATE_PRODUCT_ATTEMPT",
                       status="FAILURE", target_entity_type="Product", target_entity_id=product_id, details=details_log,
                       changes_before=old_product_data_for_log,
                       changes_after=product_in.model_dump(exclude_unset=True, mode='json'))
            # Bu log ham commit qilinmaydi
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"ID={product_in.unit_id} bo'lgan o'lchov birligi topilmadi.")

    try:
        # 1. Mahsulotni yangilash (obyekt maydonlarini o'zgartirish)
        # crud.update_product endi faqat ORM obyektini qaytaradi, commit qilmaydi
        # O'zgarishlar db_product_to_update obyektida bo'ladi
        update_data = product_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_product_to_update, key, value)
        db_product_to_update.updated_at = datetime.now()  # updated_at ni qo'lda yangilash

        db.add(db_product_to_update)

        current_state_for_log = schemas.Product.model_validate(db_product_to_update).model_dump(mode='json')

        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="UPDATE_PRODUCT", status="SUCCESS",
            target_entity_type="Product", target_entity_id=db_product_to_update.id,
            details=f"Product '{db_product_to_update.name}' (ID: {product_id}) updated by user '{current_user_from_dep.username}'.",
            changes_before=old_product_data_for_log,
            changes_after=current_state_for_log  # Yangilangan holat
        )

        # ***** MUHIM: Yagona COMMIT *****
        db.commit()

        # Commitdan keyin obyektni qayta refresh qilish (javob uchun va keyingi amallar uchun)
        db.refresh(db_product_to_update)
        if db_product_to_update.unit:  # Agar unit bog'liqligi bo'lsa, uni ham refresh qilish
            db.refresh(db_product_to_update.unit)
        if db_product_to_update.created_by_user:  # Agar user bog'liqligi bo'lsa
            db.refresh(db_product_to_update.created_by_user)

        # Keyingi amallar
        task_check_product_stock_and_notify_celery.delay(db_product_to_update.id)
        current_qty = crud.get_product_current_quantity(db, db_product_to_update.id)

        ws_payload_update = ProductDefinitionUpdatedPayload(
            product_id=db_product_to_update.id, product_name=db_product_to_update.name,
            min_quantity=db_product_to_update.min_quantity, current_quantity=current_qty,
            unit=db_product_to_update.unit.short_name if db_product_to_update.unit else "N/A",
            message=f"'{db_product_to_update.name}' mahsuloti ta'rifi yangilandi."
        )
        ws_message_obj_update = WebSocketMessage(type="product_definition_updated", payload=ws_payload_update)
        redis_client.publish(WS_MESSAGE_CHANNEL, ws_message_obj_update.model_dump_json())
        task_update_all_possible_meal_portions_celery.delay()

        return db_product_to_update  # Yangilangan ORM obyektini qaytarish

    except HTTPException:
        db.rollback()  # Agar yuqoridagi if bloklarida xatolik bo'lsa va bu yerga yetib kelsa
        raise
    except Exception as e:
        db.rollback()
        error_log_details = f"Unexpected error updating product ID {product_id} by user '{current_user_from_dep.username}': {str(e)}"
        # Kutilmagan xatolik uchun log yozish (bu log commit qilinmaydi, chunki rollback bo'ldi)
        # Agar bu logni saqlash shart bo'lsa, alohida commit logikasi kerak
        print(
            f"ERROR_AUDIT_LOG_ATTEMPT (will not be committed due to rollback): Action: UPDATE_PRODUCT_ATTEMPT, Status: ERROR, Details: {error_log_details}")
        # log_action(...)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Mahsulotni yangilashda kutilmagan server xatoligi: {error_log_details}")




@router.delete(
    "/{product_id}",
    response_model=schemas.Product,  # Yoki schemas.Msg agar faqat xabar qaytarilsa
    summary="Mahsulotni \"soft delete\" qilish",
    dependencies=[Security(security.get_current_admin_user)]
)
async def soft_delete_existing_product(
        request: Request,
        product_id: int,
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_admin_user)
):
    db_product_to_delete = crud.get_product(db, product_id=product_id)
    if db_product_to_delete is None:
        details_log = f"Product ID {product_id} not found for deletion by user '{current_user_from_dep.username}'."
        try:
            log_action(db=db, request=request, current_user=current_user_from_dep, action_name="DELETE_PRODUCT_ATTEMPT",
                       status="NOT_FOUND", target_entity_type="Product", target_entity_id=product_id,
                       details=details_log)
            db.commit()
        except Exception as log_e:
            print(f"CRITICAL: Failed to write NOT_FOUND audit log for product deletion: {log_e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="O'chirish uchun mahsulot topilmadi")

    old_product_data_for_log = schemas.Product.model_validate(db_product_to_delete).model_dump(mode='json')

    meals_using_product = db.query(models.MealIngredient).join(models.Meal).filter(
        models.MealIngredient.product_id == product_id,
        models.Meal.is_active == True,
        models.Meal.deleted_at == None
    ).all()
    if meals_using_product:
        meal_names = [mui.meal.name for mui in meals_using_product if mui.meal]
        details_msg = f"Cannot delete product '{db_product_to_delete.name}' by user '{current_user_from_dep.username}'. It is used in active meals: {', '.join(meal_names)}."
        try:
            log_action(db=db, request=request, current_user=current_user_from_dep, action_name="DELETE_PRODUCT_ATTEMPT",
                       status="FAILURE", target_entity_type="Product", target_entity_id=product_id, details=details_msg,
                       changes_before=old_product_data_for_log)
            db.commit()
        except Exception as log_e:
            print(f"CRITICAL: Failed to write FAILURE audit log for product deletion: {log_e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=details_msg)

    try:
        # 1. Mahsulotni "soft delete" qilish (crud.soft_delete_product commit qilmaydi)
        # Bu funksiya o'zgartirilgan ORM obyektini qaytarishi kerak
        # crud.soft_delete_product ichida db_product.deleted_at = datetime.now() qilinadi

        # O'zgarishni to'g'ridan-to'g'ri shu yerda bajaramiz, crud funksiyasi faqat topib berishi mumkin
        db_product_to_delete.deleted_at = datetime.now()
        # Agar Product modelida is_active bo'lsa, uni ham o'zgartirish kerak:
        # if hasattr(db_product_to_delete, 'is_active'):
        #     db_product_to_delete.is_active = False
        db.add(db_product_to_delete)  # O'zgartirilgan obyektni sessiyaga qo'shish

        # 2. Log yozish
        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="DELETE_PRODUCT", status="SUCCESS",
            target_entity_type="Product", target_entity_id=db_product_to_delete.id,
            details=f"Product '{db_product_to_delete.name}' (ID: {product_id}) soft deleted by user '{current_user_from_dep.username}'.",
            changes_before=old_product_data_for_log,
            # ***** TUZATISH SHU YERDA *****
            changes_after={
                "deleted_at": db_product_to_delete.deleted_at.isoformat() if db_product_to_delete.deleted_at else None}
            # Agar Product modelida is_active bo'lsa, uni ham qo'shing:
            # "is_active": False
        )

        # ***** Yagona COMMIT *****
        db.commit()
        db.refresh(db_product_to_delete)  # Commitdan keyin to'liq obyektni olish uchun

        task_update_all_possible_meal_portions_celery.delay()
        ws_payload_deleted = ProductDeletedPayload(
            product_id=db_product_to_delete.id,
            product_name=db_product_to_delete.name,
            message=f"'{db_product_to_delete.name}' mahsuloti o'chirildi."
        )
        ws_message_obj_deleted = WebSocketMessage(type="product_deleted", payload=ws_payload_deleted)
        redis_client.publish(WS_MESSAGE_CHANNEL, ws_message_obj_deleted.model_dump_json())

        return db_product_to_delete

    except HTTPException:
        # Bu blok endi asosan yuqoridagi if shartlaridan kelgan va logi allaqachon yozilgan
        # HTTPException lar uchun.
        # Agar xatolik loglari commit qilingan bo'lsa, bu yerda rollback qilish ularni bekor qilmaydi.
        # Agar xatolik loglari commit qilinmagan bo'lsa, rollback qilish kerak.
        # Hozirgi holatda, har bir xatolik logi alohida commit qilinmoqda.
        raise
    except Exception as e:
        db.rollback()  # Asosiy try bloki ichidagi kutilmagan xatolik uchun
        error_log_details = f"Unexpected error deleting product ID {product_id} by user '{current_user_from_dep.username}': {str(e)}"
        try:
            log_action(
                db=db, request=request, current_user=current_user_from_dep,
                action_name="DELETE_PRODUCT_ATTEMPT", status="ERROR",
                target_entity_type="Product", target_entity_id=product_id,
                details=error_log_details,
                changes_before=old_product_data_for_log
            )
            db.commit()
        except Exception as log_e:
            print(f"CRITICAL: Failed to write ERROR audit log after product deletion failure: {log_e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Mahsulotni o'chirishda kutilmagan server xatoligi: {error_log_details}")


@router.post(
    "/deliveries/",
    response_model=schemas.ProductDelivery,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi mahsulot yetkazib berilishini qayd etish",
    dependencies=[Security(security.get_current_manager_user)]
)
async def create_new_product_delivery(
        request: Request,
        delivery_in: schemas.ProductDeliveryCreate,  # Bu yerda delivery_date: datetime keladi
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_manager_user)
):
    db_product = crud.get_product(db, product_id=delivery_in.product_id)
    if not db_product:
        details_log = f"Product delivery creation by user '{current_user_from_dep.username}' failed. Product ID {delivery_in.product_id} not found."
        try:
            log_action(db=db, request=request, current_user=current_user_from_dep,
                       action_name="CREATE_PRODUCT_DELIVERY_ATTEMPT", status="NOT_FOUND", target_entity_type="Product",
                       target_entity_id=delivery_in.product_id, details=details_log,
                       changes_after=delivery_in.model_dump(mode='json'))
            db.commit()
        except Exception as log_e:
            print(f"CRITICAL: Failed to write NOT_FOUND audit log for product delivery: {log_e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"ID={delivery_in.product_id} bo'lgan mahsulot topilmadi.")

    try:
        # 1. Yetkazib berish obyektini yaratish (crud.create_product_delivery flush va refresh qiladi)
        created_delivery_orm = crud.create_product_delivery(db=db, delivery=delivery_in,
                                                            user_id=current_user_from_dep.id)
        # Endi created_delivery_orm.id va boshqa avtomatik generatsiya qilingan maydonlar mavjud

        # 2. Log yozish
        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="CREATE_PRODUCT_DELIVERY", status="SUCCESS",
            target_entity_type="ProductDelivery", target_entity_id=created_delivery_orm.id,
            details=f"Delivery for product '{db_product.name}' (Qty: {delivery_in.quantity} {db_product.unit.short_name if db_product.unit else ''}) recorded by user '{current_user_from_dep.username}'.",
            changes_after=schemas.ProductDelivery.model_validate(created_delivery_orm).model_dump(mode='json')
        )

        # ***** MUHIM: Yagona COMMIT *****
        db.commit()

        # ***** JAVOB UCHUN OBYEKTNI QAYTA REFRESH QILISH (BOG'LIQLIKLAR UCHUN) *****
        # Asosiy obyekt allaqachon CRUDda refresh qilingan. Bu yerda bog'liq obyektlarni yuklash kerak bo'lishi mumkin.
        db.refresh(created_delivery_orm)  # Sessiyadagi obyektni bazadagi eng so'nggi holatga keltirish
        if created_delivery_orm.product:
            db.refresh(created_delivery_orm.product)
            if created_delivery_orm.product.unit:
                db.refresh(created_delivery_orm.product.unit)
        if created_delivery_orm.received_by_user:
            db.refresh(created_delivery_orm.received_by_user)

        # Keyingi amallar
        task_update_all_possible_meal_portions_celery.delay()
        task_check_product_stock_and_notify_celery.delay(created_delivery_orm.product_id)

        current_qty_after_delivery = crud.get_product_current_quantity(db, created_delivery_orm.product_id)
        ws_payload_delivery = StockItemReceivedPayload(
            product_id=created_delivery_orm.product_id,
            product_name=created_delivery_orm.product.name if created_delivery_orm.product else "N/A",
            change_in_quantity=created_delivery_orm.quantity,
            new_total_quantity=current_qty_after_delivery,
            unit=created_delivery_orm.product.unit.short_name if created_delivery_orm.product and created_delivery_orm.product.unit else "N/A",
            delivery_id=created_delivery_orm.id,
            message=f"'{created_delivery_orm.product.name if created_delivery_orm.product else 'N/A'}' mahsulotidan {created_delivery_orm.quantity} {created_delivery_orm.product.unit.short_name if created_delivery_orm.product and created_delivery_orm.product.unit else ''} qabul qilindi. Yangi miqdor: {current_qty_after_delivery:.2f}"
        )
        ws_message_obj_delivery = WebSocketMessage(type="stock_item_received", payload=ws_payload_delivery)
        redis_client.publish(WS_MESSAGE_CHANNEL, ws_message_obj_delivery.model_dump_json())

        return created_delivery_orm

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        error_log_details = f"Unexpected error during product delivery creation by user '{current_user_from_dep.username}': {str(e)}"
        try:
            log_action(db=db, request=request, current_user=current_user_from_dep,
                       action_name="CREATE_PRODUCT_DELIVERY_ATTEMPT", status="ERROR", details=error_log_details,
                       changes_after=delivery_in.model_dump(mode='json'))
            db.commit()
        except Exception as log_e:
            print(f"CRITICAL: Failed to write ERROR audit log after product delivery creation failure: {log_e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Mahsulot yetkazib berishni qayd etishda kutilmagan xatolik: {error_log_details}")


@router.get(
    "/deliveries/",
    response_model=List[schemas.ProductDelivery],
    summary="Barcha mahsulot yetkazib berishlar ro'yxati",
    dependencies=[Security(security.get_current_manager_user)]
)
def read_all_product_deliveries(
        product_id: Optional[int] = Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1001),
        db: Session = Depends(get_db)
):
    deliveries_orm = crud.get_product_deliveries(db, product_id=product_id, skip=skip, limit=limit)
    deliveries_schema = []
    for del_orm in deliveries_orm:
        p_name = del_orm.product.name if del_orm.product else None
        # schemas.ProductDelivery endi product_name va product_unit_short_name ni validation_alias orqali kutadi
        deliveries_schema.append(schemas.ProductDelivery.model_validate(del_orm))
    return deliveries_schema
