# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# Ma'lumotlar bazasi URL manzilini config.py dan olamiz
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # SQLite uchun `check_same_thread` ni o'rnatamiz
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    **engine_args
    # echo=True # Agar SQL so'rovlarini konsolda ko'rishni xohlasangiz (faqat developmentda)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency: Har bir so'rov uchun DB sessiyasini olish
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()