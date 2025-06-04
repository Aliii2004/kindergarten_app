# app/routers/reports.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Security, Request # Request ni import qiling
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, datetime

from app import crud, schemas, models, security
from app.database import get_db
from app.config import settings
from app.tasks.report_tasks import task_generate_monthly_report_celery
from app.logging_utils import log_action

router = APIRouter(
    prefix=settings.API_V1_STR,
    tags=["Reports & Notifications"],
)


# --- Notifications Endpoints ---
@router.get(
    "/notifications/",
    response_model=List[schemas.Notification],
    summary="Joriy foydalanuvchi uchun bildirishnomalar",
    dependencies=[Security(security.get_current_active_user)]
)
async def get_my_notifications(
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=1000),
        unread_only: bool = Query(False, description="Faqat o'qilmagan bildirishnomalarni ko'rsatish"),
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_active_user)
):
    notifications = crud.get_notifications_for_user(
        db, user_id=current_user_from_dep.id, skip=skip, limit=limit, unread_only=unread_only
    )
    return notifications


@router.post(
    "/notifications/{notification_id}/mark-as-read",
    response_model=schemas.Notification,
    summary="Bildirishnomani o'qilgan deb belgilash",
    dependencies=[Security(security.get_current_active_user)]
)
async def mark_notification_read(
        notification_id: int,
        request: Request, # Loglash uchun Request obyektini olamiz
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_active_user)
):
    updated_notification = crud.mark_notification_as_read(db, notification_id=notification_id,
                                                          user_id=current_user_from_dep.id)
    if not updated_notification:
        existing_notif = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
        status_log = "NOT_FOUND" if not existing_notif else "FAILURE"
        details_log = f"Notification ID {notification_id} not found." if not existing_notif else f"Failed to mark notification ID {notification_id} as read by user '{current_user_from_dep.username}' (possibly not owned or already read)."
        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="MARK_NOTIFICATION_READ_ATTEMPT", status=status_log,
            target_entity_type="Notification", target_entity_id=notification_id,
            details=details_log
        )
        if not existing_notif:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bildirishnoma topilmadi.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Bildirishnomani o'qilgan deb belgilashda xatolik (ehtimol, sizga tegishli emas yoki allaqachon o'qilgan).")

    log_action(
        db=db, request=request, current_user=current_user_from_dep,
        action_name="MARK_NOTIFICATION_READ", status="SUCCESS",
        target_entity_type="Notification", target_entity_id=notification_id,
        details=f"Notification ID {notification_id} marked as read by user '{current_user_from_dep.username}'."
    )
    return updated_notification


@router.post(
    "/notifications/mark-all-as-read",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, Any],
    summary="Joriy foydalanuvchi uchun barcha bildirishnomalarni o'qilgan deb belgilash",
    dependencies=[Security(security.get_current_active_user)]
)
async def mark_all_my_notifications_read(
        request: Request, # Loglash uchun Request obyektini olamiz
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_active_user)
):
    updated_count = crud.mark_all_notifications_as_read_for_user(db, user_id=current_user_from_dep.id)
    log_action(
        db=db, request=request, current_user=current_user_from_dep,
        action_name="MARK_ALL_NOTIFICATIONS_READ", status="SUCCESS",
        details=f"User '{current_user_from_dep.username}' marked {updated_count} notifications as read."
    )
    return {"message": f"{updated_count} ta bildirishnoma o'qilgan deb belgilandi."}


# --- Reports Endpoints ---
@router.post(
    "/reports/monthly/generate",
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Oylik hisobotni qo'lda generatsiya qilishni rejalashtirish (Faqat Admin)",
    dependencies=[Security(security.get_current_admin_user)]
)
async def schedule_manual_monthly_report_generation(request: Request,
        # Non-default parameters first
        year: int = Query(..., description="Hisobot generatsiya qilinadigan yil (masalan, 2023)", ge=2020,
                          le=datetime.now().year + 5),
        month: int = Query(..., description="Hisobot generatsiya qilinadigan oy (1-12)", ge=1, le=12),
         # Loglash uchun Request obyektini olamiz
        # Default parameters (Depends)
        db: Session = Depends(get_db),
        current_admin_from_dep: models.User = Depends(security.get_current_admin_user)
):
    task = task_generate_monthly_report_celery.delay(year, month, triggered_by_user_id=current_admin_from_dep.id)
    log_action(
        db=db, request=request, current_user=current_admin_from_dep,
        action_name="SCHEDULE_MANUAL_MONTHLY_REPORT", status="INITIATED",
        details=f"Manual monthly report generation scheduled by admin '{current_admin_from_dep.username}' for {year}-{month:02d}. Celery Task ID: {task.id}",
    )
    return {
        "msg": f"Oylik hisobot ({year}-{month:02d}) generatsiyasi Celery orqali rejalashtirildi. Task ID: {task.id}"}


