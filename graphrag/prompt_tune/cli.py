# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Command line interface for the fine_tune module."""

from pathlib import Path

from graphrag.index.progress import PrintProgressReporter
from graphrag.prompt_tune.generator import MAX_TOKEN_COUNT
from graphrag.prompt_tune.loader import (
    MIN_CHUNK_SIZE,
    read_config_parameters,
)

from . import api

ENTITY_EXTRACTION_FILENAME = "entity_extraction.txt"
ENTITY_SUMMARIZATION_FILENAME = "summarize_descriptions.txt"
COMMUNITY_SUMMARIZATION_FILENAME = "community_report.txt"


async def prompt_tune(
    config: str,
    root: str,
    domain: str,
    select: str = "random",
    limit: int = 15,
    max_tokens: int = MAX_TOKEN_COUNT,
    chunk_size: int = MIN_CHUNK_SIZE,
    language: str | None = None,
    skip_entity_types: bool = False,
    output: str = "prompts",
    n_subset_max: int = 300,
    k: int = 15,
    min_examples_required: int = 2,
):
    """Prompt tune the model.

    Parameters
    ----------
    - root: The root directory.
    - domain: The domain to map the input documents to.
    - select: The chunk selection method.
    - limit: The limit of chunks to load.
    - max_tokens: The maximum number of tokens to use on entity extraction prompts.
    - chunk_size: The chunk token size to use.
    - skip_entity_types: Skip generating entity types.
    - output: The output folder to store the prompts.
    - n_subset_max: The number of text chunks to embed when using auto selection method.
    - k: The number of documents to select when using auto selection method.
    """
    reporter = PrintProgressReporter("")
    graph_config = read_config_parameters(root, reporter, config)

    prompts = await api.generate_indexing_prompts(
        config=graph_config,
        root=root,
        chunk_size=chunk_size,
        limit=limit,
        select=select,
        domain=domain,
        language=language,
        max_tokens=max_tokens,
        skip_entity_types=skip_entity_types,
        min_examples_required=min_examples_required,
        n_subset_max=n_subset_max,
        k=k,
    )

    output_path = Path(output)
    if output_path:
        reporter.info(f"Writing prompts to {output_path}")
        output_path.mkdir(parents=True, exist_ok=True)
        entity_extraction_prompt_path = output_path / ENTITY_EXTRACTION_FILENAME
        entity_summarization_prompt_path = output_path / ENTITY_SUMMARIZATION_FILENAME
        community_summarization_prompt_path = (
            output_path / COMMUNITY_SUMMARIZATION_FILENAME
        )
        # Write files to output path
        with entity_extraction_prompt_path.open("wb") as file:
            file.write(prompts[0].encode(encoding="utf-8", errors="strict"))
        with entity_summarization_prompt_path.open("wb") as file:
            file.write(prompts[1].encode(encoding="utf-8", errors="strict"))
        with community_summarization_prompt_path.open("wb") as file:
            file.write(prompts[2].encode(encoding="utf-8", errors="strict"))
