# app/schemas.py
from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import List, Optional, Any, Union, Dict
from datetime import datetime, date

# --- Asosiy sozlamalar uchun Pydantic V2 ConfigDict ---
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# --- Role Schemas ---
class RoleBase(BaseSchema):
    name: str = Field(min_length=3, max_length=50, description="Rol nomi (admin, menejer, oshpaz)")
    description: Optional[str] = Field(None, max_length=255, description="Rol tavsifi")

class RoleCreate(RoleBase):
    pass

class RoleUpdate(RoleBase): # To'liq update, hamma maydonlar bo'lishi kerak
    name: Optional[str] = Field(None, min_length=3, max_length=50)
    description: Optional[str] = Field(None, max_length=255)

class Role(RoleBase):
    id: int
    created_at: datetime


# --- Unit Schemas ---
class UnitBase(BaseSchema):
    name: str = Field(min_length=1, max_length=50, description="O'lchov birligi nomi (gramm, kilogramm)")
    short_name: str = Field(min_length=1, max_length=10, description="Qisqa nomi (gr, kg)")

class UnitCreate(UnitBase):
    pass

class UnitUpdate(UnitBase):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    short_name: Optional[str] = Field(None, min_length=1, max_length=10)

class Unit(UnitBase):
    id: int
    created_at: datetime


# --- User Schemas ---
class UserBase(BaseSchema):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$", description="Foydalanuvchi logini")
    full_name: str = Field(min_length=3, max_length=100, description="Foydalanuvchining to'liq ismi")

class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=100, description="Foydalanuvchi paroli")
    role_id: int = Field(description="Foydalanuvchi roli IDsi")

class UserUpdate(BaseSchema): # Faqat o'zgarishi mumkin bo'lgan maydonlar uchun (PATCH)
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: Optional[str] = Field(None, min_length=3, max_length=100)
    password: Optional[str] = Field(None, min_length=6, max_length=100, description="Yangi parol (agar o'zgartirilsa)")
    role_id: Optional[int] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: int
    role: Role # Role ma'lumotini ham ko'rsatish uchun
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime

class UserInDB(User):
    password_hash: str

# --- Token Schemas ---
class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user_info: Optional[User] = None # Frontend uchun foydalanuvchi ma'lumotlarini ham yuborish

class TokenPayload(BaseSchema): # Token ichidagi ma'lumotlar (sub, scopes, exp)
    sub: Optional[str] = None # Username (subject)
    scopes: List[str]
    exp: Optional[int] = None


# --- Product Schemas ---
# class ProductBase(BaseSchema):
#     name: str = Field(min_length=2, max_length=100, description="Mahsulot nomi")
#     unit_id: int = Field(description="Mahsulot o'lchov birligi IDsi")
#     min_quantity: float = Field(gt=0, description="Ombordagi minimal miqdor (ogohlantirish uchun)")

# app/schemas.py
class ProductBase(BaseSchema):
    name: str = Field(min_length=2, max_length=100, description="Mahsulot nomi")
    unit_id: int = Field(description="Mahsulot o'lchov birligi IDsi") # <--- Mana bu kerak
    min_quantity: float = Field(gt=0, description="Ombordagi minimal miqdor (ogohlantirish uchun)") # <--- Mana bu ham kerak

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseSchema): # Faqat o'zgarishi mumkin bo'lgan maydonlar
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    unit_id: Optional[int] = None
    min_quantity: Optional[float] = Field(None, gt=0)

class Product(ProductBase):
    id: int
    unit: Unit # Birlik ma'lumotlari
    created_at: datetime
    updated_at: Optional[datetime] = None
    # created_by: Optional[int] = None # Yoki User sxemasi
    created_by_user: Optional[UserBase] = None # Agar foydalanuvchi ma'lumotini ham ko'rsatish kerak bo'lsa

class ProductWithQuantity(Product): # Ombordagi miqdori bilan
    current_quantity: float = Field(description="Mahsulotning joriy ombordagi miqdori")


# --- ProductDelivery Schemas ---
class ProductDeliveryBase(BaseSchema):
    product_id: int
    quantity: float = Field(gt=0, description="Yetkazib berilgan mahsulot miqdori")
    delivery_date: datetime = Field(default_factory=datetime.now, description="Yetkazib berilgan sana va vaqt")
    supplier: Optional[str] = Field(None, max_length=100, description="Yetkazib beruvchi nomi")
    price: Optional[float] = Field(None, ge=0, description="Partiya narxi (ixtiyoriy)")



class ProductDeliveryCreate(ProductDeliveryBase):
    pass

# class ProductDelivery(ProductDeliveryBase):
#     id: int
#     # product: Product # Agar to'liq mahsulot ma'lumoti kerak bo'lsa, og'ir bo'lishi mumkin
#     product_name: Optional[str] = None # Optimallashtirish uchun
#     received_by: Optional[int] = None # Yoki User sxemasi
#     # received_by_user_full_name: Optional[str] = None # Optimallashtirish uchun
#     created_at: datetime