@router.get(
    "/reports/monthly/",
    response_model=List[schemas.MonthlyReport],
    summary="Barcha generatsiya qilingan oylik hisobotlar ro'yxati",
    dependencies=[Security(security.get_current_manager_user)]
)
async def get_all_monthly_reports(
        skip: int = Query(0, ge=0),
        limit: int = Query(12, ge=1, le=500),
        year: Optional[int] = Query(None, description="Yil bo'yicha filtrlash"),
        month: Optional[int] = Query(None, description="Oy bo'yicha filtrlash (1-12)"),
        db: Session = Depends(get_db)
):
    reports = crud.get_monthly_reports_list(db, skip=skip, limit=limit, year=year, month=month)
    return reports


@router.get(
    "/reports/monthly/{report_id}",
    response_model=schemas.MonthlyReport,
    summary="ID bo'yicha oylik hisobotni barcha tafsilotlari bilan olish",
    dependencies=[Security(security.get_current_manager_user)]
)
async def get_single_monthly_report_with_details(
    report_id: int, # Non-default
    request: Request, # Non-default (loglash uchun)
    # Default parameters (Depends)
    db: Session = Depends(get_db),
    current_user_from_dep: models.User = Depends(security.get_current_manager_user)
):
    report_with_details = crud.get_monthly_report_with_all_details(db, report_id)
    if not report_with_details:
        log_action(
             db=db, request=request, current_user=current_user_from_dep,
             action_name="VIEW_MONTHLY_REPORT_ATTEMPT", status="NOT_FOUND",
             target_entity_type="MonthlyReport", target_entity_id=report_id,
             details=f"User '{current_user_from_dep.username}' attempted to view non-existent monthly report ID {report_id}."
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oylik hisobot topilmadi")

    # Agar muvaffaqiyatli ko'rishni ham loglash kerak bo'lsa:
    log_action(
        db=db, request=request, current_user=current_user_from_dep,
        action_name="VIEW_MONTHLY_REPORT", status="SUCCESS",
        target_entity_type="MonthlyReport", target_entity_id=report_id,
        details=f"User '{current_user_from_dep.username}' viewed monthly report ID {report_id} for {report_with_details.report_month.strftime('%Y-%m')}."
    )
    return report_with_details


# --- Visualization Data Endpoints (Hozircha logsiz) ---
@router.get(
    "/reports/visualization/ingredient-consumption",
    response_model=List[schemas.IngredientConsumptionDataPoint],
    summary="Ingredientlar iste'moli grafigi uchun ma'lumotlar",
    dependencies=[Security(security.get_current_manager_user)]
)
async def get_ingredient_consumption_chart_data_endpoint(
        start_date: date = Query(..., description="Boshlanish sanasi (YYYY-MM-DD)"),
        end_date: date = Query(..., description="Tugash sanasi (YYYY-MM-DD)"),
        product_id: Optional[int] = Query(None, description="Aniq bir mahsulot IDsi bo'yicha filtrlash"),
        db: Session = Depends(get_db)
):
    if start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Boshlanish sanasi tugash sanasidan keyin bo'lishi mumkin emas.")
    consumption_data = crud.get_ingredient_consumption_data(db, start_date, end_date, product_id)
    return consumption_data


@router.get(
    "/reports/visualization/product-delivery-trends",
    response_model=List[schemas.ProductDeliveryDataPoint],
    summary="Mahsulotlarning kelib tushish trendlari grafigi uchun ma'lumotlar",
    dependencies=[Security(security.get_current_manager_user)]
)
async def get_product_delivery_chart_data_endpoint(
        start_date: date = Query(..., description="Boshlanish sanasi (YYYY-MM-DD)"),
        end_date: date = Query(..., description="Tugash sanasi (YYYY-MM-DD)"),
        product_id: Optional[int] = Query(None, description="Aniq bir mahsulot IDsi bo'yicha filtrlash"),
        db: Session = Depends(get_db)
):
    if start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Boshlanish sanasi tugash sanasidan keyin bo'lishi mumkin emas.")
    delivery_data = crud.get_product_delivery_trends(db, start_date, end_date, product_id)
    return delivery_data



