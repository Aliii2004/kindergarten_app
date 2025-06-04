# app/websockets/connection_manager.py
from typing import List, Dict, Optional, Union
from fastapi import WebSocket, WebSocketException # status ni ws_status deb nomladim


# schemas.py dan WebSocketMessage sxemasini import qilishimiz kerak
# Lekin circular import bo'lmasligi uchun, bu yerda alohida sxema yaratish yoki
# schemas.py ni bu fayldan oldin qayta ishlash kerak.
# Eng yaxshisi, WebSocketMessage sxemasi schemas.py da qolsin va uni bu yerda ishlatmaylik,
# balki main.py da xabarni tayyorlab, keyin bu manager orqali yuboraylik.
# Yoki, faqat type va payload ni qabul qiladigan generic message yuborish.

# Keling, bu yerda WebSocketMessage ga bog'liqlikni kamaytiramiz va
# xabarlarni dict ko'rinishida qabul qilamiz. Xabarni formatlash main.py yoki tasklarda bo'ladi.

class ConnectionManager:
    def __init__(self):
        # Har bir user_id uchun WebSocket ulanishini saqlaymiz
        # Bir foydalanuvchi bir nechta qurilmadan yoki tabdan ulanishi mumkin,
        # shuning uchun List[WebSocket] ishlatish yaxshiroq bo'lishi mumkin.
        # Hozircha, har bir user_id uchun bitta oxirgi ulanishni saqlaymiz.
        self.active_connections: Dict[int, WebSocket] = {} # user_id: WebSocket

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        # Agar shu user_id bilan eski ulanish bo'lsa, uni yopish mumkin (ixtiyoriy)
        # if user_id in self.active_connections:
        #     old_ws = self.active_connections[user_id]
        #     try:
        #         await old_ws.close(code=ws_status.WS_1001_GOING_AWAY, reason="Yangi ulanish o'rnatildi")
        #     except Exception:
        #         pass # Yopishda xatolik bo'lsa e'tibor bermaslik
        self.active_connections[user_id] = websocket
        print(f"INFO:     User {user_id} connected via WebSocket from: {websocket.client.host}:{websocket.client.port}")

    def disconnect(self, user_id: int, websocket: Optional[WebSocket] = None):
        # Agar websocket parametri berilsa va u saqlangan ulanish bilan bir xil bo'lsa, o'chirish
        # Bu bir foydalanuvchining bir nechta ulanishini boshqarish uchun foydali bo'lishi mumkin
        if websocket and user_id in self.active_connections and self.active_connections[user_id] == websocket:
            del self.active_connections[user_id]
            print(f"INFO:     User {user_id} (specific websocket) disconnected from WebSocket.")
        elif not websocket and user_id in self.active_connections: # Agar faqat user_id berilsa
            del self.active_connections[user_id]
            print(f"INFO:     User {user_id} (any websocket) disconnected from WebSocket.")
        # Agar ulanish topilmasa, hech narsa qilmaymiz

    async def send_personal_message(self, message_data: Union[str, dict, list], user_id: int):
        """
        Xabarni JSON formatida (agar dict yoki list bo'lsa) yoki matn sifatida yuboradi.
        """
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                if isinstance(message_data, str):
                    await websocket.send_text(message_data)
                else: # dict, list, Pydantic model (model_dump qilingan)
                    await websocket.send_json(message_data)
                # print(f"DEBUG:    Sent personal WS message to user {user_id}: {str(message_data)[:100]}...")
            except WebSocketException as e:
                print(f"WARN:     Could not send personal WS message to user {user_id} (WebSocketException: {e.reason}). Disconnecting.")
                self.disconnect(user_id, websocket)
            except RuntimeError as e: # Masalan, "Unexpected ASGI message..."
                print(f"WARN:     Runtime error sending WS message to user {user_id}: {e}. Disconnecting.")
                self.disconnect(user_id, websocket)
            except Exception as e:
                print(f"ERROR:    Unexpected error sending WS message to user {user_id}: {e}. Disconnecting.")
                self.disconnect(user_id, websocket)


    async def broadcast_to_specific_users(self, message_data: Union[str, dict, list], user_ids: List[int]):
        """
        Xabarni berilgan user_id ro'yxatidagi foydalanuvchilarga yuboradi.
        """
        for user_id in user_ids:
            # send_personal_message o'zi xatoliklarni qayta ishlaydi va disconnect qiladi
            await self.send_personal_message(message_data, user_id)

    async def broadcast_to_all_active(self, message_data: Union[str, dict, list]):
        """
        Xabarni barcha aktiv ulangan foydalanuvchilarga yuboradi.
        """
        # active_connections dict ni iterate qilganda o'zgartirmaslik uchun .copy() yoki list() ishlatish
        # print(f"DEBUG:    Broadcasting WS message to all {len(self.active_connections)} active clients: {str(message_data)[:100]}...")
        if not self.active_connections: # Agar hech kim ulanmagan bo'lsa
            return

        user_ids_to_broadcast = list(self.active_connections.keys()) # Joriy ulanganlar ro'yxati
        for user_id in user_ids_to_broadcast:
            # send_personal_message o'zi xatoliklarni qayta ishlaydi
            await self.send_personal_message(message_data, user_id)

# Global ConnectionManager obyektini yaratamiz
manager = ConnectionManager()