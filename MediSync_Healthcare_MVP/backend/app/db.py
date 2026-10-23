import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

URL = os.getenv("DATABASE_URL", "sqlite:///./medisync.db")
engine = create_engine(URL, connect_args={"check_same_thread": False} if URL.startswith("sqlite") else {})
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase): pass

def get_db():
    db = Session()
    try: yield db
    finally: db.close()
