from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy import JSON


from app.database.connection import Base

class DatasetRecord(Base):
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    
    row_count = Column(Integer, nullable=False)
    column_count = Column(Integer, nullable=False)
    
    profile = Column(JSON, nullable=False)
    quality = Column(JSON, nullable=False)
    
    quality_score = Column(Float, nullable=False)
    quality_status = Column(String(20), nullable=False)
    
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable = False,
    )
    