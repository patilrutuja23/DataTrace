from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import (
    DatasetRecord,
    LineageNode,
    LineageEdge,
)


def get_or_create_node(
    db: Session,
    dataset_id: int,
    node_key: str,
    name: str,
    node_type: str,
    properties: dict,
) -> LineageNode:
    
    node = db.scalar(
        select(LineageNode).where(
            LineageNode.node_key == node_key,
        )
    )
    
    if node is not None: 
        return node
    
    node = LineageNode(
        dataset_id=dataset_id,
        node_key=node_key,
        name=name,
        node_type=node_type,
        properties=properties,
    )
    
    db.add(node)
    db.flush()
    
    return node

def get_or_create_edge(
    db: Session,
    source: LineageNode,
    target: LineageNode,
    relationship: str,
) -> LineageEdge:

    edge = db.scalar(
        select(LineageEdge).where(
            LineageEdge.source_node_id == source.id,
            LineageEdge.target_node_id == target.id,
            LineageEdge.relationship == relationship,
        )
    )

    if edge is not None:
        return edge

    edge = LineageEdge(
        source_node_id=source.id,
        target_node_id=target.id,
        relationship=relationship,
    )

    db.add(edge)
    db.flush()

    return edge


def create_dataset_lineage(
    db: Session,
    dataset: DatasetRecord,
) -> dict:

    dataset_id = dataset.id

    source = get_or_create_node(
        db=db,
        dataset_id=dataset_id,
        node_key=f"dataset:{dataset_id}:source",
        name=dataset.filename,
        node_type="SOURCE",
        properties={
            "filename": dataset.filename,
        },
    )

    pipeline = get_or_create_node(
        db=db,
        dataset_id=dataset_id,
        node_key=f"dataset:{dataset_id}:pipeline",
        name="DataTrace Analysis",
        node_type="PIPELINE",
        properties={
            "steps": [
                "CSV ingestion",
                "Data profiling",
                "Data quality analysis",
            ],
        },
    )

    output = get_or_create_node(
        db=db,
        dataset_id=dataset_id,
        node_key=f"dataset:{dataset_id}:output",
        name=f"Dataset Analysis #{dataset_id}",
        node_type="OUTPUT",
        properties={
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "quality_score": dataset.quality_score,
            "quality_status": dataset.quality_status,
        },
    )

    get_or_create_edge(
        db, source, pipeline, "PROCESSED_BY"
    )

    get_or_create_edge(
        db, pipeline, output, "PRODUCES"
    )

    return get_dataset_lineage(db, dataset_id)


def get_dataset_lineage(
    db: Session,
    dataset_id: int,
) -> dict:

    nodes = db.scalars(
        select(LineageNode)
        .where(LineageNode.dataset_id == dataset_id)
        .order_by(LineageNode.id)
    ).all()

    node_ids = [node.id for node in nodes]

    edges = []

    if node_ids:
        edges = db.scalars(
            select(LineageEdge).where(
                LineageEdge.source_node_id.in_(node_ids),
                LineageEdge.target_node_id.in_(node_ids),
            )
        ).all()

    return {
        "dataset_id": dataset_id,
        "nodes": [
            {
                "id": node.id,
                "name": node.name,
                "type": node.node_type,
                "properties": node.properties,
            }
            for node in nodes
        ],
        "edges": [
            {
                "source": edge.source_node_id,
                "target": edge.target_node_id,
                "relationship": edge.relationship,
            }
            for edge in edges
        ],
    }
