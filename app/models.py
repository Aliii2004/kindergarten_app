# app/models.py

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime

from app.config import settings
from app.database import Base 

# --- Role ---
class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    users = relationship("User", back_populates="role")

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"

# --- User ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True) # Soft delete uchun

    role = relationship("Role", back_populates="users")
    created_products = relationship("Product", back_populates="created_by_user", foreign_keys="Product.created_by")
    received_deliveries = relationship("ProductDelivery", back_populates="received_by_user", foreign_keys="ProductDelivery.received_by")
    created_meals = relationship("Meal", back_populates="created_by_user", foreign_keys="Meal.created_by")
    served_meals = relationship("MealServing", back_populates="served_by_user", foreign_keys="MealServing.served_by")
    notifications = relationship("Notification", back_populates="user", foreign_keys="Notification.user_id")
    generated_reports = relationship("MonthlyReport", back_populates="generated_by_user", foreign_keys="MonthlyReport.generated_by")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

# --- Unit ---
class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    short_name = Column(String(10), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    products = relationship("Product", back_populates="unit")
    meal_ingredients_as_portion_unit = relationship("MealIngredient", back_populates="unit", foreign_keys="MealIngredient.unit_id") # Agar bir nechta FK bo'lsa

    def __repr__(self):
        return f"<Unit(id={self.id}, name='{self.name}')>"

# --- Product ---
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    min_quantity = Column(Float, nullable=False) # Minimal miqdor (ogohlantirish uchun)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True) # Kim yaratgani
    deleted_at = Column(DateTime, nullable=True) # Soft delete

    unit = relationship("Unit", back_populates="products")
    created_by_user = relationship("User", back_populates="created_products")
    deliveries = relationship("ProductDelivery", back_populates="product", cascade="all, delete-orphan")
    meal_ingredients = relationship("MealIngredient", back_populates="product", cascade="all, delete-orphan")
    serving_details = relationship("ServingDetail", back_populates="product")
    limiting_for_meals = relationship("PossibleMeals", back_populates="limiting_product",
                                      foreign_keys="PossibleMeals.limiting_product_id")
    ingredient_usage_details = relationship("ReportDetail",
                                            back_populates="product_for_ingredient_detail")  # Type hint olib tashlandi
    monthly_balances_of_product = relationship("ProductMonthlyBalance", back_populates="product_in_balance",
                                               cascade="all, delete-orphan")


def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}')>"


# --- ProductDelivery ---
class ProductDelivery(Base):
    __tablename__ = "product_deliveries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    delivery_date = Column(DateTime, nullable=False, default=datetime.now)
    supplier = Column(String(100), nullable=True)
    price = Column(Float, nullable=True) # Yetkazib berilgan partiya narxi
    received_by = Column(Integer, ForeignKey("users.id"), nullable=True) # Kim qabul qilgani
    created_at = Column(DateTime, default=datetime.now)

    product = relationship("Product", back_populates="deliveries")
    received_by_user = relationship("User", back_populates="received_deliveries")

    def __repr__(self):
        return f"<ProductDelivery(id={self.id}, product_id={self.product_id}, quantity={self.quantity})>"

# --- Meal ---
class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False, unique=True, index=True) # Ovqat nomi unikal bo'lishi mumkin
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True) # Ovqat menyuda faolmi?
    deleted_at = Column(DateTime, nullable=True) # Soft delete

    created_by_user = relationship("User", back_populates="created_meals")
    ingredients = relationship("MealIngredient", back_populates="meal", cascade="all, delete-orphan")
    servings = relationship("MealServing", back_populates="meal", cascade="all, delete-orphan")
    possible_meals_entry = relationship("PossibleMeals", back_populates="meal", uselist=False,
                                        cascade="all, delete-orphan")

    performance_summary_in_reports = relationship("ReportMealPerformance",
                                                  back_populates="meal_in_performance_summary")  # Type hint olib tashlandi
    ingredient_details_of_meal = relationship("ReportDetail", back_populates="meal_for_ingredient_detail")

    def __repr__(self):
        return f"<Meal(id={self.id}, name='{self.name}')>"



