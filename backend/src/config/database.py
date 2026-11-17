import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,DeclarativeBase
from .settings import DATABASE_URL
engine=create_engine(DATABASE_URL,pool_pre_ping=True,
    pool_size=int(os.getenv('DATABASE_POOL_SIZE','10')),
    max_overflow=int(os.getenv('DATABASE_POOL_OVERFLOW','20')),
    pool_timeout=int(os.getenv('DATABASE_POOL_TIMEOUT','15')))
Session=sessionmaker(engine,expire_on_commit=False)
class Base(DeclarativeBase): pass
def get_db():
    with Session() as db: yield db