class ProductDelivery(ProductDeliveryBase): # Javob uchun sxema
    id: int
    # product: ProductBase # To'liq product o'rniga kerakli maydonlarni qo'shamiz
    product_name: Optional[str] = Field(None, validation_alias='product.name') # model_validate uchun
    product_unit_short_name: Optional[str] = Field(None, validation_alias='product.unit.short_name')
    # received_by: Optional[int] = None # UserBase ni qaytarish yaxshiroq
    received_by_user: Optional[UserBase] = None # Agar UserBase kerak bo'lsa
    created_at: datetime


# --- MealIngredient Schemas (Ovqat tarkibi uchun) ---
class MealIngredientBase(BaseSchema):
    product_id: int
    quantity_per_portion: float = Field(gt=0, description="1 porsiya uchun kerakli miqdor")
    unit_id: int # Ingredient qaysi birlikda o'lchanadi

class MealIngredientCreate(MealIngredientBase):
    pass

class MealIngredient(MealIngredientBase): # Bu Meal sxemasi ichida ishlatiladi
    id: int # MealIngredient ning o'zining ID si
    product: ProductBase # Faqat asosiy mahsulot ma'lumotlari
    unit: UnitBase # Faqat asosiy birlik ma'lumotlari


# --- Meal Schemas (Ovqatlar) ---
class MealBase(BaseSchema):
    name: str = Field(min_length=3, max_length=150, description="Ovqat nomi")
    description: Optional[str] = Field(None, description="Ovqat haqida qisqacha tavsif")
    is_active: bool = Field(True, description="Ovqat menyuda faolmi?")

class MealCreate(MealBase):
    ingredients: List[MealIngredientCreate]

class MealUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    ingredients: Optional[List[MealIngredientCreate]] = Field(None, description="Ingredientlarni to'liq yangilash uchun")

class Meal(MealBase): # Javob uchun sxema
    id: int
    ingredients: List[MealIngredient] # To'liq ingredient ma'lumotlari bilan
    # created_by: Optional[int] = None
    created_by_user: Optional[UserBase] = None # Agar UserBase kerak bo'lsa
    created_at: datetime
    updated_at: Optional[datetime] = None


# --- MealServing Schemas (Ovqat berish) ---
class MealServingBase(BaseSchema):
    meal_id: int
    portions_served: int = Field(gt=0, description="Berilgan porsiyalar soni")
    notes: Optional[str] = Field(None, description="Ovqat berish haqida izohlar")

class MealServingCreate(MealServingBase):
    pass # served_by va served_at avtomatik

class ServingDetailBase(BaseSchema): # Bu MealServingWithDetails ichida ishlatiladi
    product_id: int
    quantity_used: float

class ServingDetail(ServingDetailBase):
    id: int
    product: ProductBase # Qaysi mahsulot ishlatilgani (asosiy ma'lumotlar)
    created_at: datetime

class MealServing(MealServingBase): # Javob uchun asosiy sxema
    id: int
    served_at: datetime
    meal: MealBase # To'liq meal o'rniga MealBase
    served_by_user: Optional[UserBase] = None

class MealServingWithDetails(MealServing):
    serving_details: List[ServingDetail]


# --- NotificationType Schemas ---
class NotificationTypeBase(BaseSchema):
    name: str = Field(min_length=3, max_length=50, description="Bildirishnoma turi nomi (low_stock)")
    description: Optional[str] = Field(None, description="Bildirishnoma turi tavsifi")

class NotificationTypeCreate(NotificationTypeBase):
    pass

class NotificationType(NotificationTypeBase):
    id: int


# --- Notification Schemas ---
class NotificationBase(BaseSchema):
    message: str = Field(description="Bildirishnoma matni")
    notification_type_id: int
    user_id: Optional[int] = Field(None, description="Agar shaxsiy bo'lsa, foydalanuvchi IDsi")
    # related_item_id: Optional[int] = None # Qaysi obyektga tegishli (masalan, product_id)
    # related_item_type: Optional[str] = None # Obyekt turi ("product", "report")

class NotificationCreate(NotificationBase):
    pass

class Notification(NotificationBase): # Javob uchun sxema
    id: int
    notification_type: NotificationType # To'liq type ma'lumoti
    user: Optional[UserBase] = None # Agar user_id bo'lsa va user ma'lumotlari kerak bo'lsa
    is_read: bool
    created_at: datetime



class ReportDetailBase(BaseSchema): # DBga yozish uchun asosiy maydonlar (Create uchun ishlatiladi)
    meal_id: int
    product_id: int
    total_quantity_used: float


