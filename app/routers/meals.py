# app/routers/meals.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Security, Request # Request ni import qiling
from sqlalchemy.orm import Session
from typing import List, Optional

from app import crud, schemas, models, security
from app.database import get_db
from app.config import settings
from app.celery_config import redis_client_for_celery_config as redis_client, \
    WS_MESSAGE_CHANNEL
from app.schemas import WebSocketMessage, MealDefinitionUpdatedPayload, MealDeletedPayload # Payload sxemalarini import qiling
from app.tasks.portion_tasks import task_update_all_possible_meal_portions_celery
from app.logging_utils import log_action # log_action ni import qiling

router = APIRouter(
    prefix=settings.API_V1_STR + "/meals",
    tags=["Meals & Recipes Management"],
)


# app/routers/meals.py
# ... (boshqa importlar, MealDefinitionUpdatedPayload va WebSocketMessage import qilinganiga ishonch hosil qiling) ...

@router.post(
    "/",
    response_model=schemas.Meal,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi ovqat va uning retseptini yaratish",
    dependencies=[Security(security.get_current_manager_user)]
)
def create_new_meal(
        request: Request,
        meal_in: schemas.MealCreate,
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_manager_user)
):
    db_meal_by_name = crud.get_meal_by_name(db, name=meal_in.name)
    if db_meal_by_name:
        details_log = f"Meal creation failed by user '{current_user_from_dep.username}'. Meal name '{meal_in.name}' already exists."
        try:
            log_action(db=db, request=request, current_user=current_user_from_dep, action_name="CREATE_MEAL_ATTEMPT",
                       status="FAILURE", details=details_log, changes_after=meal_in.model_dump(mode='json'))
            db.commit()  # Xatolik logini saqlash
        except Exception as log_e:
            print(f"CRITICAL: Failed to write FAILURE audit log for meal creation (name exists): {log_e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"'{meal_in.name}' nomli ovqat allaqachon mavjud.")

    for ing_data in meal_in.ingredients:
        db_product = crud.get_product(db, product_id=ing_data.product_id)
        if not db_product:
            details_log = f"Meal creation by user '{current_user_from_dep.username}' failed. Ingredient product ID {ing_data.product_id} not found for meal '{meal_in.name}'."
            try:
                log_action(db=db, request=request, current_user=current_user_from_dep,
                           action_name="CREATE_MEAL_ATTEMPT", status="FAILURE", details=details_log,
                           changes_after=meal_in.model_dump(mode='json'))
                db.commit()
            except Exception as log_e:
                print(f"CRITICAL: Failed to write FAILURE audit log for meal creation (product not found): {log_e}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Ingredient uchun ID={ing_data.product_id} bo'lgan mahsulot topilmadi.")
        db_unit = crud.get_unit(db, unit_id=ing_data.unit_id)
        if not db_unit:
            details_log = f"Meal creation by user '{current_user_from_dep.username}' failed. Ingredient unit ID {ing_data.unit_id} not found for meal '{meal_in.name}'."
            try:
                log_action(db=db, request=request, current_user=current_user_from_dep,
                           action_name="CREATE_MEAL_ATTEMPT", status="FAILURE", details=details_log,
                           changes_after=meal_in.model_dump(mode='json'))
                db.commit()
            except Exception as log_e:
                print(f"CRITICAL: Failed to write FAILURE audit log for meal creation (unit not found): {log_e}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Ingredient uchun ID={ing_data.unit_id} bo'lgan o'lchov birligi topilmadi.")

    try:
        # 1. Ovqatni yaratish (crud.create_meal commit qilmaydi)
        # Bu funksiya db.add, flush, refresh qiladi
        created_meal_orm = crud.create_meal(db=db, meal_data=meal_in, user_id=current_user_from_dep.id)

        # 2. Log yozish (crud.create_audit_log_entry commit qilmaydi)
        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="CREATE_MEAL", status="SUCCESS",
            target_entity_type="Meal", target_entity_id=created_meal_orm.id,
            details=f"Meal '{created_meal_orm.name}' created successfully by user '{current_user_from_dep.username}'.",
            changes_after=schemas.Meal.model_validate(created_meal_orm).model_dump(mode='json')
        )

        # ***** MUHIM: Yagona COMMIT *****
        db.commit()  # Ovqat, ingredientlar va log yozuvini saqlash

        # Javob qaytarishdan oldin obyektni va uning bog'liqliklarini to'liq yuklash
        # crud.create_meal allaqachon refresh qilgan, lekin yana bir bor ishonch hosil qilish uchun
        # yoki agar selectinload bilan to'liqroq ma'lumot kerak bo'lsa.
        # Eng yaxshisi, ID orqali qayta o'qish:
        final_created_meal = crud.get_meal(db,
                                           created_meal_orm.id)  # Bu selectinload bilan ingredientlarni ham yuklaydi
        if not final_created_meal:
            # Bu deyarli bo'lmasligi kerak
            raise HTTPException(status_code=500, detail="Failed to retrieve created meal after commit.")

        # Keyingi amallar
        task_update_all_possible_meal_portions_celery.delay()
        ws_payload_new_meal = MealDefinitionUpdatedPayload(
            meal_id=final_created_meal.id,
            meal_name=final_created_meal.name,
            message=f"Yangi '{final_created_meal.name}' ovqati tizimga qo'shildi."
        )
        ws_message_obj_new_meal = WebSocketMessage(type="meal_definition_updated", payload=ws_payload_new_meal)
        redis_client.publish(WS_MESSAGE_CHANNEL, ws_message_obj_new_meal.model_dump_json())

        return final_created_meal  # To'liq yuklangan obyektni qaytarish

    except HTTPException:
        db.rollback()  # Agar yuqoridagi if bloklarida xatolik bo'lsa va bu yerga yetib kelsa
        raise
    except Exception as e:
        db.rollback()  # Asosiy try bloki ichidagi kutilmagan xatolik uchun
        error_log_details = f"Unexpected error during meal creation by user '{current_user_from_dep.username}': {str(e)}"
        try:
            log_action(
                db=db, request=request, current_user=current_user_from_dep,
                action_name="CREATE_MEAL_ATTEMPT", status="ERROR",
                details=error_log_details,
                changes_after=meal_in.model_dump(mode='json')
            )
            db.commit()  # Xatolik logini saqlashga urinish
        except Exception as log_e:
            print(f"CRITICAL: Failed to write ERROR audit log after meal creation failure: {log_e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Ovqat yaratishda kutilmagan xatolik: {error_log_details}")

