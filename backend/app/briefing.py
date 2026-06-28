from datetime import datetime, timezone

from app.rag.schemas import (
    BriefingResponse,
    RecommendationResponse,
    ResearchWithNvidiaContextResponse,
)


MAX_QUOTE_CHARS = 500


def shorten_quote(text: str) -> str:
    cleaned_text = " ".join(text.split())

    cleaned_text = cleaned_text.replace('\\"', '"')
    cleaned_text = cleaned_text.replace("”", '"')
    cleaned_text = cleaned_text.replace("“", '"')

    if len(cleaned_text) <= MAX_QUOTE_CHARS:
        return cleaned_text

    return f"{cleaned_text[:MAX_QUOTE_CHARS].rstrip()}..."


def format_evidences(evidences) -> list[str]:
    lines = []
    seen_ids = set()

    for evidence in evidences:
        if evidence.evidence_id in seen_ids:
            continue

        seen_ids.add(evidence.evidence_id)

        lines.append(
            f'- **{evidence.evidence_id}** — '
            f'[{evidence.source_url}]({evidence.source_url})\n'
            f'  > {shorten_quote(evidence.quote)}'
        )

    return lines


def build_recommendation_section(recommendation, position: int) -> str:
    startup_evidence_lines = format_evidences(
        recommendation.startup_evidences
    )

    nvidia_evidence_lines = format_evidences(
        recommendation.nvidia_evidences
    )

    lines = [
        f"### {position}. {recommendation.technology_name}",
        "",
        f"**Prioridade:** {recommendation.priority}",
        f"**Complexidade:** {recommendation.complexity}",
        "",
        "**Justificativa técnica**",
        recommendation.technical_reason,
        "",
        "**Justificativa de negócio**",
        recommendation.business_reason,
        "",
        "**Próxima ação**",
        recommendation.next_action,
        "",
        "**Evidências da startup**",
        *startup_evidence_lines,
        "",
        "**Evidências NVIDIA**",
        *nvidia_evidence_lines,
        "",
    ]

    return "\n".join(lines)


def build_briefing_markdown(
    research_with_context: ResearchWithNvidiaContextResponse,
    recommendation_response: RecommendationResponse,
) -> str:
    research = research_with_context.research
    classification = research.classification

    lines = [
        f"# Startup Briefing — {research.startup_name}",
        "",
        (
            "Relatório gerado a partir de fontes públicas, "
            "evidências validadas e documentação oficial NVIDIA."
        ),
        "",
        "## 1. Resumo executivo",
        "",
        f"- **Classificação:** {classification.category}",
        f"- **AI-native score:** {classification.ai_native_score}",
        f"- **Wrapper risk score:** {classification.wrapper_risk_score}",
        (
            "- **NVIDIA opportunity score:** "
            f"{classification.nvidia_opportunity_score}"
        ),
        f"- **Fontes públicas coletadas com sucesso:** {research.sources_successful}",
        "",
        "## 2. Perfil público identificado",
        "",
        (
            f"- Evidências de IA no produto: "
            f"{len(research.profile.ai_product)}"
        ),
        (
            f"- Evidências de workflow operacional: "
            f"{len(research.profile.workflow_depth)}"
        ),
        (
            f"- Evidências de dados proprietários ou internos: "
            f"{len(research.profile.proprietary_data)}"
        ),
        (
            f"- Evidências de governança e segurança: "
            f"{len(research.profile.governance_security)}"
        ),
        (
            f"- Evidências de escala e tração: "
            f"{len(research.profile.scale_traction)}"
        ),
        "",
        "## 3. Gaps e limites públicos",
        "",
    ]

    if research.gaps:
        for gap in research.gaps:
            lines.append(
                f"- **{gap.category}:** {gap.message}"
            )
    else:
        lines.append(
            "- Não foram identificados gaps públicos relevantes "
            "pelas regras atuais."
        )

    lines.extend(
        [
            "",
            "## 4. Tecnologias NVIDIA recomendadas",
            "",
        ]
    )

    for position, recommendation in enumerate(
        recommendation_response.recommendations,
        start=1,
    ):
        lines.append(
            build_recommendation_section(
                recommendation=recommendation,
                position=position,
            )
        )

    lines.extend(
        [
            "## 5. Limitações da análise",
            "",
        ]
    )

    if recommendation_response.limitations:
        for limitation in recommendation_response.limitations:
            lines.append(f"- {limitation}")
    else:
        lines.append(
            "- A análise considera somente informações públicas "
            "e evidências recuperadas no momento da consulta."
        )

    lines.extend(
        [
            "",
            "## 6. Próximos passos sugeridos",
            "",
            "1. Validar as hipóteses técnicas com a startup.",
            (
                "2. Priorizar um assessment ou piloto para a "
                "recomendação de maior prioridade."
            ),
            (
                "3. Confirmar requisitos de infraestrutura, dados, "
                "segurança, custo e integração."
            ),
            (
                "4. Registrar novas evidências antes de avançar "
                "para uma recomendação comercial definitiva."
            ),
        ]
    )

    return "\n".join(lines)


def build_briefing(
    research_with_context: ResearchWithNvidiaContextResponse,
    recommendation_response: RecommendationResponse,
) -> BriefingResponse:
    return BriefingResponse(
        startup_name=research_with_context.research.startup_name,
        generated_at=datetime.now(timezone.utc),
        recommendation_count=len(
            recommendation_response.recommendations
        ),
        markdown=build_briefing_markdown(
            research_with_context=research_with_context,
            recommendation_response=recommendation_response,
        ),
    )