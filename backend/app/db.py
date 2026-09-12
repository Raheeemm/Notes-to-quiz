import os
from datetime import datetime,timezone

from dotenv import load_dotenv
from sqlalchemy import Column,DateTime,Integer,String,Text,create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

engine=create_engine(DATABASE_URL,pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)
Base = declarative_base()

class NoteSet(Base):
    __tablename__ = "note_sets"

    id = Column(Integer, primary_key=True,index=True)
    user_id = Column(String(64),nullable=False,index=True)
    source_text = Column(Text,nullable=False)
    summary = Column(Text,nullable=False)
    questions_json = Column(Text,nullable=False)
    created_at = Column(DateTime(timezone=True),default=datetime.now(timezone.utc))

def init_db():
    Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()