import re

from app.schemas import Evidence


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


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)

    return [
        sentence.strip()
        for sentence in sentences
        if len(sentence.strip()) >= 30
    ]


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


def build_evidences(
    clean_text: str,
    source_url: str
) -> tuple[list[Evidence], list[str]]:
    matches = find_sentences_with_keywords(clean_text, AI_KEYWORDS)

    evidences = []
    signals = []

    for keyword, sentence in matches:
        signals.append(keyword)

        evidences.append(
            Evidence(
                claim=(
                    "Foram encontrados sinais públicos "
                    f"relacionados a '{keyword}'."
                ),
                quote=sentence[:500],
                source_url=source_url,
                status="OBSERVADA",
                confidence=0.85
            )
        )

    return evidences, sorted(set(signals))