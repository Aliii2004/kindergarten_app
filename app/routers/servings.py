# app/routers/servings.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Security, Request # Request ni import qiling
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app import crud, schemas, models, security
from app.database import get_db
from app.config import settings
from app.celery_config import redis_client_for_celery_config as redis_client, \
    WS_MESSAGE_CHANNEL

from app.schemas import WebSocketMessage, NewMealServedPayload
from app.tasks.portion_tasks import task_update_all_possible_meal_portions_celery, \
    task_check_product_stock_and_notify_celery
from app.logging_utils import log_action # log_action ni import qiling

router = APIRouter(
    prefix=settings.API_V1_STR + "/servings",
    tags=["Meal Servings & Consumption Log"],
)


@router.post(
    "/",
    response_model=schemas.MealServingWithDetails,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi ovqat berilishini qayd etish",
    dependencies=[Security(security.get_current_chef_user)]
)
async def create_new_meal_serving(
        request: Request,
        serving_in: schemas.MealServingCreate,
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_chef_user)
):
    db_meal = crud.get_meal(db, serving_in.meal_id) # Bu selectinload bilan ingredientlarni yuklaydi
    if not db_meal or not db_meal.is_active:
        details_log = f"Meal serving creation failed by user '{current_user_from_dep.username}'. Meal ID {serving_in.meal_id} not found or not active."
        try:
            log_action(db=db, request=request, current_user=current_user_from_dep, action_name="CREATE_MEAL_SERVING_ATTEMPT", status="FAILURE_NOT_FOUND", target_entity_type="Meal", target_entity_id=serving_in.meal_id, details=details_log, changes_after=serving_in.model_dump(mode='json'))
            db.commit() # Xatolik logini saqlash
        except Exception as log_e:
            print(f"CRITICAL: Failed to write FAILURE_NOT_FOUND audit log for meal serving: {log_e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ovqat topilmadi yoki faol emas.")

    # Bu funksiya (ORM_Object | None, ErrorMessage | None) qaytaradi
    # Yoki ideal holda, xatolik bo'lsa Exception ko'taradi
    created_serving_orm, error_message_crud = crud.create_meal_serving(db=db, serving_data=serving_in, user_id=current_user_from_dep.id)

    if error_message_crud:
        details_log = f"Meal serving creation failed for meal '{db_meal.name}' by user '{current_user_from_dep.username}'. Reason: {error_message_crud}"
        try:
            log_action(db=db, request=request, current_user=current_user_from_dep, action_name="CREATE_MEAL_SERVING_ATTEMPT", status="VALIDATION_ERROR", target_entity_type="Meal", target_entity_id=serving_in.meal_id, details=details_log, changes_after=serving_in.model_dump(mode='json'))
            db.commit()
        except Exception as log_e:
            print(f"CRITICAL: Failed to write VALIDATION_ERROR audit log for meal serving: {log_e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message_crud)

    if not created_serving_orm: # Agar crud.create_meal_serving None qaytarsa (kutilmagan xatolik)
        details_log_err = f"Meal serving creation for meal '{db_meal.name}' by user '{current_user_from_dep.username}' returned None from CRUD unexpectedly."
        try:
            log_action(db=db, request=request, current_user=current_user_from_dep, action_name="CREATE_MEAL_SERVING_ATTEMPT", status="ERROR_CRUD", target_entity_type="Meal", target_entity_id=serving_in.meal_id, details=details_log_err, changes_after=serving_in.model_dump(mode='json'))
            db.commit()
        except Exception as log_e:
            print(f"CRITICAL: Failed to write ERROR_CRUD audit log for meal serving: {log_e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ovqat berishni qayd etishda noma'lum server xatoligi (CRUD dan).")

    try:
        # Log yozish (crud.create_audit_log_entry commit qilmaydi)
        # created_serving_orm allaqachon to'liq (get_meal_serving_with_details orqali)
        serving_details_log = []
        if created_serving_orm.serving_details:
            for sd in created_serving_orm.serving_details:
                serving_details_log.append({ "product_id": sd.product_id, "product_name": sd.product.name if sd.product else "N/A", "quantity_used": sd.quantity_used })

        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="CREATE_MEAL_SERVING", status="SUCCESS",
            target_entity_type="MealServing", target_entity_id=created_serving_orm.id,
            details=f"{created_serving_orm.portions_served} portions of meal '{db_meal.name}' (Meal ID: {db_meal.id}) served by user '{current_user_from_dep.username}'.",
            changes_after={
                "serving_info": schemas.MealServing.model_validate(created_serving_orm).model_dump(mode='json'),
                "consumed_ingredients": serving_details_log
            }
        )

        # ***** Yagona COMMIT *****
        db.commit() # MealServing, ServingDetail va AuditLog yozuvlarini saqlash

        # Javob uchun obyektni qayta refresh qilish (agar kerak bo'lsa, lekin created_serving_orm allaqachon to'liq)
        # db.refresh(created_serving_orm) # Barcha bog'liqliklar bilan refresh qilish kerak bo'lsa
        # Yoki ID orqali qayta o'qish:
        final_serving_for_response = crud.get_meal_serving_with_details(db, created_serving_orm.id)
        if not final_serving_for_response:
            # Bu deyarli bo'lmasligi kerak
            raise HTTPException(status_code=500, detail="Failed to retrieve created meal serving after commit.")


        # Keyingi amallar
        task_update_all_possible_meal_portions_celery.delay()
        # serving_details_for_tasks ni final_serving_for_response dan olish kerak
        if final_serving_for_response.serving_details:
            for detail in final_serving_for_response.serving_details:
                task_check_product_stock_and_notify_celery.delay(detail.product_id)

        ws_payload_served = NewMealServedPayload(
            serving_id=final_serving_for_response.id,
            meal_id=final_serving_for_response.meal_id,
            meal_name=db_meal.name, # Yoki final_serving_for_response.meal.name
            portions_served=final_serving_for_response.portions_served,
            served_at=final_serving_for_response.served_at.isoformat(),
            served_by_user_name=current_user_from_dep.full_name,
            message=f"'{db_meal.name}' ovqatidan {final_serving_for_response.portions_served} porsiya {current_user_from_dep.full_name} tomonidan berildi."
        )
        ws_message_obj_served = WebSocketMessage(type="new_meal_served", payload=ws_payload_served)
        redis_client.publish(WS_MESSAGE_CHANNEL, ws_message_obj_served.model_dump_json())

        return schemas.MealServingWithDetails.model_validate(final_serving_for_response)

    except HTTPException:
        db.rollback() # Agar log_action yoki boshqa DB o'zgarishi bo'lgan bo'lsa
        raise
    except Exception as e:
        db.rollback()
        error_log_details = f"Unexpected error after CRUD call in create_new_meal_serving by user '{current_user_from_dep.username}': {str(e)}"
        try:
            log_action(db=db, request=request, current_user=current_user_from_dep, action_name="CREATE_MEAL_SERVING_ATTEMPT", status="ERROR", target_entity_type="Meal", target_entity_id=serving_in.meal_id, details=error_log_details, changes_after=serving_in.model_dump(mode='json'))
            db.commit()
        except Exception as log_e:
            print(f"CRITICAL: Failed to write ERROR audit log after meal serving creation failure: {log_e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ovqat berishda kutilmagan server xatoligi: {error_log_details}")