@router.get(
    "/",
    response_model=List[schemas.Meal],
    summary="Barcha ovqatlar ro'yxati (retseptlari bilan)",
    dependencies=[Security(security.get_current_active_user)]
)
def read_all_meals(
        # request: Request, # GET so'rovlarini odatda loglamaymiz, agar maxsus talab bo'lmasa
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=200),
        active_only: Optional[bool] = Query(None,
                                            description="Status bo'yicha filtr: True - faqat faol, False - faqat nofaol, None - hammasi"),
        name_filter: Optional[str] = Query(None, description="Ovqat nomini qisman qidirish"),
        db: Session = Depends(get_db)
):
    meals = crud.get_meals(db, skip=skip, limit=limit, active_only=active_only, name_filter=name_filter)
    return meals


@router.get(
    "/available-for-serving",
    response_model=List[schemas.MealPortionInfo],
    summary="Tayyorlash mumkin bo'lgan faol ovqatlar ro'yxati",
    dependencies=[Security(security.get_current_active_user)]
)
def get_meals_available_for_serving(
        db: Session = Depends(get_db)
):
    available_meals = crud.get_possible_meal_portions_list(db, limit=100)
    return [meal_info for meal_info in available_meals if meal_info.possible_portions > 0]


@router.get(
    "/{meal_id}",
    response_model=schemas.Meal,
    summary="ID bo'yicha ovqatni olish (retsepti bilan)",
    dependencies=[Security(security.get_current_active_user)]
)
def read_meal_by_id(
        meal_id: int,
        db: Session = Depends(get_db)
):
    db_meal = crud.get_meal(db, meal_id=meal_id)
    if db_meal is None:
        # Bu yerda log yozish mumkin (masalan, agar kimdir mavjud bo'lmagan ID ni so'rasa)
        # log_action(...)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ovqat topilmadi")
    return db_meal


