from datetime import datetime, timezone
import re

import httpx
import trafilatura
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl


app = FastAPI(
    title="NVIDIA Startup AI Radar",
    version="0.2.0",
    description="API para coletar, analisar e identificar sinais públicos sobre startups."
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


class Evidence(BaseModel):
    claim: str
    quote: str
    source_url: str
    status: str
    confidence: float


class ScoreReason(BaseModel):
    criterion: str
    points: int
    reason: str


class ClassificationResult(BaseModel):
    category: str
    ai_native_score: int
    wrapper_risk_score: int
    nvidia_opportunity_score: int
    score_reasons: list[ScoreReason]


class AnalyzeResponse(BaseModel):
    startup_name: str
    source: SourceMetadata
    collected_at: datetime
    classification: ClassificationResult
    evidences: list[Evidence]
    ai_signals_found: list[str]
    clean_text_preview: str


AI_KEYWORDS = [
    "inteligência artificial",
    "inteligencia artificial",
    "ia generativa",
    "generative ai",
    "machine learning",
    "aprendizado de máquina",
    "aprendizado de maquina",
    "modelo de linguagem",
    "llm",
    "automação",
    "automacao",
    "agente de ia",
    "agentes de ia",
    "análise de documentos",
    "analise de documentos",
    "processamento de linguagem natural",
    "visão computacional",
    "visao computacional"
]

WORKFLOW_KEYWORDS = [
    "jurídico",
    "juridico",
    "legal",
    "processos",
    "documentos",
    "operações",
    "operacoes",
    "clientes",
    "empresas",
    "plataforma",
    "workflow",
    "automação",
    "automacao"
]

SCALE_KEYWORDS = [
    "escala",
    "volume",
    "milhares",
    "milhões",
    "milhoes",
    "empresas",
    "clientes",
    "corporativo",
    "enterprise",
    "latência",
    "latencia",
    "performance"
]

NVIDIA_OPPORTUNITY_KEYWORDS = [
    "inteligência artificial",
    "inteligencia artificial",
    "machine learning",
    "llm",
    "modelo",
    "documentos",
    "dados",
    "latência",
    "latencia",
    "escala",
    "governança",
    "governanca",
    "privacidade",
    "automação",
    "automacao"
]


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


async def collect_source(startup_name: str, url: str) -> CollectResponse:
    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/122 Safari/537.36"
                )
            }
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
                "Não foi possível acessar esta fonte pública. "
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
        startup_name=startup_name,
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


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if len(sentence.strip()) >= 30]


def find_sentences_with_keywords(
    text: str,
    keywords: list[str],
    limit: int = 5
) -> list[tuple[str, str]]:
    found = []
    used_sentences = set()

    for sentence in split_sentences(text):
        sentence_lower = sentence.lower()

        for keyword in keywords:
            if keyword in sentence_lower and sentence not in used_sentences:
                found.append((keyword, sentence))
                used_sentences.add(sentence)
                break

        if len(found) >= limit:
            break

    return found


def build_evidences(clean_text: str, source_url: str) -> tuple[list[Evidence], list[str]]:
    matches = find_sentences_with_keywords(clean_text, AI_KEYWORDS)

    evidences = []
    signals = []

    for keyword, sentence in matches:
        signals.append(keyword)

        evidences.append(
            Evidence(
                claim=f"Foram encontrados sinais públicos relacionados a '{keyword}'.",
                quote=sentence[:500],
                source_url=source_url,
                status="OBSERVADA",
                confidence=0.85
            )
        )

    return evidences, sorted(set(signals))


def calculate_scores(
    clean_text: str,
    ai_signals: list[str]
) -> ClassificationResult:
    text_lower = clean_text.lower()
    reasons = []

    ai_native_score = 0
    wrapper_risk_score = 50
    nvidia_opportunity_score = 0

    workflow_matches = [
        keyword for keyword in WORKFLOW_KEYWORDS
        if keyword in text_lower
    ]

    scale_matches = [
        keyword for keyword in SCALE_KEYWORDS
        if keyword in text_lower
    ]

    nvidia_matches = [
        keyword for keyword in NVIDIA_OPPORTUNITY_KEYWORDS
        if keyword in text_lower
    ]

    if ai_signals:
        ai_native_score += 35
        wrapper_risk_score -= 15

        reasons.append(
            ScoreReason(
                criterion="IA no produto",
                points=35,
                reason="Foram encontrados sinais públicos de IA no conteúdo analisado."
            )
        )

    if len(ai_signals) >= 3:
        ai_native_score += 15
        wrapper_risk_score -= 10

        reasons.append(
            ScoreReason(
                criterion="Diversidade de sinais de IA",
                points=15,
                reason="A fonte apresenta mais de um tipo de sinal relacionado a IA."
            )
        )

    if workflow_matches:
        ai_native_score += 20
        wrapper_risk_score -= 10

        reasons.append(
            ScoreReason(
                criterion="Profundidade de workflow",
                points=20,
                reason="Foram encontrados sinais de integração com processos, documentos ou operações."
            )
        )

    if scale_matches:
        ai_native_score += 10

        reasons.append(
            ScoreReason(
                criterion="Produção e escala",
                points=10,
                reason="A fonte apresenta sinais públicos de clientes, escala, volume ou operação corporativa."
            )
        )

    if nvidia_matches:
        nvidia_opportunity_score += min(40, len(nvidia_matches) * 5)

        reasons.append(
            ScoreReason(
                criterion="Aderência a tecnologias NVIDIA",
                points=min(40, len(nvidia_matches) * 5),
                reason="Foram encontrados sinais de dados, modelos, escala, IA, documentos ou automação."
            )
        )

    if ai_signals:
        nvidia_opportunity_score += 25

        reasons.append(
            ScoreReason(
                criterion="Maturidade de IA",
                points=25,
                reason="A startup apresenta sinais públicos de uso de IA no produto ou operação."
            )
        )

    if workflow_matches:
        nvidia_opportunity_score += 15

        reasons.append(
            ScoreReason(
                criterion="Dor de negócio",
                points=15,
                reason="O conteúdo sugere uma aplicação de IA conectada a um workflow real."
            )
        )

    ai_native_score = min(ai_native_score, 100)
    wrapper_risk_score = max(min(wrapper_risk_score, 100), 0)
    nvidia_opportunity_score = min(nvidia_opportunity_score, 100)

    if ai_native_score >= 50:
        category = "AI-native"
    elif ai_native_score >= 20:
        category = "AI-enabled"
    else:
        category = "Non-AI ou evidência insuficiente"

    return ClassificationResult(
        category=category,
        ai_native_score=ai_native_score,
        wrapper_risk_score=wrapper_risk_score,
        nvidia_opportunity_score=nvidia_opportunity_score,
        score_reasons=reasons
    )


@app.get("/")
async def root():
    return {
        "project": "NVIDIA Startup AI Radar",
        "status": "running",
        "available_endpoints": [
            "POST /collect",
            "POST /analyze"
        ]
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


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