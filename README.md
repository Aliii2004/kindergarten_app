# Bog'cha Oshxonasi Boshqaruv Tizimi v1.0

Bu FastAPI, SQLAlchemy, Celery va Redis yordamida ishlab chiqilgan bog'cha oshxonasini boshqarish uchun dasturiy yechim. Tizim mahsulotlarni hisobga olish, ovqatlar tarkibini boshqarish, ovqat berishni qayd etish, porsiyalarni hisoblash, batafsil oylik hisobotlarni (shu jumladan, ovqat performansi, ingredient sarfi va mahsulot balansi) generatsiya qilish va real-vaqt bildirishnomalarini olish imkoniyatini beradi.

## Loyiha Tavsifi

Tizim quyidagi asosiy funksiyalarni o'z ichiga oladi:
*   **Mahsulotlar Boshqaruvi:** Mahsulotlarni qo'shish, tahrirlash, o'chirish (soft delete), ombordagi miqdorni kuzatish, minimal qoldiq uchun ogohlantirish, yetkazib berishlarni qayd etish.
*   **Ovqatlar Boshqaruvi:** Ovqatlarni va ularning retseptlarini (ingredientlar, miqdorlari, birliklari) yaratish, tahrirlash, o'chirish.
*   **Ovqat Berish Tizimi:** Berilgan ovqat porsiyalarini qayd etish, ingredientlarni ombordan avtomatik (birliklar konvertatsiyasi bilan) kamaytirish, ingredient yetarli bo'lmasa xatolik chiqarish.
*   **Porsiya Hisoblash:** Har bir ovqatdan mavjud mahsulotlar asosida nechta porsiya tayyorlash mumkinligini dinamik hisoblash va `PossibleMeals` jadvalida saqlash.
*   **Batafsil Oylik Hisobotlar:**
    *   Har bir ovqat uchun oy davomida berilgan porsiyalar va hisobot paytida mumkin bo'lgan porsiyalar.
    *   Har bir ovqat uchun farq foizi va shubhali holat belgisi.
    *   Har bir ovqatdagi har bir ingredientning oy davomidagi umumiy sarfi.
    *   Har bir mahsulot uchun oylik balans (oy boshidagi qoldiq, kirim, nazariy sarf, haqiqiy sarf, nazariy qoldiq, haqiqiy qoldiq, farq va shubhali holat).
    *   Umumiy (oylik) berilgan porsiyalar soni va umumiy shubhali holat belgisi.
