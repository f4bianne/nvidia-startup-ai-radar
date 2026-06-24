from fastapi import HTTPException
import re
import unicodedata
from typing import Any
from app.rag.schemas import HybridCandidate


RERANKER_MODEL_NAME = (
    "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
)

_reranker_model: Any | None = None

MAX_DOCUMENT_CHARS = 1800

MODEL_WEIGHT = 0.65
METADATA_WEIGHT = 0.35


CONCEPT_KEYWORDS = {
    "llm": {
        "llm",
        "llms",
        "language",
        "linguagem",
        "token",
        "tokens",
    },
    "performance": {
        "latencia",
        "latency",
        "throughput",
        "inferencia",
        "inference",
        "batching",
        "otimizacao",
        "optimization",
    },
    "production": {
        "producao",
        "production",
        "deploy",
        "deployment",
        "serving",
        "microservices",
        "microservicos",
    },
    "governance": {
        "guardrails",
        "governanca",
        "governance",
        "seguranca",
        "safety",
        "validacao",
        "validation",
        "jailbreak",
        "pii",
    },
    "retrieval": {
        "rag",
        "retrieval",
        "embedding",
        "embeddings",
        "reranking",
        "documentos",
        "documents",
    },
}


CONCEPT_WEIGHTS = {
    "llm": 1.5,
    "performance": 2.0,
    "production": 1.2,
    "governance": 2.0,
    "retrieval": 2.0,
}

def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize(
        "NFD",
        text.casefold(),
    )

    without_accents = "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    )

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        without_accents,
    ).strip()


def get_concepts(text: str) -> set[str]:
    words = set(normalize_text(text).split())

    return {
        concept
        for concept, keywords in CONCEPT_KEYWORDS.items()
        if words & keywords
    }


def build_candidate_context(candidate: Any) -> str:
    document_preview = candidate.text[:MAX_DOCUMENT_CHARS]

    return (
        f"Technology: {candidate.technology_name}\n"
        f"Tags: {', '.join(candidate.tags)}\n"
        f"Documentation: {document_preview}"
    )


def calculate_metadata_alignment(
    query: str,
    candidate: Any,
) -> float:
    query_concepts = get_concepts(query)

    if not query_concepts:
        return 0.0

    candidate_concepts = get_concepts(
        build_candidate_context(candidate)
    )

    matched_concepts = query_concepts & candidate_concepts

    matched_weight = sum(
        CONCEPT_WEIGHTS[concept]
        for concept in matched_concepts
    )

    total_weight = sum(
        CONCEPT_WEIGHTS[concept]
        for concept in query_concepts
    )

    return matched_weight / total_weight

def get_reranker_model() -> Any:
    global _reranker_model

    if _reranker_model is None:
        try:
            import torch
            from sentence_transformers import CrossEncoder

            _reranker_model = CrossEncoder(
                RERANKER_MODEL_NAME,
                activation_fn=torch.nn.Sigmoid(),
            )

        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Não foi possível carregar o modelo de reranking: "
                    f"{error}"
                ),
            )

    return _reranker_model

def rerank_candidates(
    query: str,
    candidates: list[Any],
    top_k: int,
) -> list[Any]:
    if not candidates:
        return []

    reranker = get_reranker_model()

    pairs = [
        (
            query,
            build_candidate_context(candidate),
        )
        for candidate in candidates
    ]

    model_scores = reranker.predict(
        pairs,
        show_progress_bar=False,
    )

    reranked = []

    for candidate, model_score in zip(
        candidates,
        model_scores,
    ):
        metadata_score = calculate_metadata_alignment(
            query=query,
            candidate=candidate,
        )

        final_score = (
            MODEL_WEIGHT * float(model_score)
            + METADATA_WEIGHT * metadata_score
        )

        reranked.append(
            candidate.model_copy(
                update={
                    "rerank_score": final_score,
                }
            )
        )

    return sorted(
        reranked,
        key=lambda candidate: (
            candidate.rerank_score or 0.0
        ),
        reverse=True,
    )[:top_k]