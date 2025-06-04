# app/routers/audit_logs.py
from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy.orm import Session
from typing import List, Optional
from app import schemas, models, security # security ni import qilishni unutmang
from app.database import get_db
from app.config import settings
from datetime import datetime # datetime ni import qilish

router = APIRouter(
    prefix=settings.API_V1_STR + "/audit-logs",
    tags=["Audit Logs"],
    dependencies=[Security(security.get_current_admin_user)] # Faqat Admin uchun
)

@router.get("/", response_model=List[schemas.AuditLog], summary="Barcha audit log yozuvlari")
def read_audit_logs(
    # request: Request, # Agar bu GET so'rovini ham loglamoqchi bo'lsangiz
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    user_id: Optional[int] = Query(None, description="Foydalanuvchi IDsi bo'yicha filtr"),
    username_filter: Optional[str] = Query(None, alias="username", description="Foydalanuvchi nomi (username) bo'yicha qisman filtr"),
    action_filter: Optional[str] = Query(None, alias="action", description="Amal turi bo'yicha qisman filtr (masalan, CREATE_PRODUCT)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Status bo'yicha filtr (SUCCESS, FAILURE)"),
    target_entity_type_filter: Optional[str] = Query(None, alias="target_entity_type", description="Obyekt turi bo'yicha filtr"),
    target_entity_id_filter: Optional[int] = Query(None, alias="target_entity_id", description="Obyekt IDsi bo'yicha filtr"),
    start_date: Optional[datetime] = Query(None, description="Boshlanish sanasi va vaqti (YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[datetime] = Query(None, description="Tugash sanasi va vaqti (YYYY-MM-DDTHH:MM:SS)"),
    db: Session = Depends(get_db),
    current_admin_from_dep: models.User = Depends(security.get_current_admin_user) # Joriy adminni olish
):
    """
    Audit log yozuvlarini filtrlash imkoniyati bilan olish (Faqat Admin).
    """
    query = db.query(models.AuditLog)
    if user_id is not None:
        query = query.filter(models.AuditLog.user_id == user_id)
    if username_filter:
        query = query.filter(models.AuditLog.username.ilike(f"%{username_filter}%"))
    if action_filter:
        query = query.filter(models.AuditLog.action.ilike(f"%{action_filter}%"))
    if status_filter:
        query = query.filter(models.AuditLog.status.ilike(f"%{status_filter}%")) # .ilike() yoki == status_filter
    if target_entity_type_filter:
        query = query.filter(models.AuditLog.target_entity_type.ilike(f"%{target_entity_type_filter}%"))
    if target_entity_id_filter is not None:
        query = query.filter(models.AuditLog.target_entity_id == target_entity_id_filter)
    if start_date:
        query = query.filter(models.AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(models.AuditLog.timestamp <= end_date)

    logs = query.order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return logs