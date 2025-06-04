# app/tasks/report_tasks.py
from typing import Optional

from app.celery_config import celery_app, redis_client_for_celery_config as redis_client, WS_MESSAGE_CHANNEL
from app.database import SessionLocal
from app import crud, models, schemas  # schemas.py dan WebSocketMessage ni olish uchun
from app.schemas import WebSocketMessage
from datetime import datetime, timedelta
import json


@celery_app.task(
    name="kindergarten.reports.generate_monthly",  # Unikalroq nom
    autoretry_for=(Exception,),
    max_retries=2,  # Hisobot generatsiyasi og'irroq bo'lishi mumkin, kamroq retry
    default_retry_delay=60 * 5  # 5 daqiqadan keyin
)
def task_generate_monthly_report_celery(year: int, month: int, triggered_by_user_id: Optional[int] = None):
    """
    Celery task: Belgilangan yil va oy uchun oylik hisobotni generatsiya qiladi.
    Agar hisobot shubhali bo'lsa, DBga bildirishnoma yozadi va Redis orqali
    WebSocket uchun "suspicious_report_alert" xabarini yuboradi.
    `triggered_by_user_id` agar qo'lda ishga tushirilgan bo'lsa, kim tomonidanligini bildiradi.
    """
    db = None
    try:
        db = SessionLocal()
        print(
            f"CELERY_TASK: [{task_generate_monthly_report_celery.name}] - Starting monthly report generation for {year}-{month:02d}...")

        # Bu funksiya DBga yozadi va MonthlyReport obyektini qaytaradi
        db_report = crud.generate_monthly_report_db_only(db, year, month, triggered_by_user_id)

        if db_report:
            is_suspicious = db_report.is_overall_suspicious
            print(
                f"CELERY_TASK: [{task_generate_monthly_report_celery.name}] - Monthly report for {year}-{month:02d} generated (ID: {db_report.id}). Suspicious: {is_suspicious}")

            if is_suspicious:
                # 1. DBga Notification yozish (Adminlarga)
                # Bu funksiya List[models.Notification] qaytaradi
                created_db_notifications = crud.create_suspicious_report_db_notifications(db, db_report)
                # create_suspicious_report_db_notifications o'zi commit qiladi (agar kerak bo'lsa)
                # yoki bu yerda commit

                # 2. Redis Pub/Sub orqali WebSocket uchun xabar yuborish
                message_text_for_ws = f"DIQQAT! {db_report.report_month.strftime('%B %Y')} oyi uchun hisobotda katta farq ({db_report.difference_percentage:.2f}%) aniqlandi. Iltimos, tekshiring."
                ws_payload = schemas.SuspiciousReportAlertPayload(
                    report_id=db_report.id,
                    report_month=db_report.report_month.strftime('%Y-%m'),  # YYYY-MM formatida
                    difference_percentage=db_report.difference_percentage,
                    message=message_text_for_ws
                    # notification_ids=[n.id for n in created_db_notifications] # Agar kerak bo'lsa
                )
                ws_message_obj = WebSocketMessage(type="suspicious_report_alert", payload=ws_payload)
                redis_client.publish(WS_MESSAGE_CHANNEL, ws_message_obj.model_dump_json())
                print(
                    f"CELERY_TASK: [{task_generate_monthly_report_celery.name}] - Suspicious report alert for {db_report.report_month.strftime('%Y-%m')} sent to Redis.")

            return {"status": "success", "report_id": db_report.id, "is_suspicious": is_suspicious}
        else:
            # crud.generate_monthly_report_db_only None qaytargan bo'lishi mumkin (masalan, ma'lumot yo'q)
            print(
                f"CELERY_TASK_WARN: [{task_generate_monthly_report_celery.name}] - No data to generate report for {year}-{month:02d}.")
            return {"status": "no_data", "message": "Hisobot uchun ma'lumotlar topilmadi."}

    except Exception as e:
        if db: db.rollback()  # Agar generate_monthly_report_db_only o'zi commit qilmasa
        print(f"CELERY_TASK_ERROR: [{task_generate_monthly_report_celery.name}] for {year}-{month:02d} - {str(e)}")
        raise
    finally:
        if db:
            db.close()


@celery_app.task(name="kindergarten.reports.schedule_previous_month_generation")
def task_schedule_previous_month_report_generation():
    """
    Celery Beat task: O'tgan oy uchun oylik hisobot generatsiyasini rejalashtiradi.
    Bu task Celery Beat tomonidan (masalan, har oyning 1-kuni) avtomatik ishga tushiriladi.
    """
    today = datetime.today()
    # O'tgan oyning birinchi kunini topish (bu oyning birinchi kunidan bir kun ayirish orqali o'tgan oyning oxirgi kunini topamiz)
    first_day_of_current_month = today.replace(day=1)
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)

    report_year = last_day_of_previous_month.year
    report_month = last_day_of_previous_month.month

    print(
        f"CELERY_BEAT_TASK: [{task_schedule_previous_month_report_generation.name}] - Scheduling report generation for {report_year}-{report_month:02d}")

    # Asosiy hisobot generatsiya taskini chaqirish
    task_generate_monthly_report_celery.delay(report_year, report_month,
                                              triggered_by_user_id=None)  # Avtomatik generatsiya, user_id=None

    return f"Monthly report generation for {report_year}-{report_month:02d} has been scheduled via Celery."