*   **Vizualizatsiya uchun Ma'lumotlar:** Ingredientlar iste'moli va mahsulot kelib tushish trendlari uchun API endpointlari.
*   **Foydalanuvchilarni Kuzatish:** Kim qaysi ovqatni berganligi, sana va vaqt bilan qayd qilinadi.
*   **Rolga Asoslangan Kirish:** Admin, Menejer, Oshpaz rollari va ularga mos huquqlar.
*   **Ogohlantirishlar (DB va Real-vaqt):** Minimal mahsulot miqdori, shubhali oylik hisobot (mahsulot balansi yoki ovqat performansi bo'yicha) haqida.
*   **Fon Vazifalari (Celery + Redis):**
    *   Oylik hisobotlarni avtomatik (har oyning boshida) generatsiya qilish.
    *   Porsiya taxminlarini davriy (masalan, har 30 daqiqada) va hodisaga (mahsulot/ovqat o'zgarishi) bog'liq holda qayta hisoblash.
    *   Kam qolgan mahsulotlar haqida ogohlantirishlarni fonda tekshirish.
*   **Real-vaqt Yangilanishlar (WebSocket + Redis Pub/Sub):**
    *   Ombor holati o'zgarganda (mahsulot kelishi, ovqat berilishi).
    *   Yangi ovqat/mahsulot qo'shilganda/o'zgartirilganda/o'chirilganda.
    *   Kam qolgan mahsulotlar yoki shubhali hisobotlar haqida bildirishnomalar.

## Texnologiyalar Steki

*   **Backend:** FastAPI
*   **Frontend (Minimal):** HTML, CSS, JavaScript (Jinja2 shablonizatori bilan), Chart.js
*   **Ma'lumotlar Bazasi:** SQLite (standart sozlamada), PostgreSQL ga o'tish uchun yo'riqnoma mavjud.
*   **Asinxron Vazifa Navbati:** Celery
*   **Xabar Broakeri (Celery & Pub/Sub uchun):** Redis
*   **ORM:** SQLAlchemy (Klassik sintaksis)
*   **Validatsiya:** Pydantic
*   **Autentifikatsiya:** JWT tokenlari (OAuth2PasswordBearer)
*   **Real-vaqt Aloqa:** FastAPI WebSocket, Redis Pub/Sub

## O'rnatish (Installation)

### Talablar:
*   Python 3.9+
*   Pip (Python paket menejeri)
*   Redis Server (ishlab turgan bo'lishi kerak)
*   Git (ixtiyoriy)

### Bosqichlar:

1.  **Loyiha Klonlash/Yuklab Olish:**
    ```bash
    # Agar Git orqali bo'lsa:
    # git clone <repository_url>
    # cd kindergarten_app 
    # Agar ZIP bo'lsa, arxivdan chiqarib, loyiha papkasiga o'ting.
    cd kindergarten_app 
    ```

2.  **Virtual Muhit Yaratish va Aktivlashtirish (Tavsiya Etiladi):**
    ```bash
    python -m venv .venv
    ```
    Windows uchun:
    ```bash
    .venv\Scripts\activate
    ```
    Linux/MacOS uchun:
    ```bash
    source .venv/bin/activate
    ```

3.  **Kerakli Python Kutubxonalarni O'rnatish:**
    ```bash
    pip install -r requirements.txt
    ```
    Agar PostgreSQL ishlatmoqchi bo'lsangiz, `requirements.txt` da `psycopg2-binary` kommentariyadan chiqarilganiga va o'rnatilganiga ishonch hosil qiling.

4.  **Redis Serverini Ishga Tushirish:**
    Redis serveringiz `localhost:6379` manzilida ishlab turganiga ishonch hosil qiling. Agar boshqa manzilda bo'lsa, `.env` faylini moslang. Docker orqali ishga tushirish misoli:
    ```bash
    docker run -d -p 6379:6379 --name my-redis redis
    ```

5.  **`.env` Faylini Sozlash:**
    Loyiha ildizida `.env` faylini yarating (agar mavjud bo'lmasa, `.env.example` dan nusxa oling) va quyidagi asosiy qiymatlarni kiriting:
    ```env
    # Ma'lumotlar bazasi (SQLite standart)
    DATABASE_URL="sqlite:///./kindergarten_app.db" # Fayl nomini o'zgartirishingiz mumkin

    # PostgreSQL uchun (agar ishlatmoqchi bo'lsangiz, SQLite ni kommentga oling)
    # DB_USER="your_pg_user"
    # DB_PASSWORD="your_pg_password"
    # DB_HOST="localhost" # Yoki PostgreSQL server manzili
    # DB_PORT="5432"
    # DB_NAME="kindergarten_pg_db"
    # DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

    SECRET_KEY="DUDA_XAVFSIZ_VA_UNIKAL_MAXFIY_KALITNI_Oylab_TOPING_VA_ALMASHTIRING_!"
    ALGORITHM="HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES=120
    APP_ENV="development" # Yoki "production"
    
    CELERY_BROKER_URL="redis://localhost:6379/0"
    CELERY_RESULT_BACKEND="redis://localhost:6379/0"
    WS_MESSAGE_CHANNEL="ws_kindergarten_notifications"
    TIMEZONE="Asia/Tashkent"
    SUSPICIOUS_DIFFERENCE_PERCENTAGE=15.0 
    ```
    **DIQQAT:** `SECRET_KEY` ni albatta o'zgartiring!

6.  **Chart.js Kutubxonasini Yuklab Olish:**
    `static/js/` papkasiga `chart.min.js` faylini yuklab oling (masalan, cdnjs.com dan).

## Ishga Tushirish

Loyihani ishga tushirish uchun **uchta alohida terminal** kerak bo'ladi (Redis serveri allaqachon ishlab turgan deb hisoblaymiz):

1.  **FastAPI Serveri (Uvicorn):**
    Birinchi terminalda (loyiha ildiz papkasida, virtual muhit aktiv):
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    `--reload` faqat development uchun.

2.  **Celery Worker:**
    Ikkinchi terminalda (loyiha ildiz papkasida, virtual muhit aktiv):
    ```bash
    celery -A app.celery_config.celery_app worker -l info -P solo 
    ```
    (Windows uchun `-P solo` tavsiya etiladi. Linux/MacOS uchun `-P eventlet` yoki `-P gevent` ishlatishingiz mumkin, buning uchun ularni `pip install` qilishingiz kerak).

3.  **Celery Beat (Davriy Vazifalar Uchun):**
    Uchinchi terminalda (loyiha ildiz papkasida, virtual muhit aktiv):
    ```bash
    celery -A app.celery_config.celery_app beat -l info --scheduler celery.beat:PersistentScheduler
    ```

**Ma'lumotlar Bazasini Birinchi Marta Sozlash:**
FastAPI serveri birinchi marta ishga tushganda, agar `.env` da ko'rsatilgan DB fayli mavjud bo'lmasa, u avtomatik ravishda yaratiladi, jadvallar tuziladi va `app/utils.py` dagi `create_initial_data` funksiyasi orqali boshlang'ich ma'lumotlar (standart admin, rollar, birliklar, bildirishnoma turlari) qo'shiladi.
*   **Standart Admin Login:** `admin`
*   **Standart Admin Parol:** `adminpassword` (BIRINCHI KIRISHDAN KEYIN O'ZGARTIRING!)

## Foydalanish

*   Brauzerda `http://127.0.0.1:8000/` manzilini oching. Siz `/login` sahifasiga yo'naltirilishingiz kerak.
*   API hujjatlari uchun `/docs` (Swagger UI) yoki `/redoc` manziliga o'ting.
*   Celery vazifalari monitoringi uchun (agar `flower` o'rnatilgan bo'lsa): `celery -A app.celery_config.celery_app flower --port=5555` buyrug'ini ishga tushirib, `http://localhost:5555` ni oching.

## Loyiha Strukturasi
(Avvalgi javoblarda ko'rsatilgan struktura)

## Keyingi Rivojlanish Yo'nalishlari
*   Frontendni React/Vue.js kabi zamonaviy frameworkda qayta yozish.
*   Batafsil testlar (unit, integration, E2E).
*   Ma'lumotlar bazasi migratsiyalari uchun `Alembic` integratsiyasi.
*   Xavfsizlikni yanada kuchaytirish.
*   Batafsil loglash va monitoring.
*   Ko'p tilli interfeys.
*   `ProductMonthlyBalance` uchun `calculated_consumption_in_month` ni aniqroq hisoblash.
*   `MonthlyReport`dagi umumiy `max_possible_portions` uchun mantiqiyroq hisoblash usulini topish.#   k i n d e r g a r t e n _ a p p  
 