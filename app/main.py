# app/main.py
# import eventlet
# eventlet.monkey_patch()

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Dict, Any

import redis
from fastapi import (
    FastAPI, Depends, Request, WebSocket, WebSocketDisconnect,
    HTTPException, status, Query, Security
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session
from pathlib import Path

from app import crud, models, schemas, security
from app.database import engine, get_db, SessionLocal
from app.config import settings
from app.utils import create_initial_data

# Routerlarni import qilish
from app.routers import auth, users, products, meals, servings, reports, audit_logs

# WebSocket Connection Manager va Redis Pub/Sub
from app.websockets.connection_manager import manager as ws_manager
from app.schemas import WebSocketMessage
from app.celery_config import redis_client_for_celery_config as redis_client, \
    WS_MESSAGE_CHANNEL  # celery_config dan olamiz

# JWT xatoliklari uchun
from jose import JWTError, jwt


# --- Redis Pub/Sub Listener ---
async def redis_message_listener():
    """
    Redis Pub/Sub kanaliga obuna bo'ladi va kelgan xabarlarni
    WebSocket orqali barcha ulangan klientlarga (yoki kerakli guruhlarga) yuboradi.
    Bu funksiya FastAPI startup eventida `asyncio.create_task` orqali ishga tushiriladi.
    """
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    try:
        pubsub.subscribe(WS_MESSAGE_CHANNEL)
        print(f"INFO:     Successfully subscribed to Redis channel: '{WS_MESSAGE_CHANNEL}'")

        # Xabarlarni asinxron o'qish uchun
        # `pubsub.listen()` bloking, shuning uchun uni to'g'ridan-to'g'ri async funksiyada ishlatish qiyin.
        # `aioredis` kutubxonasi bu ishni osonlashtiradi, lekin hozirgi `redis` kutubxonasi bilan
        # `pubsub.get_message(timeout=...)` ni loopda ishlatish yoki `threading` bilan yechish mumkin.
        # Eng yaxshi yechim `aioredis` ishlatish.

        # Hozirgi `redis` kutubxonasi bilan (bloklanish xavfi bor, test qilish kerak):
        # while True:
        #     message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0) # timeout bilan
        #     if message and message['type'] == 'message':
        #         print(f"DEBUG:    Received message from Redis: {message['data']}")
        #         try:
        #             message_data_dict = json.loads(message['data'])
        #             # Bu yerda message_data_dict ni WebSocketMessage ga validatsiya qilish mumkin
        #             # schemas.WebSocketMessage.model_validate(message_data_dict)
        #             await ws_manager.broadcast_to_all_active(message_data_dict)
        #         except json.JSONDecodeError:
        #             print(f"ERROR:    Could not decode JSON from Redis message: {message['data']}")
        #         except Exception as e:
        #             print(f"ERROR:    Error broadcasting message from Redis via WebSocket: {e}")
        #     await asyncio.sleep(0.01) # Boshqa tasklarga ham imkon berish

        # `redis` >= 4.2.0rc1 `pubsub.listen()` generator qaytaradi, `async for` bilan ishlatsa bo'ladi.
        # Ammo hozirgi barqaror versiyalarda (masalan, 5.0.1) `listen()` bloking.
        # Keling, `get_message` bilan vaqtinchalik yechim qilamiz.
        # Production uchun `aioredis` yoki `listen()` ni alohida thread da ishlatish yaxshiroq.

        # Yaxshilangan yondashuv (get_message bilan, FastAPI async contextida ishlashi uchun):
        while True:
            # print("DEBUG: Checking Redis for messages...") # Har soniyada tekshirish (bu yaxshi emas)
            message = None
            try:
                message = pubsub.get_message(timeout=0.5)  # Non-blocking qilishga harakat
            except redis.exceptions.TimeoutError:
                await asyncio.sleep(0.1)  # Agar timeout bo'lsa, biroz kutish
                continue
            except redis.exceptions.ConnectionError as e:
                print(f"ERROR: Redis connection error in listener: {e}. Reconnecting...")
                await asyncio.sleep(5)  # 5 sekunddan keyin qayta ulanishga harakat qilish
                try:
                    # pubsub obyektini qayta yaratish kerak bo'lishi mumkin
                    pubsub.close()  # Eskisini yopish
                    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
                    pubsub.subscribe(WS_MESSAGE_CHANNEL)
                    print("INFO: Reconnected to Redis Pub/Sub.")
                except Exception as recon_e:
                    print(f"ERROR: Failed to reconnect to Redis Pub/Sub: {recon_e}")
                    await asyncio.sleep(10)  # Yana kutish
                continue

            if message and message['type'] == 'message':
                data_str = message['data']
                print(f"DEBUG:    Received message from Redis: {data_str}")
                try:
                    # Xabarni WebSocketMessage sxemasiga validatsiya qilish
                    message_obj = schemas.WebSocketMessage.model_validate_json(data_str)
                    await ws_manager.broadcast_to_all_active(message_obj.model_dump(mode='json'))
                except ValidationError as ve:
                    print(f"ERROR:    WebSocketMessage validation error from Redis: {ve.errors()}")
                except json.JSONDecodeError:
                    print(f"ERROR:    Could not decode JSON from Redis message: {data_str}")
                except Exception as e:
                    print(f"ERROR:    Error broadcasting message from Redis via WebSocket: {e}")

            await asyncio.sleep(0.1)  # Loopni juda tez aylantirmaslik uchun

    except Exception as e:
        print(f"FATAL_ERROR: Redis Pub/Sub listener failed: {e}")
    finally:
        if 'pubsub' in locals() and pubsub:
            print("INFO:     Unsubscribing and closing Redis Pub/Sub listener.")
            pubsub.unsubscribe()
            pubsub.close()


# --- FastAPI Lifespan (Startup va Shutdown hodisalari) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("INFO:     Application startup...")
    # Ma'lumotlar bazasi jadvallarini yaratish
    try:
        models.Base.metadata.create_all(bind=engine)
        print("INFO:     Database tables checked/created.")
        # Boshlang'ich ma'lumotlarni yaratish (agar kerak bo'lsa)
        db_for_startup = SessionLocal()
        try:
            admin_user = crud.get_user_by_username(db_for_startup, "admin")
            if not admin_user:
                print("INFO:     Admin user not found, running initial data setup...")
                create_initial_data(db_for_startup)
            else:
                print("INFO:     Initial data (admin user) already exists. Skipping setup.")

            possible_meals_count = db_for_startup.query(models.PossibleMeals).count()
            if possible_meals_count == 0 and db_for_startup.query(models.Meal).count() > 0:
                print("INFO:     PossibleMeals table is empty, calculating initial possible portions...")
                crud.update_all_possible_meal_portions(db_for_startup)
                print("INFO:     Initial possible portions calculated.")
        finally:
            db_for_startup.close()
    except Exception as e:
        print(f"ERROR:    Error during initial database setup or data creation: {e}")

    # Redis listenerini ishga tushirish
    # Bu asyncio taskini `background_tasks` ga qo'shish mumkin emas, chunki u request scope da ishlaydi.
    # `asyncio.create_task` to'g'ri yechim.
    listener_task = asyncio.create_task(redis_message_listener())
    print("INFO:     Redis Pub/Sub listener task created.")

    yield  # Ilova ishlayotgan payt

    # Shutdown
    print("INFO:     Application shutdown...")
    if listener_task:
        print("INFO:     Cancelling Redis Pub/Sub listener task...")
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            print("INFO:     Redis Pub/Sub listener task cancelled successfully.")
        except Exception as e:
            print(f"ERROR:    Error during Redis listener task cancellation: {e}")
    print("INFO:     Application shutdown complete.")


# --- FastAPI Ilovasini Yaratish ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Bog'cha uchun oshxona va ombor boshqaruvi tizimi.",
    lifespan=lifespan,  # Startup va Shutdown hodisalari uchun
    # docs_url=None, redoc_url=None # Agar API hujjatlarini o'chirmoqchi bo'lsangiz
    # openapi_prefix=settings.API_V1_STR # Agar barcha APIlar bir xil prefixda bo'lsa
)