# app/routers/meals.py
# ... (boshqa importlar, MealDefinitionUpdatedPayload va WebSocketMessage import qilinganiga ishonch hosil qiling) ...
from datetime import datetime  # Agar crud.update_meal ichida datetime.now() ishlatilmasa


@router.put(
    "/{meal_id}",
    response_model=schemas.Meal,
    summary="Mavjud ovqatni va retseptini yangilash",
    dependencies=[Security(security.get_current_manager_user)]
)
async def update_existing_meal(
        request: Request,  # Birinchi parametr
        meal_id: int,
        meal_in: schemas.MealUpdate,
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_manager_user)
):
    db_meal_to_update = crud.get_meal(db, meal_id=meal_id)  # Bu selectinload bilan keladi
    if db_meal_to_update is None:
        details_log = f"Meal ID {meal_id} not found for update by user '{current_user_from_dep.username}'."
        try:
            log_action(db=db, request=request, current_user=current_user_from_dep, action_name="UPDATE_MEAL_ATTEMPT",
                       status="NOT_FOUND", target_entity_type="Meal", target_entity_id=meal_id, details=details_log)
            db.commit()  # Xatolik logini saqlash
        except Exception as log_e:
            print(f"CRITICAL: Failed to write NOT_FOUND audit log for meal update: {log_e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yangilash uchun ovqat topilmadi")

    old_meal_data_for_log = schemas.Meal.model_validate(db_meal_to_update).model_dump(mode='json')

    if meal_in.name and meal_in.name != db_meal_to_update.name:
        existing_meal_with_new_name = crud.get_meal_by_name(db, name=meal_in.name)
        if existing_meal_with_new_name and existing_meal_with_new_name.id != meal_id:
            details_log = f"Update meal by user '{current_user_from_dep.username}' failed for meal ID {meal_id}. New name '{meal_in.name}' already exists."
            try:
                log_action(db=db, request=request, current_user=current_user_from_dep,
                           action_name="UPDATE_MEAL_ATTEMPT", status="FAILURE", target_entity_type="Meal",
                           target_entity_id=meal_id, details=details_log, changes_before=old_meal_data_for_log,
                           changes_after=meal_in.model_dump(exclude_unset=True, mode='json'))
                db.commit()
            except Exception as log_e:
                print(f"CRITICAL: Failed to write FAILURE audit log for meal update (name exists): {log_e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"'{meal_in.name}' nomli ovqat allaqachon mavjud.")

    if meal_in.ingredients:
        for ing_data in meal_in.ingredients:
            db_product = crud.get_product(db, product_id=ing_data.product_id)
            if not db_product:
                details_log = f"Update meal by user '{current_user_from_dep.username}' failed for meal ID {meal_id}. Ingredient product ID {ing_data.product_id} not found."
                try:
                    log_action(db=db, request=request, current_user=current_user_from_dep,
                               action_name="UPDATE_MEAL_ATTEMPT", status="FAILURE", target_entity_type="Meal",
                               target_entity_id=meal_id, details=details_log, changes_before=old_meal_data_for_log,
                               changes_after=meal_in.model_dump(exclude_unset=True, mode='json'))
                    db.commit()
                except Exception as log_e:
                    print(f"CRITICAL: Failed to write FAILURE audit log for meal update (product not found): {log_e}")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Ingredient uchun ID={ing_data.product_id} bo'lgan mahsulot topilmadi.")
            db_unit = crud.get_unit(db, unit_id=ing_data.unit_id)
            if not db_unit:
                details_log = f"Update meal by user '{current_user_from_dep.username}' failed for meal ID {meal_id}. Ingredient unit ID {ing_data.unit_id} not found."
                try:
                    log_action(db=db, request=request, current_user=current_user_from_dep,
                               action_name="UPDATE_MEAL_ATTEMPT", status="FAILURE", target_entity_type="Meal",
                               target_entity_id=meal_id, details=details_log, changes_before=old_meal_data_for_log,
                               changes_after=meal_in.model_dump(exclude_unset=True, mode='json'))
                    db.commit()
                except Exception as log_e:
                    print(f"CRITICAL: Failed to write FAILURE audit log for meal update (unit not found): {log_e}")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Ingredient uchun ID={ing_data.unit_id} bo'lgan o'lchov birligi topilmadi.")

    try:
        # 1. Ovqatni yangilash (crud.update_meal commit qilmaydi)
        # Bu funksiya o'zgartirilgan va refresh qilingan ORM obyektini qaytaradi
        updated_meal_orm = crud.update_meal(db=db, meal_id=meal_id, meal_update_data=meal_in,
                                            user_id=current_user_from_dep.id)

        if updated_meal_orm is None:  # Bu holat agar get_meal None qaytarsa (yuqorida tekshirilgan)
            details_log_err = f"Meal ID {meal_id} update returned None unexpectedly by user '{current_user_from_dep.username}'."
            try:
                log_action(db=db, request=request, current_user=current_user_from_dep,
                           action_name="UPDATE_MEAL_ATTEMPT", status="ERROR", target_entity_type="Meal",
                           target_entity_id=meal_id, details=details_log_err, changes_before=old_meal_data_for_log,
                           changes_after=meal_in.model_dump(exclude_unset=True, mode='json'))
                db.commit()
            except Exception as log_e:
                print(f"CRITICAL: Failed to write ERROR audit log for meal update (None returned): {log_e}")
            # db.rollback() # Bu yerda rollback kerak emas, chunki hali commit bo'lmagan
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Ovqatni yangilashda noma'lum xatolik (obyekt qaytarilmadi).")

        # 2. Log yozish (crud.create_audit_log_entry commit qilmaydi)
        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="UPDATE_MEAL", status="SUCCESS",
            target_entity_type="Meal", target_entity_id=updated_meal_orm.id,
            details=f"Meal '{updated_meal_orm.name}' (ID: {meal_id}) updated by user '{current_user_from_dep.username}'.",
            changes_before=old_meal_data_for_log,  # Bu allaqachon mode='json' qilingan
            changes_after=schemas.Meal.model_validate(updated_meal_orm).model_dump(mode='json')
            # Yangilangan to'liq holat
        )

        # ***** MUHIM: Yagona COMMIT *****
        db.commit()

        # Javob qaytarishdan oldin obyektni qayta refresh qilish shart emas,
        # chunki crud.update_meal oxirida get_meal(db, meal_id) ni chaqiradi,
        # bu esa selectinload bilan to'liq yuklangan obyektni qaytaradi.
        # db.refresh(updated_meal_orm) # Agar crud.update_meal faqat refresh qilsa, bu kerak bo'lardi

        # Keyingi amallar
        task_update_all_possible_meal_portions_celery.delay()
        ws_payload_meal_updated = MealDefinitionUpdatedPayload(
            meal_id=updated_meal_orm.id,
            meal_name=updated_meal_orm.name,
            message=f"'{updated_meal_orm.name}' ovqati yangilandi."
        )
        ws_message_obj_meal_updated = WebSocketMessage(type="meal_definition_updated", payload=ws_payload_meal_updated)
        redis_client.publish(WS_MESSAGE_CHANNEL, ws_message_obj_meal_updated.model_dump_json())

        return updated_meal_orm

    except HTTPException:
        # Agar xatolik yuqoridagi if bloklarida yuzaga kelsa va log yozilib, commit qilingan bo'lsa,
        # bu yerda rollback qilish o'sha logni bekor qilmaydi.
        # Agar asosiy try blokida xatolik bo'lsa, rollback kerak.
        # Hozirgi holatda, har bir xatolik logi alohida commit qilinmoqda.
        db.rollback()  # Agar asosiy try blokida log_action dan keyin xatolik bo'lsa
        raise
    except Exception as e:
        db.rollback()  # Asosiy try bloki ichidagi kutilmagan xatolik uchun
        error_log_details = f"Unexpected error updating meal ID {meal_id} by user '{current_user_from_dep.username}': {str(e)}"
        try:
            log_action(
                db=db, request=request, current_user=current_user_from_dep,
                action_name="UPDATE_MEAL_ATTEMPT", status="ERROR",
                target_entity_type="Meal", target_entity_id=meal_id,
                details=error_log_details,
                changes_before=old_meal_data_for_log,
                changes_after=meal_in.model_dump(exclude_unset=True, mode='json')
            )
            db.commit()  # Xatolik logini saqlashga urinish
        except Exception as log_e:
            print(f"CRITICAL: Failed to write ERROR audit log after meal update failure: {log_e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Ovqatni yangilashda kutilmagan server xatoligi: {error_log_details}")


