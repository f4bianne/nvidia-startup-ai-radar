from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class NvidiaSource(BaseModel):
    technology_id: str
    technology_name: str
    title: str
    source_url: HttpUrl
    source_type: str
    tags: list[str]
    enabled: bool = True


class NvidiaChunk(BaseModel):
    chunk_id: str
    technology_id: str
    technology_name: str
    title: str
    text: str
    source_url: str
    source_type: str
    tags: list[str]
    chunk_index: int
    word_count: int
    collected_at: datetime


class NvidiaIngestStatus(BaseModel):
    technology_id: str
    technology_name: str
    source_url: str
    status: str
    chunks_created: int = 0
    text_characters: int = 0
    error: str | None = None


class NvidiaIngestResponse(BaseModel):
    collected_at: datetime
    sources_processed: int
    sources_successful: int
    sources_failed: int
    chunks_created: int
    embedding_model: str
    statuses: list[NvidiaIngestStatus]


class NvidiaRagQueryRequest(BaseModel):
    query: str = Field(min_length=10, max_length=1500)
    top_k: int = Field(default=3, ge=1, le=8)


class HybridCandidate(BaseModel):
    chunk_id: str
    technology_id: str
    technology_name: str
    title: str
    text: str
    source_url: str
    source_type: str
    tags: list[str]
    lexical_score: float
    semantic_score: float
    fused_score: float
    rerank_score: float | None = None


class NvidiaRagResult(BaseModel):
    technology_id: str
    technology_name: str
    title: str
    text: str
    source_url: str
    tags: list[str]
    lexical_score: float
    semantic_score: float
    fused_score: float
    rerank_score: float


class NvidiaRagQueryResponse(BaseModel):
    query: str
    pipeline: str
    retrieved_at: datetime
    results: list[NvidiaRagResult]