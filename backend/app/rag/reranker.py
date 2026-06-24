from fastapi import HTTPException
from typing import Any
from app.rag.schemas import HybridCandidate


RERANKER_MODEL_NAME = (
    "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
)

_reranker_model: Any | None = None


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
    candidates: list[HybridCandidate],
    top_k: int,
) -> list[HybridCandidate]:
    if not candidates:
        return []

    reranker = get_reranker_model()

    pairs = [
        (query, candidate.text)
        for candidate in candidates
    ]

    scores = reranker.predict(
        pairs,
        show_progress_bar=False,
    )

    reranked = [
        candidate.model_copy(
            update={
                "rerank_score": float(score),
            }
        )
        for candidate, score in zip(candidates, scores)
    ]

    return sorted(
        reranked,
        key=lambda candidate: (
            candidate.rerank_score or 0.0
        ),
        reverse=True,
    )[:top_k]