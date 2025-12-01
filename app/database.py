from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# 1. Create the Database Engine
# pool_pre_ping=True ensures we don't get disconnected from Supabase unexpectedly
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# 2. Create the Session Local class
# Each request will create a new session from this factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Base class for Models
Base = declarative_base()

# 4. Dependency to get DB session in endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()