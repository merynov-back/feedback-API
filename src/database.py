from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings

engine = create_engine(settings.BASE_URL)
SessionLocal = sessionmaker(auticommit=False, autoflush=False, bind=engine)