@router.get(
    "/",
    response_model=List[schemas.MealServing],
    summary="Barcha ovqat berish holatlari ro'yxati",
    dependencies=[Security(security.get_current_manager_user)]
)
def read_all_meal_servings(
        # request: Request, # Agar loglamoqchi bo'lsangiz
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=200),
        meal_id: Optional[int] = Query(None, description="Ovqat IDsi bo'yicha filtrlash"),
        user_id: Optional[int] = Query(None, description="Ovqatni bergan foydalanuvchi IDsi bo'yicha filtrlash"),
        start_date: Optional[date] = Query(None, description="Berilgan sana (boshlanish) bo'yicha filtrlash (YYYY-MM-DD)"),
        end_date: Optional[date] = Query(None, description="Berilgan sana (tugash) bo'yicha filtrlash (YYYY-MM-DD)"),
        db: Session = Depends(get_db)
        # current_user_from_dep: models.User = Depends(security.get_current_manager_user) # Agar loglamoqchi bo'lsangiz
):
    servings_orm = crud.get_meal_servings(
        db, skip=skip, limit=limit, meal_id=meal_id, user_id=user_id, start_date=start_date, end_date=end_date
    )
    response_servings = []
    for s_orm in servings_orm:
        meal_name_val = s_orm.meal.name if s_orm.meal else None
        user_full_name_val = s_orm.served_by_user.full_name if s_orm.served_by_user else None
        serving_data_dict = schemas.MealServing.model_validate(s_orm).model_dump()
        serving_data_dict["meal_name"] = meal_name_val # Bu MealServing sxemasida allaqachon bo'lishi kerak (agar validation_alias ishlatilsa)
        serving_data_dict["served_by_user_full_name"] = user_full_name_val # Bu ham
        response_servings.append(schemas.MealServing(**serving_data_dict)) # Agar sxemada yo'q bo'lsa, bu xatolik beradi
    # Yaxshiroq yechim: schemas.MealServing da meal_name va served_by_user_full_name uchun @computed_field yoki
    # relationship larni to'g'ri yuklab, Pydantic avtomatik to'ldirishini ta'minlash.
    # Hozircha, sxema ichida bu maydonlar yo'q deb faraz qilib, ularni qo'shmaymiz,
    # CRUDda javobni boyitish kerak bo'ladi yoki sxemani moslashtirish kerak.
    # Avvalgi kodda bu maydonlar sxemaga qo'shilgan edi, shuning uchun o'sha sxemani ishlatish kerak.
    return servings_orm # To'g'ridan-to'g'ri ORM obyektlarini qaytarish (agar sxema to'g'ri bo'lsa)


@router.get(
    "/{serving_id}",
    response_model=schemas.MealServingWithDetails,
    summary="ID bo'yicha ovqat berish holatini olish (tafsilotlari bilan)",
    dependencies=[Security(security.get_current_manager_user)]
)
def read_meal_serving_by_id_with_details(
        serving_id: int,
        # request: Request, # Agar loglamoqchi bo'lsangiz
        db: Session = Depends(get_db)
        # current_user_from_dep: models.User = Depends(security.get_current_manager_user) # Agar loglamoqchi bo'lsangiz
):
    db_serving_with_details = crud.get_meal_serving_with_details(db, serving_id=serving_id)
    if db_serving_with_details is None:
        # log_action(...)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ovqat berish yozuvi topilmadi")
    return db_serving_with_details


