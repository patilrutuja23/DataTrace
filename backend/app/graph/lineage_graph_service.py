
import json

from neo4j import Driver
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import LineageNode, LineageEdge


def sync_lineage_to_neo4j(
    db: Session,
    driver: Driver,
    dataset_id: int,
) -> dict:
    nodes = db.scalars(
        select(LineageNode)
        .where(LineageNode.dataset_id == dataset_id)
        .order_by(LineageNode.id)
    ).all()

    if not nodes:
        return {
            "dataset_id": dataset_id,
            "nodes_synced": 0,
            "edges_synced": 0,
            "message": "No PostgreSQL lineage exists for this dataset.",
        }

    node_ids = [node.id for node in nodes]

    edges = db.scalars(
        select(LineageEdge).where(
            LineageEdge.source_node_id.in_(node_ids),
            LineageEdge.target_node_id.in_(node_ids),
        )
    ).all()

    node_by_id = {node.id: node for node in nodes}

    with driver.session() as session:
        session.run("""
            CREATE CONSTRAINT lineage_node_key IF NOT EXISTS
            FOR (n:LineageNode)
            REQUIRE n.node_key IS UNIQUE
        """).consume()

        for node in nodes:
            session.run("""
                MERGE (n:LineageNode {node_key: $node_key})
                SET n.name = $name,
                    n.node_type = $node_type,
                    n.dataset_id = $dataset_id,
                    n.properties_json = $properties_json
            """,
                node_key=node.node_key,
                name=node.name,
                node_type=node.node_type,
                dataset_id=node.dataset_id,
                properties_json=json.dumps(node.properties or {}),
            ).consume()

        for edge in edges:
            source = node_by_id[edge.source_node_id]
            target = node_by_id[edge.target_node_id]

            session.run("""
                MATCH (s:LineageNode {node_key: $source_key})
                MATCH (t:LineageNode {node_key: $target_key})
                MERGE (s)-[r:LINEAGE {
                    relationship: $relationship
                }]->(t)
                SET r.dataset_id = $dataset_id
            """,
                source_key=source.node_key,
                target_key=target.node_key,
                relationship=edge.relationship,
                dataset_id=dataset_id,
            ).consume()

    return {
        "dataset_id": dataset_id,
        "nodes_synced": len(nodes),
        "edges_synced": len(edges),
        "message": "Lineage synchronized to Neo4j successfully.",
    }


def get_lineage_from_neo4j(
    driver: Driver,
    dataset_id: int,
) -> dict:
    with driver.session() as session:
        result = session.run("""
            MATCH (n:LineageNode {dataset_id: $dataset_id})
            OPTIONAL MATCH (n)-[r:LINEAGE]->(target:LineageNode)
            WHERE target IS NULL OR target.dataset_id = $dataset_id
            RETURN
                n.node_key AS node_key,
                n.name AS name,
                n.node_type AS node_type,
                n.properties_json AS properties_json,
                collect(
                    CASE WHEN r IS NULL THEN null ELSE {
                        source_key: n.node_key,
                        target_key: target.node_key,
                        relationship: r.relationship
                    } END
                ) AS relationships
            ORDER BY n.node_key
        """, dataset_id=dataset_id)

        nodes = []
        edges = []
        seen_edges = set()

        for record in result:
            nodes.append({
                "node_key": record["node_key"],
                "name": record["name"],
                "type": record["node_type"],
                "properties": json.loads(
                    record["properties_json"] or "{}"
                ),
            })

            for edge in record["relationships"]:
                if edge is None:
                    continue

                key = (
                    edge["source_key"],
                    edge["target_key"],
                    edge["relationship"],
                )

                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append({
                        "source_key": key[0],
                        "target_key": key[1],
                        "relationship": key[2],
                    })

    return {
        "dataset_id": dataset_id,
        "nodes": nodes,
        "edges": edges,
    }