class ReportDetailCreate(ReportDetailBase):
    pass

class ReportDetail(ReportDetailBase):
    id: int
    meal: Optional[MealBase] = None
    product: Optional[ProductBase] = None

# class MonthlyReportBase(BaseSchema):
#     report_month: date # YYYY-MM-01 formatida
#     total_portions_served: int
#     max_possible_portions: int # Umumiy hisoblangan
#     difference_percentage: float
#     is_suspicious: bool

# 4. Asosiy Oylik Hisobot Sxemasi (Yangilangan)
# class MonthlyReportBase(BaseSchema): # Bu sxema DBga yozish uchun ishlatilmaydi (faqat o'qish)
#     report_month: date
#     # Umumiy ko'rsatkichlar DBdan olinadi
#     total_portions_served_overall: Optional[int] = None
#     is_overall_suspicious: Optional[bool] = None
#     # Boshqa umumiy maydonlar (max_possible_overall, diff_perc_overall) agar DBda saqlansa yoki @computed_field bo'lsa

class MonthlyReportBase(BaseSchema): # O'qish uchun asosiy sxema
    report_month: date
    total_portions_served_overall: Optional[int] = None
    is_overall_suspicious: Optional[bool] = None
    generated_at: datetime # Buni ham qo'shamiz
    generated_by: Optional[int] = None # Yoki UserBase

class MonthlyReportCreate(MonthlyReportBase): # Avtomatik generatsiyada ishlatiladi
    pass # generated_by avtomatik





# --- PossibleMeals Schemas (Tayyorlash mumkin bo'lgan porsiyalar) ---
class PossibleMealsBase(BaseSchema): # Bu asosan ichki hisob-kitoblar uchun
    meal_id: int
    possible_portions: int
    limiting_product_id: Optional[int] = None

# PossibleMealsCreate kerak emas, chunki bu avtomatik hisoblanadi

class PossibleMeals(PossibleMealsBase):
    id: int # Bu jadvalning o'zining ID si
    meal: MealBase # Ovqatning asosiy ma'lumotlari
    limiting_product: Optional[ProductBase] = None # Cheklovchi mahsulot (asosiy ma'lumotlar)
    calculated_at: datetime


# --- Vizualizatsiya uchun maxsus sxemalar ---
class IngredientConsumptionDataPoint(BaseSchema):
    product_name: str
    total_consumed: float
    unit_short_name: str

class ProductDeliveryDataPoint(BaseSchema):
    delivery_date: date # Yoki datetime, agar vaqt ham muhim bo'lsa
    product_name: str
    total_delivered: float
    unit_short_name: str

class MealPortionInfo(BaseSchema): # Oshpaz paneli uchun
    meal_id: int
    meal_name: str
    possible_portions: int
    limiting_ingredient_name: Optional[str] = None
    limiting_ingredient_unit: Optional[str] = None




# --- WebSocket uchun xabar sxemasi ---
class LowStockAlertPayload(BaseModel): # BaseSchema emas, chunki from_attributes kerak emas
    product_id: int
    product_name: str
    current_quantity: float
    min_quantity: float
    unit: str
    message: str
    notification_id: Optional[int] = None

class SuspiciousReportAlertPayload(BaseModel):
    report_id: int
    report_month: str # YYYY-MM
    difference_percentage: float # Modelda bu maydon yo'q, MonthlyReport.is_overall_suspicious bor
    message: str

class StockItemReceivedPayload(BaseModel):
    product_id: int
    product_name: str
    change_in_quantity: float
    new_total_quantity: float
    unit: str
    delivery_id: int
    message: str

class ProductDefinitionUpdatedPayload(BaseModel):
    product_id: int
    product_name: str
    min_quantity: float
    current_quantity: float
    unit: str
    message: str

class NewMealServedPayload(BaseModel):
    serving_id: int
    meal_id: int
    meal_name: str
    portions_served: int
    served_at: str # ISO format
    served_by_user_name: str # Yoki UserBase
    message: str
    # consumed_ingredients: Optional[List[Dict[str, Any]]] = None # Agar kerak bo'lsa

class GeneralNotificationPayload(BaseModel): # Umumiy bildirishnomalar uchun
    title: str
    body: str
    severity: str = "info" # "info", "warning", "error"
    notification_id: Optional[int] = None

class PossiblePortionsRecalculatedPayload(BaseModel):
    message: str
    recalculated_at: str # ISO format

class MealDefinitionUpdatedPayload(BaseModel): # Qo'shildi
    meal_id: int
    meal_name: str
    message: str

class ProductDeletedPayload(BaseModel): # Qo'shildi
    product_id: int
    product_name: str
    message: str

class MealDeletedPayload(BaseModel): # Qo'shildi
    meal_id: int
    meal_name: str
    message: str


