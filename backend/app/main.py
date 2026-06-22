from datetime import datetime, timezone
from app.discovery import discover_sources
from fastapi import FastAPI, HTTPException

from app.collector import collect_source
from app.evidence import build_evidences
from app.schemas import (
    AnalyzeMultipleRequest,
    AnalyzeMultipleResponse,
    AnalyzeResponse,
    CollectRequest,
    CollectResponse,
    SourceCollectionStatus,
    DiscoverSourcesRequest,
    DiscoverSourcesResponse
)
from app.scoring import calculate_scores


app = FastAPI(
    title="NVIDIA Startup AI Radar",
    version="0.3.0",
    description="API para coletar, analisar e identificar sinais públicos sobre startups."
)


@app.get("/")
async def root():
    return {
        "project": "NVIDIA Startup AI Radar",
        "status": "running",
        "available_endpoints": [
            "POST /collect",
            "POST /analyze",
            "POST /analyze-multiple",
            "POST /discover-sources"
        ]
    }


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post(
    "/discover-sources",
    response_model=DiscoverSourcesResponse
)
async def discover_public_sources(payload: DiscoverSourcesRequest):
    return await discover_sources(payload)


@app.post("/collect", response_model=CollectResponse)
async def collect_public_source(payload: CollectRequest):
    return await collect_source(
        startup_name=payload.startup_name,
        url=str(payload.url)
    )


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_startup(payload: CollectRequest):
    collected = await collect_source(
        startup_name=payload.startup_name,
        url=str(payload.url)
    )

    evidences, ai_signals = build_evidences(
        clean_text=collected.clean_text,
        source_url=collected.source.url
    )

    classification = calculate_scores(
        clean_text=collected.clean_text,
        ai_signals=ai_signals
    )

    return AnalyzeResponse(
        startup_name=collected.startup_name,
        source=collected.source,
        collected_at=collected.collected_at,
        classification=classification,
        evidences=evidences,
        ai_signals_found=ai_signals,
        clean_text_preview=collected.clean_text[:1000]
    )


@app.post("/analyze-multiple", response_model=AnalyzeMultipleResponse)
async def analyze_multiple_sources(payload: AnalyzeMultipleRequest):
    successful_collections = []
    source_statuses = []
    seen_urls = set()

    for url_item in payload.urls:
        url = str(url_item)

        if url in seen_urls:
            continue

        seen_urls.add(url)

        try:
            collected = await collect_source(
                startup_name=payload.startup_name,
                url=url
            )

            successful_collections.append(collected)

            source_statuses.append(
                SourceCollectionStatus(
                    url=collected.source.url,
                    status="COLLECTED",
                    title=collected.source.title,
                    extraction_method=collected.source.extraction_method,
                    text_characters=collected.text_characters,
                    word_count=collected.word_count
                )
            )

        except HTTPException as error:
            source_statuses.append(
                SourceCollectionStatus(
                    url=url,
                    status="FAILED",
                    error=str(error.detail)
                )
            )

    if not successful_collections:
        raise HTTPException(
            status_code=422,
            detail=(
                "Nenhuma das fontes fornecidas pôde ser coletada. "
                "Verifique as URLs ou tente outras fontes públicas."
            )
        )

    all_evidences = []
    all_ai_signals = []

    for collected in successful_collections:
        evidences, ai_signals = build_evidences(
            clean_text=collected.clean_text,
            source_url=collected.source.url
        )

        all_evidences.extend(evidences)
        all_ai_signals.extend(ai_signals)

    unique_ai_signals = sorted(set(all_ai_signals))

    combined_text = "\n\n".join(
        collection.clean_text
        for collection in successful_collections
    )

    classification = calculate_scores(
        clean_text=combined_text,
        ai_signals=unique_ai_signals
    )

    successful_count = len(successful_collections)
    failed_count = len(source_statuses) - successful_count

    return AnalyzeMultipleResponse(
        startup_name=payload.startup_name,
        collected_at=datetime.now(timezone.utc),
        sources=source_statuses,
        sources_successful=successful_count,
        sources_failed=failed_count,
        classification=classification,
        evidences=all_evidences,
        ai_signals_found=unique_ai_signals,
        clean_text_preview=combined_text[:1500]
    )