# app/routers/meals.py
# ... (boshqa importlar, MealDeletedPayload va WebSocketMessage import qilinganiga ishonch hosil qiling) ...
from datetime import datetime  # Agar crud.soft_delete_meal ichida datetime.now() ishlatilmasa


@router.delete(
    "/{meal_id}",
    response_model=schemas.Meal,
    summary="Ovqatni \"soft delete\" qilish",
    dependencies=[Security(security.get_current_admin_user)]
)
async def soft_delete_existing_meal(
        request: Request,  # Birinchi parametr
        meal_id: int,
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_admin_user)
):
    db_meal_to_delete = crud.get_meal(db, meal_id=meal_id)  # Bu selectinload bilan keladi
    if db_meal_to_delete is None:
        details_log = f"Meal ID {meal_id} not found for deletion by user '{current_user_from_dep.username}'."
        try:
            log_action(
                db=db, request=request, current_user=current_user_from_dep,
                action_name="DELETE_MEAL_ATTEMPT", status="NOT_FOUND",
                target_entity_type="Meal", target_entity_id=meal_id,
                details=details_log
            )
            db.commit()  # Xatolik logini saqlash
        except Exception as log_e:
            print(f"CRITICAL: Failed to write NOT_FOUND audit log for meal deletion: {log_e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="O'chirish uchun ovqat topilmadi")

    old_meal_data_for_log = schemas.Meal.model_validate(db_meal_to_delete).model_dump(mode='json')

    # Ovqatni o'chirishdan oldin boshqa tekshiruvlar bo'lsa (masalan, bog'liq aktiv servinglar), shu yerga qo'shiladi
    # Hozircha bunday tekshiruv yo'q.

    try:
        # 1. Ovqatni "soft delete" qilish (crud.soft_delete_meal commit qilmaydi)
        # Bu funksiya o'zgartirilgan va refresh qilingan ORM obyektini qaytaradi

        # Yoki logikani shu yerga olib chiqamiz:
        db_meal_to_delete.deleted_at = datetime.now()
        db_meal_to_delete.is_active = False
        db.add(db_meal_to_delete)  # O'zgartirilgan obyektni sessiyaga qo'shish

        # deleted_product_orm o'rniga db_meal_to_delete ni ishlatamiz, chunki u allaqachon o'zgartirildi
        # Agar crud.soft_delete_meal dan foydalansak:
        # deleted_meal_orm = crud.soft_delete_meal(db=db, meal_id=meal_id)
        # if deleted_meal_orm is None: ... (bu holat deyarli bo'lmaydi, chunki db_meal_to_delete mavjud edi)

        # 2. Log yozish (crud.create_audit_log_entry commit qilmaydi)
        log_action(
            db=db, request=request, current_user=current_user_from_dep,
            action_name="DELETE_MEAL", status="SUCCESS",
            target_entity_type="Meal", target_entity_id=db_meal_to_delete.id,
            details=f"Meal '{db_meal_to_delete.name}' (ID: {meal_id}) soft deleted by user '{current_user_from_dep.username}'.",
            changes_before=old_meal_data_for_log,
            changes_after={
                "deleted_at": db_meal_to_delete.deleted_at.isoformat() if db_meal_to_delete.deleted_at else None,
                "is_active": db_meal_to_delete.is_active
            }
        )

        # ***** MUHIM: Yagona COMMIT *****
        db.commit()  # Ovqatni soft delete qilish va audit log yozuvini saqlash

        # Commitdan keyin obyektni refresh qilish (agar javob uchun kerak bo'lsa)
        db.refresh(db_meal_to_delete)
        # Agar ingredientlar kabi bog'liqliklar ham javobda kerak bo'lsa (hozirgi schemas.Meal talab qiladi):
        # final_deleted_meal = crud.get_meal(db, db_meal_to_delete.id) # Bu selectinload bilan keladi
        # if not final_deleted_meal: ... handle error ...

        # Keyingi amallar
        task_update_all_possible_meal_portions_celery.delay()
        ws_payload_meal_deleted = MealDeletedPayload(
            meal_id=db_meal_to_delete.id,
            meal_name=db_meal_to_delete.name,
            message=f"'{db_meal_to_delete.name}' ovqati o'chirildi/noaktiv qilindi."
        )
        ws_message_obj_meal_deleted = WebSocketMessage(type="meal_deleted", payload=ws_payload_meal_deleted)
        redis_client.publish(WS_MESSAGE_CHANNEL, ws_message_obj_meal_deleted.model_dump_json())

        return db_meal_to_delete  # Yoki final_deleted_meal

    except HTTPException:  # Biz o'zimiz ko'targan HTTPException lar
        db.rollback()
        raise
    except Exception as e:
        db.rollback()  # Asosiy try bloki ichidagi kutilmagan xatolik uchun
        error_log_details = f"Unexpected error deleting meal ID {meal_id} by user '{current_user_from_dep.username}': {str(e)}"
        try:
            log_action(
                db=db, request=request, current_user=current_user_from_dep,
                action_name="DELETE_MEAL_ATTEMPT", status="ERROR",
                target_entity_type="Meal", target_entity_id=meal_id,
                details=error_log_details,
                changes_before=old_meal_data_for_log
            )
            db.commit()  # Xatolik logini saqlashga urinish
        except Exception as log_e:
            print(f"CRITICAL: Failed to write ERROR audit log after meal deletion failure: {log_e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Ovqatni o'chirishda kutilmagan server xatoligi: {error_log_details}")


# app/routers/meals.py (yoki qaysi faylda bo'lsa)
# ... (boshqa importlar)

@router.post(
    "/recalculate-possible-portions/",
    status_code=status.HTTP_202_ACCEPTED,  # Amal qabul qilindi, fonda bajariladi
    response_model=schemas.Msg,  # Yoki Dict[str, str]
    summary="Barcha ovqatlar uchun mumkin porsiyalarni qayta hisoblashni ishga tushirish",
    dependencies=[Security(security.get_current_manager_user)]
)
async def trigger_recalculate_possible_portions_endpoint(
        request: Request,
        db: Session = Depends(get_db),
        current_user_from_dep: models.User = Depends(security.get_current_manager_user)
):
    """
    Barcha faol ovqatlar uchun tayyorlanishi mumkin bo'lgan porsiyalarni
    Celery orqali qayta hisoblashni majburiy ishga tushirish (Menejer yoki Admin uchun).
    Bu operatsiya fonda bajariladi va bu harakat loglanadi.
    """
    try:
        # Celery taskini ishga tushirish
        task = task_update_all_possible_meal_portions_celery.delay()

        # Harakatni loglash
        log_action(
            db=db,
            request=request,
            current_user=current_user_from_dep,
            action_name="TRIGGER_RECALCULATE_PORTIONS",
            status="INITIATED",  # Yoki "SCHEDULED"
            details=f"Manual recalculation of all possible meal portions triggered via Celery by user '{current_user_from_dep.username}'. Task ID: {task.id}",
            # Bu amal to'g'ridan-to'g'ri DB obyektini o'zgartirmagani uchun target_entity va changes yo'q
        )

        # Log yozuvini saqlash uchun commit
        db.commit()

        return {
            "msg": f"Barcha ovqatlar uchun mumkin bo'lgan porsiyalarni qayta hisoblash Celery orqali rejalashtirildi. Task ID: {task.id}"
        }
    except Exception as e:
        # Agar log yozishda yoki taskni ishga tushirishda kutilmagan xatolik bo'lsa
        db.rollback()  # Agar log_action db.add qilgan bo'lsa-yu, commit bo'lmagan bo'lsa
        error_log_details = f"Unexpected error triggering recalculate portions by user '{current_user_from_dep.username}': {str(e)}"
        try:
            # Xatolik logini yozishga urinish
            log_action(
                db=db, request=request, current_user=current_user_from_dep,
                action_name="TRIGGER_RECALCULATE_PORTIONS_ATTEMPT", status="ERROR",
                details=error_log_details
            )
            db.commit()
        except Exception as log_e:
            print(f"CRITICAL: Failed to write ERROR audit log for triggering recalculate portions: {log_e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Porsiyalarni qayta hisoblashni ishga tushirishda kutilmagan xatolik: {str(e)}"
        )


