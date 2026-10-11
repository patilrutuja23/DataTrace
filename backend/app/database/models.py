from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy import ForeignKey, UniqueConstraint



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
    
    
class LineageNode(Base):
    __tablename__ = "lineage_nodes"
    
    __table_args__ = (
        UniqueConstraint("node_key", name="uq_lineage_nodes_node_key"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(
        Integer,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    node_key = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    node_type = Column(String(50), nullable=False)
    properties = Column(JSON, nullable=False, default=dict)
    



class LineageEdge(Base):
    __tablename__ = "lineage_edges"
    
    __table_args__ = (
        UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "relationship",
            name="up_lineage_edge",
        ),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    
    source_node_id = Column(
        Integer,
        ForeignKey("lineage_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    target_node_id = Column(
        Integer,
        ForeignKey("lineage_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    relationship = Column(String(50), nullable=False)