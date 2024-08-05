# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""
A centralized API for the query engine.

The API provides a set of functions that external applications can leverage to hook into graphrag
and run a variety of search queries over a knowledge generated by graphrag.

WARNING: This API is under development and may change between releases. Users should
not expect backwards compatibility at this time.
"""

from typing import Any

import pandas as pd

from graphrag.config.models.graph_rag_config import GraphRagConfig
from graphrag.index.progress.types import PrintProgressReporter
from graphrag.model.entity import Entity
from graphrag.vector_stores.lancedb import LanceDBVectorStore
from graphrag.vector_stores.typing import VectorStoreFactory, VectorStoreType

from .factories import get_global_search_engine, get_local_search_engine
from .indexer_adapters import (
    read_indexer_covariates,
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
    read_indexer_text_units,
)
from .input.loaders.dfs import store_entity_semantic_embeddings

reporter = PrintProgressReporter("")


def __get_embedding_description_store(
    entities: list[Entity],
    vector_store_type: str = VectorStoreType.LanceDB,
    config_args: dict | None = None,
):
    """Get the embedding description store."""
    if not config_args:
        config_args = {}

    collection_name = config_args.get(
        "query_collection_name", "entity_description_embeddings"
    )
    config_args.update({"collection_name": collection_name})
    description_embedding_store = VectorStoreFactory.get_vector_store(
        vector_store_type=vector_store_type, kwargs=config_args
    )

    description_embedding_store.connect(**config_args)

    if config_args.get("overwrite", False):
        # this step assumps the embeddings where originally stored in a file rather
        # than a vector database

        # dump embeddings from the entities list to the description_embedding_store
        store_entity_semantic_embeddings(
            entities=entities, vectorstore=description_embedding_store
        )
    else:
        # load description embeddings to an in-memory lancedb vectorstore
        # to connect to a remote db, specify url and port values.
        description_embedding_store = LanceDBVectorStore(
            collection_name=collection_name
        )
        description_embedding_store.connect(
            db_uri=config_args.get("db_uri", "./lancedb")
        )

        # load data from an existing table
        description_embedding_store.document_collection = (
            description_embedding_store.db_connection.open_table(
                description_embedding_store.collection_name
            )
        )

    return description_embedding_store


def global_search(
    config: GraphRagConfig,
    final_nodes: pd.DataFrame,
    final_entities: pd.DataFrame,
    final_community_reports: pd.DataFrame,
    community_level: int,
    response_type: str,
    query: str,
) -> str | dict[str, Any] | list[dict[str, Any]]:
    """Perform a global search.

    Args
    ----
    config (GraphRagConfig): A graphrag configuration (from settings.yaml)
    final_nodes (pd.DataFrame): A DataFrame containing the final nodes (from create_final_nodes.parquet)
    final_entities (pd.DataFrame): A DataFrame containing the final entities (from create_final_entities.parquet)
    final_community_reports (pd.DataFrame): A DataFrame containing the final community reports (from create_final_community_reports.parquet)
    community_level (int): The community level to search at.
    response_type (str): The type of response to return.
    query (str): The user query to search for.

    Returns
    -------
    search response

    Raises
    ------
    TODO: Document any exceptions to expect
    """
    reports = read_indexer_reports(
        final_community_reports, final_nodes, community_level
    )
    entities = read_indexer_entities(final_nodes, final_entities, community_level)
    search_engine = get_global_search_engine(
        config,
        reports=reports,
        entities=entities,
        response_type=response_type,
    )
    result = search_engine.search(query=query)
    reporter.success(f"Global Search Response: {result.response}")
    return result.response


def local_search(
    config: GraphRagConfig,
    final_nodes: pd.DataFrame,
    final_entities: pd.DataFrame,
    final_community_reports: pd.DataFrame,
    final_text_units: pd.DataFrame,
    final_relationships: pd.DataFrame,
    final_covariates: pd.DataFrame | None,
    community_level: int,
    response_type: str,
    query: str,
) -> str | dict[str, Any] | list[dict[str, Any]]:
    """Perform a local search.

    Args
    ----
    config (GraphRagConfig): A graphrag configuration (settings.yaml)
    final_nodes (pd.DataFrame): A DataFrame containing the final nodes (create_final_nodes.parquet)
    final_entities (pd.DataFrame): A DataFrame containing the final entities (create_final_entities.parquet)
    final_community_reports (pd.DataFrame): A DataFrame containing the final community reports (create_final_community_reports.parquet)
    final_text_units (pd.DataFrame): A DataFrame containing the final text units (create_final_text_units.parquet)
    final_relationships (pd.DataFrame): A DataFrame containing the final relationships (create_final_relationships.parquet)
    final_covariates (pd.DataFrame): A DataFrame containing the final covariates (create_final_covariates.parquet)
    community_level (int): The community level to search at.
    response_type (str): The response type to return.
    query (str): The user query to search for.

    Returns
    -------
    search response

    Raises
    ------
    TODO: Document any exceptions to expect
    """
    vector_store_args = (
        config.embeddings.vector_store if config.embeddings.vector_store else {}
    )

    reporter.info(f"Vector Store Args: {vector_store_args}")
    vector_store_type = vector_store_args.get("type", VectorStoreType.LanceDB)

    entities = read_indexer_entities(final_nodes, final_entities, community_level)
    description_embedding_store = __get_embedding_description_store(
        entities=entities,
        vector_store_type=vector_store_type,
        config_args=vector_store_args,
    )
    covariates = (
        read_indexer_covariates(final_covariates)
        if final_covariates is not None
        else []
    )

    search_engine = get_local_search_engine(
        config,
        reports=read_indexer_reports(
            final_community_reports, final_nodes, community_level
        ),
        text_units=read_indexer_text_units(final_text_units),
        entities=entities,
        relationships=read_indexer_relationships(final_relationships),
        covariates={"claims": covariates},
        description_embedding_store=description_embedding_store,
        response_type=response_type,
    )

    result = search_engine.search(query=query)
    reporter.success(f"Local Search Response: {result.response}")
    return result.response
