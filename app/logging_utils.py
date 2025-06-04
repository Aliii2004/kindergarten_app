# app/utils.py yoki yangi app/logging_utils.py faylida
from fastapi import Request
from sqlalchemy.orm import Session
from typing import Optional, Any, Dict
from app import crud, models # models ni to'g'ri import qiling

def log_action(
    db: Session,
    request: Optional[Request], # IP manzil va user_agent ni olish uchun
    current_user: Optional[models.User], # Kim amalni bajargani
    action_name: str,
    status: str = "SUCCESS",
    target_entity_type: Optional[str] = None,
    target_entity_id: Optional[int] = None,
    details: Optional[str] = None,
    changes_before: Optional[Dict[str, Any]] = None,
    changes_after: Optional[Dict[str, Any]] = None
):
    user_id_log = current_user.id if current_user else None
    username_log = current_user.username if current_user else "System" # Yoki "Anonymous"
    ip_address_log = request.client.host if request and request.client else None
    user_agent_log = request.headers.get("user-agent") if request else None

    crud.create_audit_log_entry(
        db=db,
        user_id=user_id_log,
        username=username_log,
        action=action_name,
        status=status,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        details=details,
        changes_before=changes_before,
        changes_after=changes_after,
        ip_address=ip_address_log,
        user_agent=user_agent_log
    )