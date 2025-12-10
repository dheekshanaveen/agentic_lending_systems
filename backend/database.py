from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# SQLite database in a local file "lending.db" in project root
DATABASE_URL = "sqlite:///./lending.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # needed for SQLite + FastAPI
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