# --- Statik Fayllar va Shablonlar ---
APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Shablonlar uchun yo'l (templates papkasi app papkasining ichida)
TEMPLATES_DIR = APP_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
# --- CORS (Cross-Origin Resource Sharing) Sozlamalari (Agar frontend boshqa domenda bo'lsa) ---
from fastapi.middleware.cors import CORSMiddleware
origins = [
    "http://localhost:8080", # React/Vue development server uchun
    # Boshqa ruxsat etilgan manbalar
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routerlarini Ulanish ---
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(meals.router)
app.include_router(servings.router)
app.include_router(reports.router)
app.include_router(audit_logs.router)

# --- WebSocket Endpoint ---
@app.websocket(f"{settings.API_V1_STR}/ws")  # Prefix bilan
async def websocket_endpoint(
        websocket: WebSocket,
        token: Optional[str] = Query(None, description="Autentifikatsiya uchun JWT tokeni")
):
    current_user_ws: Optional[models.User] = None
    db_ws: Optional[Session] = None

    if not token:
        print("WARN:     WebSocket connection attempt without token.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token talab qilinadi")
        return

    try:
        db_ws = SessionLocal()
        # Tokenni tekshirish (security.py dagi get_user_from_token dan foydalanish)
        current_user_ws = security.get_user_from_token(db=db_ws, token=token)

        if not current_user_ws:  # Token yaroqsiz yoki foydalanuvchi topilmadi/aktiv emas
            print(f"WARN:     WebSocket authentication failed for token: {token[:20]}...")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Autentifikatsiya xatoligi")
            return

        # Muvaffaqiyatli autentifikatsiyadan so'ng ulanish
        await ws_manager.connect(websocket, current_user_ws.id)

        # Klientga ulanish muvaffaqiyatli ekanligi haqida xabar (ixtiyoriy)
        ack_payload = {"user_id": current_user_ws.id, "message": "WebSocket ulanishi muvaffaqiyatli o'rnatildi."}
        ack_message = WebSocketMessage(type="connection_ack", payload=ack_payload)
        await ws_manager.send_personal_message(ack_message.model_dump(mode='json'), current_user_ws.id)

        while True:  # Klientdan keladigan xabarlarni tinglash
            try:
                data = await websocket.receive_text()
                print(f"DEBUG:    WebSocket received from user {current_user_ws.id}: {data}")
                # Bu yerda klientdan kelgan maxsus komandalarni qayta ishlash mumkin
                if data.lower() == "ping":
                    pong_payload = {"response_to": "ping", "server_time": datetime.now(settings.TIMEZONE).isoformat()}
                    pong_message = WebSocketMessage(type="pong", payload=pong_payload)
                    await ws_manager.send_personal_message(pong_message.model_dump(mode='json'), current_user_ws.id)
                # Boshqa komandalar...
            except WebSocketDisconnect:
                print(f"INFO:     WebSocket disconnected for user {current_user_ws.id} (client closed).")
                break
            except Exception as e_inner:
                print(f"ERROR:    Error processing WebSocket message from user {current_user_ws.id}: {e_inner}")
                # Xatolik haqida klientga xabar yuborish (agar ulanish hali ham aktiv bo'lsa)
                try:
                    error_payload = {"detail": "Xabaringizni qayta ishlashda xatolik yuz berdi."}
                    error_message_ws = WebSocketMessage(type="error_message", payload=error_payload)
                    await ws_manager.send_personal_message(error_message_ws.model_dump(mode='json'), current_user_ws.id)
                except:
                    pass
                break  # Ichki xatolikdan keyin loopdan chiqish

    except WebSocketDisconnect:  # connect() dan oldin uzilish
        print(f"INFO:     WebSocket connection attempt aborted or disconnected early.")
    except Exception as e_outer:
        print(f"ERROR:    Unexpected error in WebSocket connection: {e_outer}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass
    finally:
        if current_user_ws and current_user_ws.id in ws_manager.active_connections:
            ws_manager.disconnect(current_user_ws.id)
        if db_ws:
            db_ws.close()
        print(
            f"INFO:     WebSocket connection cleanup for user {current_user_ws.id if current_user_ws else 'unknown'}.")


# --- Frontend uchun Asosiy Sahifalar (HTMLResponse) ---
async def get_user_from_cookie_for_template(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    token_cookie = request.cookies.get("access_token")
    if not token_cookie or not token_cookie.startswith("Bearer "):
        return None

    token_value = token_cookie.split("Bearer ")[1]
    user = security.get_user_from_token(db=db, token=token_value)  # Aktiv va o'chirilmagan
    return user


@app.get("/", response_class=HTMLResponse, tags=["Frontend"], include_in_schema=False)
async def read_root(request: Request, current_user: Optional[models.User] = Depends(get_user_from_cookie_for_template)):
    if current_user:
        if current_user.role.name == settings.ADMIN_ROLE_NAME:
            return RedirectResponse(url=request.url_for('admin_dashboard'), status_code=status.HTTP_302_FOUND)
        elif current_user.role.name == settings.MANAGER_ROLE_NAME:
            return RedirectResponse(url=request.url_for('manager_dashboard'), status_code=status.HTTP_302_FOUND)
        elif current_user.role.name == settings.CHEF_ROLE_NAME:
            return RedirectResponse(url=request.url_for('chef_dashboard'), status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url=request.url_for('login_page'), status_code=status.HTTP_302_FOUND)


@app.get("/login", response_class=HTMLResponse, name="login_page", tags=["Frontend"], include_in_schema=False)
async def login_page_render(request: Request):  # Nomi o'zgartirildi
    return templates.TemplateResponse("login.html", {"request": request, "settings": settings})


@app.get("/dashboard/admin", response_class=HTMLResponse, name="admin_dashboard", tags=["Frontend"],
         include_in_schema=False)
async def admin_dashboard_render(request: Request,
                                 current_user: Optional[models.User] = Depends(get_user_from_cookie_for_template)):
    if not current_user or current_user.role.name != settings.ADMIN_ROLE_NAME:
        return RedirectResponse(url=f"{request.url_for('login_page')}?error=auth_required&next={request.url.path}",
                                status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("admin_dashboard.html",
                                      {"request": request, "user": current_user, "settings": settings})


@app.get("/dashboard/manager", response_class=HTMLResponse, name="manager_dashboard", tags=["Frontend"],
         include_in_schema=False)
async def manager_dashboard_render(request: Request,
                                   current_user: Optional[models.User] = Depends(get_user_from_cookie_for_template)):
    if not current_user or current_user.role.name not in [settings.MANAGER_ROLE_NAME, settings.ADMIN_ROLE_NAME]:
        return RedirectResponse(url=f"{request.url_for('login_page')}?error=auth_required&next={request.url.path}",
                                status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("manager_dashboard.html",
                                      {"request": request, "user": current_user, "settings": settings})


@app.get("/dashboard/chef", response_class=HTMLResponse, name="chef_dashboard", tags=["Frontend"],
         include_in_schema=False)
async def chef_dashboard_render(request: Request,
                                current_user: Optional[models.User] = Depends(get_user_from_cookie_for_template)):
    if not current_user or current_user.role.name not in [settings.CHEF_ROLE_NAME, settings.ADMIN_ROLE_NAME]:
        return RedirectResponse(url=f"{request.url_for('login_page')}?error=auth_required&next={request.url.path}",
                                status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("chef_dashboard.html",
                                      {"request": request, "user": current_user, "settings": settings})


# --- Boshqa Frontend Sahifalari ---
@app.get("/users-management", response_class=HTMLResponse, name="frontend_users_page", tags=["Frontend"],
         include_in_schema=False)
async def users_management_page_render(request: Request, current_user: Optional[models.User] = Depends(
    get_user_from_cookie_for_template)):
    if not current_user or current_user.role.name != settings.ADMIN_ROLE_NAME:
        return RedirectResponse(url=f"{request.url_for('login_page')}?error=permission_denied&next={request.url.path}",
                                status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("users_management.html",
                                      {"request": request, "user": current_user, "settings": settings})


@app.get("/products", response_class=HTMLResponse, name="frontend_products_page", tags=["Frontend"],
         include_in_schema=False)
async def products_page_render(request: Request,
                               current_user: Optional[models.User] = Depends(get_user_from_cookie_for_template)):
    if not current_user:  # Hamma rollar ko'rishi mumkin (huquqlar JSda ham tekshiriladi)
        return RedirectResponse(url=f"{request.url_for('login_page')}?error=auth_required&next={request.url.path}",
                                status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("products.html", {"request": request, "user": current_user, "settings": settings})


@app.get("/meals", response_class=HTMLResponse, name="frontend_meals_page", tags=["Frontend"], include_in_schema=False)
async def meals_page_render(request: Request,
                            current_user: Optional[models.User] = Depends(get_user_from_cookie_for_template)):
    if not current_user:
        return RedirectResponse(url=f"{request.url_for('login_page')}?error=auth_required&next={request.url.path}",
                                status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("meals.html", {"request": request, "user": current_user, "settings": settings})


@app.get("/servings-log", response_class=HTMLResponse, name="frontend_servings_log_page", tags=["Frontend"],
         include_in_schema=False)
async def servings_log_page_render(request: Request,
                                   current_user: Optional[models.User] = Depends(get_user_from_cookie_for_template)):
    if not current_user:
        return RedirectResponse(url=f"{request.url_for('login_page')}?error=auth_required&next={request.url.path}",
                                status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("servings_log.html",
                                      {"request": request, "user": current_user, "settings": settings})


@app.get("/reports", response_class=HTMLResponse, name="frontend_reports_page", tags=["Frontend"],
         include_in_schema=False)
async def reports_main_page_render(request: Request,
                                   current_user: Optional[models.User] = Depends(get_user_from_cookie_for_template)):
    if not current_user or current_user.role.name not in [settings.ADMIN_ROLE_NAME, settings.MANAGER_ROLE_NAME]:
        return RedirectResponse(url=f"{request.url_for('login_page')}?error=permission_denied&next={request.url.path}",
                                status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("reports_page.html",
                                      {"request": request, "user": current_user, "settings": settings})


# Test uchun WebSocket xabarini yuborish (Redis orqali)
# Bu endpoint Redisga yozadi, Redis listener esa WebSocketga yuboradi
@app.post(
    f"{settings.API_V1_STR}/ws/test-broadcast-redis",
    summary="Test WebSocket xabarini Redis orqali yuborish (Admin)",
    dependencies=[Security(security.get_current_admin_user)],
    response_model=schemas.Msg,
    include_in_schema=settings.APP_ENV == "development"
)
async def test_websocket_broadcast_via_redis(message_payload: Dict[str, Any]):
    """
    (Faqat Admin uchun) WebSocket orqali test xabarini Redis Pub/Sub kanaliga yuborish.
    Redis listener bu xabarni olib, barcha ulangan klientlarga tarqatadi.
    `message_payload` `WebSocketMessage.payload` uchun ma'lumot bo'lishi kerak.
    """
    try:
        test_ws_message = WebSocketMessage(type="test_broadcast", payload=message_payload)
        # Bu yerda message_payloadni WebSocketMessagePayload sxemalaridan biriga moslashtirish kerak bo'lishi mumkin.
        # Hozircha, Dict[str, Any] qilib qoldiramiz.
        redis_client.publish(WS_MESSAGE_CHANNEL, test_ws_message.model_dump_json())
        return {"msg": "Test xabari Redis kanaliga muvaffaqiyatli yuborildi."}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Redisga xabar yuborishda xatolik: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     # Uvicorn ni ishga tushirish uchun:
#     # Loyiha ildiz papkasidan (kindergarten_app): uvicorn app.main:app --reload
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=(settings.APP_ENV == "development"))