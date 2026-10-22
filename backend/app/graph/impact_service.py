
from neo4j import Driver


def get_downstream_impact(
    driver: Driver,
    dataset_id: int,
) -> dict:

    query = """
    MATCH (source:LineageNode {
        dataset_id: $dataset_id,
        node_type: "SOURCE"
    })-[rels:LINEAGE*1..]->(downstream:LineageNode)

    WHERE downstream.dataset_id = $dataset_id

    RETURN DISTINCT
        downstream.node_key AS node_key,
        downstream.name AS name,
        downstream.node_type AS node_type,
        [rel IN rels | rel.relationship] AS path_relationships

    ORDER BY downstream.name
    """

    with driver.session() as session:
        records = list(
            session.run(query, dataset_id=dataset_id)
        )

    impacted_assets = [
        {
            "node_key": record["node_key"],
            "name": record["name"],
            "type": record["node_type"],
            "path_relationships": record["path_relationships"],
        }
        for record in records
    ]

    return {
        "dataset_id": dataset_id,
        "impacted_asset_count": len(impacted_assets),
        "impacted_assets": impacted_assets,
    }