class WebSocketMessage(BaseModel):
    type: str = Field(description="Xabar turi")
    payload: Union[
        LowStockAlertPayload,
        SuspiciousReportAlertPayload,
        StockItemReceivedPayload,
        ProductDefinitionUpdatedPayload,
        NewMealServedPayload,
        MealDefinitionUpdatedPayload, # Qo'shildi
        ProductDeletedPayload, # Qo'shildi
        MealDeletedPayload, # Qo'shildi
        PossiblePortionsRecalculatedPayload,
        GeneralNotificationPayload,
        Dict[str, Any] # Umumiy holat uchun
    ]
    timestamp: datetime = Field(default_factory=datetime.now)


class Msg(BaseSchema): # BaseSchema dan meros olish
    msg: str


# 1. Har bir ovqatning oylik performansi uchun
class ReportMealPerformanceBase(BaseSchema):
    meal_id: int
    portions_served_this_meal: int
    possible_portions_at_report_time: int
    difference_percentage: Optional[float] = None
    is_suspicious: Optional[bool] = None


class ReportMealPerformance(ReportMealPerformanceBase):
    id: int
    meal: Optional[MealBase] = None  # Ovqat nomini va boshqa ma'lumotlarni ko'rsatish uchun



# 2. Har bir ingredientning oylik sarfi uchun (ReportDetail -> ReportIngredientUsageDetail)
class ReportIngredientUsageDetailBase(BaseSchema): # Sxema nomini aniqlashtirdim
    meal_id: int
    product_id: int
    total_quantity_used: float

class ReportIngredientUsageDetail(ReportIngredientUsageDetailBase):
    id: int
    meal_for_ingredient_detail: Optional[MealBase] = Field(None, validation_alias='meal_for_ingredient_detail')
    product_for_ingredient_detail: Optional[ProductBase] = Field(None, validation_alias='product_for_ingredient_detail')

# 3. Har bir mahsulotning oylik balansi uchun (ProductMonthlyBalance)
class ProductMonthlyBalanceBase(BaseSchema):
    product_id: int
    initial_stock: float
    total_received: float
    total_available: float # Bu maydon modelda hisoblanadi (initial_stock + total_received)
    calculated_consumption: float
    actual_consumption: float
    theoretical_ending_stock: float
    actual_ending_stock: float
    discrepancy: float
    is_balance_suspicious: bool


class ProductMonthlyBalance(ProductMonthlyBalanceBase):
    id: int
    product_in_balance: Optional[ProductBase] = Field(None, validation_alias='product_in_balance')

    @computed_field(return_type=Optional[float])
    @property
    def discrepancy_percentage(self) -> Optional[float]:
        denominator = self.initial_stock + self.total_received
        if abs(denominator) > 1e-9: # 0 ga yaqin songa bo'lishni oldini olish
            return round((self.discrepancy / denominator) * 100, 2)
        if abs(self.discrepancy) > 1e-9: # Agar denominator 0 bo'lsa, lekin farq bo'lsa
             return 100.0 if self.discrepancy > 0 else -100.0 # Yoki boshqa maxsus qiymat
        return 0.0 # Agar ikkalasi ham 0 bo'lsa

# Asosiy Oylik Hisobot Sxemasi
class MonthlyReportBase(BaseSchema):
    report_month: date
    total_portions_served_overall: Optional[int] = None
    is_overall_suspicious: Optional[bool] = None
    generated_at: datetime
    # generated_by: Optional[int] = None # UserBase orqali qaytaramiz


class MonthlyReport(MonthlyReportBase): # Bu GET /reports/monthly/{report_id} uchun javob sxemasi
    id: int
    generated_by_user: Optional[UserBase] = Field(None, validation_alias='generated_by_user')
    meal_performance_summaries: List[ReportMealPerformance] # Model relationship nomi bilan bir xil
    all_ingredient_usage_details: List[ReportIngredientUsageDetail] # Model relationship nomi bilan bir xil
    product_balance_summaries: List[ProductMonthlyBalance] # Model relationship nomi bilan bir xil


class MonthlyReportWithDetails(MonthlyReport):
    details: List[ReportDetail]









class AuditLogBase(BaseSchema):
    action: str
    target_entity_type: Optional[str] = None
    target_entity_id: Optional[int] = None
    status: str = "SUCCESS"
    details: Optional[str] = None
    changes_before: Optional[Dict[str, Any]] = None
    changes_after: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class AuditLogCreate(AuditLogBase):
    user_id: Optional[int] = None # Bu avtomatik olinadi
    username: Optional[str] = None # Bu ham

class AuditLog(AuditLogBase):
    id: int
    timestamp: datetime
    user_id: Optional[int] = None
    username: Optional[str] = None
    user: Optional[UserBase] = None # Agar user ma'lumotlarini ham ko'rsatish kerak bo'lsa
