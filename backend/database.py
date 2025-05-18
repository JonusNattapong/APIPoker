from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DB_USER = os.getenv('POSTGRES_USER', 'poker')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'pokerpass')
DB_HOST = os.getenv('POSTGRES_HOST', 'db')
DB_NAME = os.getenv('POSTGRES_DB', 'pokerdb')
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
