from datetime import datetime, timezone
import re

import httpx
import trafilatura
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl


app = FastAPI(
    title="NVIDIA Startup AI Radar",
    version="0.1.0",
    description="API para coletar e limpar fontes públicas sobre startups."
)


class CollectRequest(BaseModel):
    startup_name: str = Field(min_length=2, max_length=120)
    url: HttpUrl


class SourceMetadata(BaseModel):
    url: str
    title: str | None
    extraction_method: str


class CollectResponse(BaseModel):
    startup_name: str
    source: SourceMetadata
    collected_at: datetime
    text_characters: int
    word_count: int
    clean_text: str


def get_page_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    return None


def extract_clean_text(html: str, url: str) -> tuple[str, str]:
    extracted_text = trafilatura.extract(
        html,
        url=url,
        include_links=False,
        include_tables=True,
        favor_precision=True
    )

    if extracted_text:
        clean_text = extracted_text
        extraction_method = "trafilatura"
    else:
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        clean_text = soup.get_text(" ", strip=True)
        extraction_method = "beautifulsoup_fallback"

    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    if not clean_text:
        raise ValueError("Não foi possível extrair texto útil desta página.")

    return clean_text[:15000], extraction_method


@app.get("/")
async def root():
    return {
        "project": "NVIDIA Startup AI Radar",
        "status": "running",
        "next_step": "Use POST /collect para coletar uma fonte pública."
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/collect", response_model=CollectResponse)
async def collect_public_source(payload: CollectRequest):
    url = str(payload.url)

    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "NVIDIA-Startup-AI-Radar/0.1"}
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=f"A fonte respondeu com erro HTTP {error.response.status_code}."
        ) from error

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Não foi possível acessar esta fonte pública. "
                f"Motivo: {type(error).__name__} - {str(error)}"
            )
        ) from error

    try:
        clean_text, extraction_method = extract_clean_text(
            html=response.text,
            url=url
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        ) from error

    return CollectResponse(
        startup_name=payload.startup_name,
        source=SourceMetadata(
            url=url,
            title=get_page_title(response.text),
            extraction_method=extraction_method
        ),
        collected_at=datetime.now(timezone.utc),
        text_characters=len(clean_text),
        word_count=len(clean_text.split()),
        clean_text=clean_text
    )