# --- MealIngredient ---
class MealIngredient(Base):
    __tablename__ = "meal_ingredients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meal_id = Column(Integer, ForeignKey("meals.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_per_portion = Column(Float, nullable=False) # 1 porsiya uchun kerakli miqdor
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False) # Shu ingredient qaysi birlikda o'lchanadi
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    meal = relationship("Meal", back_populates="ingredients")
    product = relationship("Product", back_populates="meal_ingredients")
    unit = relationship("Unit", back_populates="meal_ingredients_as_portion_unit")

    def __repr__(self):
        return f"<MealIngredient(meal_id={self.meal_id}, product_id={self.product_id})>"

# --- MealServing ---
class MealServing(Base):
    __tablename__ = "meal_servings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meal_id = Column(Integer, ForeignKey("meals.id"), nullable=False)
    portions_served = Column(Integer, nullable=False)
    served_at = Column(DateTime, default=datetime.now, nullable=False)
    served_by = Column(Integer, ForeignKey("users.id"), nullable=True) # Kim bergani
    notes = Column(Text, nullable=True) # Qo'shimcha izohlar

    meal = relationship("Meal", back_populates="servings")
    served_by_user = relationship("User", back_populates="served_meals")
    serving_details = relationship("ServingDetail", back_populates="serving", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MealServing(id={self.id}, meal_id={self.meal_id}, portions={self.portions_served})>"

# --- ServingDetail ---
class ServingDetail(Base): # Ovqat berilganda qaysi ingredientdan qancha ishlatilgani
    __tablename__ = "serving_details"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    serving_id = Column(Integer, ForeignKey("meal_servings.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_used = Column(Float, nullable=False) # Shu serving uchun ishlatilgan miqdor
    created_at = Column(DateTime, default=datetime.now)

    serving = relationship("MealServing", back_populates="serving_details")
    product = relationship("Product", back_populates="serving_details")

    def __repr__(self):
        return f"<ServingDetail(serving_id={self.serving_id}, product_id={self.product_id})>"

# --- NotificationType ---
class NotificationType(Base):
    __tablename__ = "notification_types"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False) # Masalan, "low_stock", "suspicious_report"
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    notifications = relationship("Notification", back_populates="notification_type")

    def __repr__(self):
        return f"<NotificationType(name='{self.name}')>"

# --- Notification ---
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message = Column(Text, nullable=False)
    notification_type_id = Column(Integer, ForeignKey("notification_types.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Agar shaxsiy bo'lsa, None - umumiy
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now, index=True)

    notification_type = relationship("NotificationType", back_populates="notifications")
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, type_id={self.notification_type_id}, read={self.is_read})>"

# --- MonthlyReport ---
class MonthlyReport(Base):
    __tablename__ = "monthly_reports"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_month = Column(Date, nullable=False, unique=True)
    generated_at = Column(DateTime, default=datetime.now)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=True)


    total_portions_served_overall = Column(Integer, nullable=True)
    is_overall_suspicious = Column(Boolean, default=False, nullable=True)

    difference_percentage = Column(Float, nullable=True)

    generated_by_user = relationship("User", back_populates="generated_reports")  # Optional["User"] edi
    meal_performance_summaries = relationship("ReportMealPerformance", back_populates="report",
                                              cascade="all, delete-orphan")
    all_ingredient_usage_details = relationship("ReportDetail", back_populates="report", cascade="all, delete-orphan")
    product_balance_summaries = relationship("ProductMonthlyBalance", back_populates="report",
                                             cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MonthlyReport(month='{self.report_month}', suspicious={self.is_overall_suspicious})>"


# --- ReportMealPerformance Modeli (YANGI) ---
# Bu har bir ovqat uchun oylik porsiya ko'rsatkichlarini saqlaydi
class ReportMealPerformance(Base):
    __tablename__ = "report_meal_performance"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("monthly_reports.id"), nullable=False)
    meal_id = Column(Integer, ForeignKey("meals.id"), nullable=False)

    portions_served_this_meal = Column(Integer, nullable=False, default=0)  # Shu ovqatdan shu oyda berilgan
    possible_portions_at_report_time = Column(Integer, nullable=False, default=0)  # Hisobot paytida mumkin bo'lgan

    # Har bir ovqat uchun farq foizi va shubhalilikni DBda saqlashimiz mumkin
    difference_percentage = Column(Float, nullable=True)
    is_suspicious = Column(Boolean, default=False, nullable=True)

    report = relationship("MonthlyReport", back_populates="meal_performance_summaries")
    meal_in_performance_summary = relationship("Meal", back_populates="performance_summary_in_reports")

class ReportDetail(Base): # Ingredient sarfi uchun (bu klass bir marta e'lon qilingan)
    __tablename__ = "report_ingredient_details" # JADVAL NOMINI ANIQ QILAMIZ
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("monthly_reports.id"), nullable=False)
    meal_id = Column(Integer, ForeignKey("meals.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    total_quantity_used = Column(Float, nullable=False)

    report = relationship("MonthlyReport", back_populates="all_ingredient_usage_details")
    meal_for_ingredient_detail = relationship("Meal", back_populates="ingredient_details_of_meal")
    product_for_ingredient_detail = relationship("Product", back_populates="ingredient_usage_details")

    def __repr__(self):
        return f"<ReportDetail(r_id={self.report_id}, m_id={self.meal_id}, p_id={self.product_id}, usage={self.total_quantity_used})>"

# --- PossibleMeals ---
class PossibleMeals(Base): # Har bir ovqatdan hozirda qancha porsiya tayyorlash mumkinligi
    __tablename__ = "possible_meals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True) # O'zining IDsi
    meal_id = Column(Integer, ForeignKey("meals.id"), nullable=False, unique=True) # Bir ovqat uchun bitta yozuv
    possible_portions = Column(Integer, nullable=False)
    limiting_product_id = Column(Integer, ForeignKey("products.id"), nullable=True) # Qaysi mahsulot cheklayotgani
    calculated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    meal = relationship("Meal", back_populates="possible_meals_entry", uselist=False)
    limiting_product = relationship("Product", back_populates="limiting_for_meals")

    def __repr__(self):
        return f"<PossibleMeals(meal_id={self.meal_id}, portions={self.possible_portions})>"


# --- ProductMonthlyBalance Modeli (YANGI) ---
class ProductMonthlyBalance(Base):
    __tablename__ = "product_monthly_balances"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("monthly_reports.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    initial_stock = Column(Float)
    total_received = Column(Float, default=0.0)
    total_available = Column(Float)
    calculated_consumption = Column(Float, default=0.0)  # Retsept bo'yicha nazariy sarf
    actual_consumption = Column(Float, default=0.0)  # ServingDetail dan olingan haqiqiy sarf
    theoretical_ending_stock = Column(Float)
    actual_ending_stock = Column(Float)  # Oy oxiridagi haqiqiy qoldiq
    discrepancy = Column(Float)
    is_balance_suspicious = Column(Boolean, default=False)

    report = relationship("MonthlyReport", back_populates="product_balance_summaries")
    product_in_balance = relationship("Product", back_populates="monthly_balances_of_product")





# app/models.py
# ... (boshqa importlar)
from sqlalchemy.dialects.postgresql import JSONB # Agar PostgreSQL ishlatsangiz, JSONB yaxshiroq
from sqlalchemy import JSON

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Amalni bajargan user, None bo'lishi mumkin (masalan, tizim tomonidan)
    username = Column(String, nullable=True) # Qulaylik uchun user nomini ham saqlash
    action = Column(String(100), nullable=False, index=True) # Masalan, "CREATE_PRODUCT", "USER_LOGIN"
    target_entity_type = Column(String(50), nullable=True) # Masalan, "Product", "User", "Meal"
    target_entity_id = Column(Integer, nullable=True, index=True) # Ta'sir qilingan obyekt IDsi
    status = Column(String(20), nullable=False, default="SUCCESS") # "SUCCESS", "FAILURE", "ATTEMPT"
    details = Column(Text, nullable=True) # Umumiy matnli ma'lumot
    changes_before = Column(JSONB if settings.DATABASE_URL.startswith("postgresql") else JSON, nullable=True) # O'zgarishdan oldingi holat (JSON)
    changes_after = Column(JSONB if settings.DATABASE_URL.startswith("postgresql") else JSON, nullable=True) # O'zgarishdan keyingi holat (JSON)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)

    user = relationship("User") # Audit yozuviga bog'langan foydalanuvchi

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user='{self.username}', action='{self.action}')>"


