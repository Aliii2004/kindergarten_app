# app/tasks/portion_tasks.py
from app.celery_config import celery_app, redis_client_for_celery_config as redis_client, WS_MESSAGE_CHANNEL
from app.database import SessionLocal
from app import crud, schemas
from app.schemas import WebSocketMessage
from datetime import datetime
import json  # Redisga yuborish uchun


@celery_app.task(
    name="kindergarten.portions.update_all_possible",  # Unikalroq nom
    autoretry_for=(Exception,),  # Umumiy xatoliklarda qayta urinish (ehtiyot bo'lish kerak)
    max_retries=3,
    default_retry_delay=60  # 1 daqiqadan keyin
)
def task_update_all_possible_meal_portions_celery():
    """
    Celery task: Barcha faol ovqatlar uchun tayyorlanishi mumkin bo'lgan porsiyalarni
    hisoblaydi va `PossibleMeals` jadvalini yangilaydi.
    Natija haqida Redis orqali WebSocket uchun xabar yuboradi.
    """
    db = None
    try:
        db = SessionLocal()
        print(f"CELERY_TASK: [{task_update_all_possible_meal_portions_celery.name}] - Running...")
        crud.update_all_possible_meal_portions(db)  # Bu funksiya o'zi commit qiladi
        print(
            f"CELERY_TASK: [{task_update_all_possible_meal_portions_celery.name}] - Possible meal portions recalculated.")

        # Yangilangan porsiyalar haqida umumiy WS xabari (Redis orqali)
        ws_payload = {"message": "Barcha ovqatlar uchun mumkin bo'lgan porsiyalar qayta hisoblandi.",
                      "recalculated_at": datetime.now().isoformat()}
        ws_message_obj = WebSocketMessage(type="possible_portions_recalculated", payload=ws_payload)
        redis_client.publish(WS_MESSAGE_CHANNEL, ws_message_obj.model_dump_json())  # Pydantic V2 da .model_dump_json()

        return {"status": "success", "message": "Possible meal portions recalculated and notification sent."}
    except Exception as e:
        print(f"CELERY_TASK_ERROR: [{task_update_all_possible_meal_portions_celery.name}] - {str(e)}")
        # Qayta urinish autoretry_for orqali avtomatik bo'ladi
        raise  # Xatolikni qayta ko'tarish, Celery retry logikasi ishlashi uchun
    finally:
        if db:
            db.close()


@celery_app.task(
    name="kindergarten.stock.check_and_notify",  # Unikalroq nom
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=300  # 5 daqiqadan keyin
)
def task_check_product_stock_and_notify_celery(product_id: int):
    """
    Celery task: Berilgan mahsulot IDsi uchun ombordagi qoldiqni tekshiradi.
    Agar miqdor minimaldan kam bo'lsa, DBga bildirishnoma yozadi va
    Redis orqali WebSocket uchun "low_stock_alert" xabarini yuboradi.
    """
    db = None
    try:
        db = SessionLocal()
        print(
            f"CELERY_TASK: [{task_check_product_stock_and_notify_celery.name}] - Checking stock for product_id: {product_id}")
        product = crud.get_product(db, product_id)  # deleted_at == None tekshiriladi
        if not product:
            print(
                f"CELERY_TASK_WARN: [{task_check_product_stock_and_notify_celery.name}] - Product {product_id} not found.")
            return {"status": "error", "message": "Product not found", "product_id": product_id}

        current_quantity = crud.get_product_current_quantity(db, product_id)

        if current_quantity < product.min_quantity:
            print(
                f"CELERY_TASK: [{task_check_product_stock_and_notify_celery.name}] - Low stock detected for product {product.name} (ID: {product_id}).")
            # 1. DBga Notification yozish
            db_notification = crud.create_low_stock_db_notification(db, product, current_quantity)
            # create_low_stock_db_notification o'zi commit qiladi (agar kerak bo'lsa) yoki bu yerda commit
            # crud.create_low_stock_db_notification qaytargan notification obyektini ishlatamiz
            db_notification_id = db_notification.id if db_notification else None

            # 2. Redis Pub/Sub orqali WebSocket uchun xabar yuborish
            message_text_for_ws = f"DIQQAT! '{product.name}' mahsuloti kam qoldi. Joriy miqdor: {current_quantity:.2f} {product.unit.short_name} (Minimal: {product.min_quantity} {product.unit.short_name})."
            ws_payload = schemas.LowStockAlertPayload(  # Maxsus payload sxemasidan foydalanish
                product_id=product.id,
                product_name=product.name,
                current_quantity=current_quantity,
                min_quantity=product.min_quantity,
                unit=product.unit.short_name,
                message=message_text_for_ws,
                notification_id=db_notification_id
            )
            ws_message_obj = WebSocketMessage(type="low_stock_alert", payload=ws_payload)  # To'g'ri payload bilan
            redis_client.publish(WS_MESSAGE_CHANNEL, ws_message_obj.model_dump_json())
            print(
                f"CELERY_TASK: [{task_check_product_stock_and_notify_celery.name}] - Low stock alert for product {product.name} sent to Redis.")
            return {"status": "success", "alert_sent": True, "product_id": product_id}
        else:
            print(
                f"CELERY_TASK: [{task_check_product_stock_and_notify_celery.name}] - Stock for product {product.name} (ID: {product_id}) is sufficient.")
            return {"status": "success", "alert_sent": False, "product_id": product_id}
    except Exception as e:
        if db: db.rollback()  # Agar create_low_stock_db_notification o'zi commit qilmasa
        print(
            f"CELERY_TASK_ERROR: [{task_check_product_stock_and_notify_celery.name}] for product {product_id} - {str(e)}")
        raise
    finally:
        if db:
            db.close()