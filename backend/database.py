from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- 1. Database URL ---
# DATABASE_URL = "sqlite:///./sql_app.db"
DATABASE_URL = "postgresql+psycopg2://neondb_owner:npg_7twsE2cOuHSr@ep-mute-brook-a4aw9d40-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# --- 2. SQLAlchemy Engine ---
engine = create_engine(
    DATABASE_URL, 
    # This is required for SQLite
    # connect_args={"check_same_thread": False} 
)

# --- 3. Database Session ---
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 4. Base Class ---
# 'Base' is defined here for models.py to import
Base = declarative_base()

# --- 5. get_db Dependency ---
def get_db():
    """
    Dependency to get a database session for each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()