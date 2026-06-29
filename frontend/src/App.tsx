import { useEffect, useState, type FormEvent } from "react";
import {
  createFullAnalysis,
  getAnalysis,
  getStartupAnalyses,
  getStartups,
  type FullAnalysisResponse,
  type StartupAnalysesResponse,
  type StartupHistoryItem,
} from "./api";
import "./App.css";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type PipelineStep = {
  title: string;
  description: string;
};

const PIPELINE_STEPS: PipelineStep[] = [
  {
    title: "Planejando pesquisa",
    description: "Definindo consultas públicas sobre a startup.",
  },
  {
    title: "Coletando fontes",
    description: "Buscando páginas oficiais, notícias e fontes públicas.",
  },
  {
    title: "Validando evidências",
    description: "Extraindo sinais, classificando evidências e identificando gaps.",
  },
  {
    title: "Consultando NVIDIA RAG",
    description: "Buscando documentação técnica oficial da NVIDIA.",
  },
  {
    title: "Gerando recomendações",
    description: "Relacionando evidências da startup com tecnologias NVIDIA.",
  },
  {
    title: "Gerando briefing",
    description: "Montando o relatório final e salvando a análise no histórico.",
  },
];

type ResultTab =
  | "summary"
  | "recommendations"
  | "evidences"
  | "briefing";

function formatDate(value: string | null) {
  if (!value) {
    return "Data não disponível";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function downloadBriefing(markdown: string, startupName: string) {
  const file = new Blob([markdown], {
    type: "text/markdown;charset=utf-8",
  });

  const url = URL.createObjectURL(file);
  const link = document.createElement("a");

  link.href = url;
  link.download = `briefing-${startupName
    .toLowerCase()
    .replace(/\s+/g, "-")}.md`;

  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}

function App() {
  const [startups, setStartups] = useState<StartupHistoryItem[]>(
    [],
  );

  const [pipelineStep, setPipelineStep] = useState(0);

  const [selectedAnalysis, setSelectedAnalysis] =
    useState<FullAnalysisResponse | null>(null);

  const [activeResultTab, setActiveResultTab] =
    useState<ResultTab>("summary");

  const [selectedStartupHistory, setSelectedStartupHistory] =
    useState<StartupAnalysesResponse | null>(null);

  const [startupName, setStartupName] = useState("");
  const [sector, setSector] = useState("");

  const [showNewAnalysisForm, setShowNewAnalysisForm] =
    useState(false);

  const [loadingHistory, setLoadingHistory] = useState(true);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [loadingStartupHistory, setLoadingStartupHistory] =
    useState(false);

  const [loadingSavedAnalysis, setLoadingSavedAnalysis] =
    useState(false);

  const [error, setError] = useState("");

  async function loadHistory() {
    try {
      setError("");
      setLoadingHistory(true);

      const savedStartups = await getStartups();
      setStartups(savedStartups);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Ocorreu um erro inesperado.",
      );
    } finally {
      setLoadingHistory(false);
    }
  }

  useEffect(() => {
    void loadHistory();
  }, []);

  async function handleCreateAnalysis(event: FormEvent) {
    event.preventDefault();

    if (!startupName.trim()) {
      setError("Informe o nome da startup.");
      return;
    }

    let stageTimer: ReturnType<typeof window.setInterval> | undefined;

    try {
      setError("");
      setLoadingAnalysis(true);
      setSelectedAnalysis(null);
      setSelectedStartupHistory(null);
      setPipelineStep(0);

      stageTimer = window.setInterval(() => {
        setPipelineStep((currentStep) =>
          Math.min(
            currentStep + 1,
            PIPELINE_STEPS.length - 1,
          ),
        );
      }, 3500);

      const analysis = await createFullAnalysis({
        startup_name: startupName.trim(),
        sector: sector.trim() || undefined,
        max_sources: 4,
      });

      setPipelineStep(PIPELINE_STEPS.length - 1);
      setSelectedAnalysis(analysis);
      setShowNewAnalysisForm(false);
      setStartupName("");
      setSector("");

      await loadHistory();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Ocorreu um erro inesperado.",
      );
    } finally {
      if (stageTimer) {
        window.clearInterval(stageTimer);
      }

      setLoadingAnalysis(false);
    }
  }

  async function handleOpenStartupHistory(
    startup: StartupHistoryItem,
  ) {
    try {
      setError("");
      setLoadingStartupHistory(true);
      setSelectedAnalysis(null);
      setShowNewAnalysisForm(false);

      const history = await getStartupAnalyses(startup.startup_id);

      setSelectedStartupHistory(history);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Ocorreu um erro inesperado.",
      );
    } finally {
      setLoadingStartupHistory(false);
    }
  }

  async function handleOpenSavedAnalysis(analysisId: string) {
    try {
      setError("");
      setLoadingSavedAnalysis(true);

      const analysis = await getAnalysis(analysisId);

      setSelectedAnalysis(analysis);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Ocorreu um erro inesperado.",
      );
    } finally {
      setLoadingSavedAnalysis(false);
    }
  }

  return (
    <main className="page">
      <header className="hero">
        <p className="eyebrow">NVIDIA Startup AI Radar</p>

        <h1>
          Inteligência para identificar oportunidades em startups.
        </h1>

        <p>
          Pesquisa pública, evidências rastreáveis, contexto técnico
          NVIDIA e recomendações estruturadas.
        </p>
      </header>

      <section className="panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Histórico</p>
            <h2>Startups analisadas</h2>
          </div>

          <button
            type="button"
            onClick={() => {
              setShowNewAnalysisForm((current) => !current);
              setSelectedAnalysis(null);
              setSelectedStartupHistory(null);
              setError("");
            }}
          >
            Nova análise
          </button>
        </div>

        {showNewAnalysisForm && (
          <form
            className="analysis-form"
            onSubmit={handleCreateAnalysis}
          >
            <label>
              Nome da startup
              <input
                value={startupName}
                onChange={(event) =>
                  setStartupName(event.target.value)
                }
                placeholder="Ex.: Enter"
              />
            </label>

            <label>
              Setor
              <input
                value={sector}
                onChange={(event) => setSector(event.target.value)}
                placeholder="Ex.: Legaltech"
              />
            </label>

            <button type="submit" disabled={loadingAnalysis}>
              {loadingAnalysis ? "Analisando..." : "Iniciar análise"}
            </button>
          </form>
        )}

        {loadingHistory && <p>Carregando histórico...</p>}

        {error && <p className="error">{error}</p>}

        {loadingAnalysis && (
          <section className="pipeline-loading" aria-live="polite">
            <div className="pipeline-loading-header">
              <div>
                <p className="eyebrow">Pipeline multiagente</p>
                <h3>Análise em andamento</h3>
              </div>

              <span className="pipeline-estimate">
                Progresso estimado
              </span>
            </div>

            <p className="pipeline-note">
              O backend executa o fluxo completo e devolve o resultado ao
              final da análise.
            </p>

            <ol className="pipeline-steps">
              {PIPELINE_STEPS.map((step, index) => {
                const isCompleted = index < pipelineStep;
                const isCurrent = index === pipelineStep;

                return (
                  <li
                    className={[
                      "pipeline-step",
                      isCompleted ? "completed" : "",
                      isCurrent ? "current" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    key={step.title}
                  >
                    <span className="pipeline-marker">
                      {isCompleted ? "✓" : index + 1}
                    </span>

                    <div>
                      <div className="pipeline-step-title">
                        <strong>{step.title}</strong>

                        {isCurrent && (
                          <span className="pipeline-status">
                            Em andamento
                          </span>
                        )}

                        {isCompleted && (
                          <span className="pipeline-status done">
                            Concluído
                          </span>
                        )}
                      </div>

                      <p>{step.description}</p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </section>
        )}

        {!loadingHistory && startups.length === 0 && (
          <p>Nenhuma startup foi analisada ainda.</p>
        )}

        {!loadingHistory && startups.length > 0 && (
          <div className="startup-list">
            {startups.map((startup) => (
              <button
                className="startup-card"
                key={startup.startup_id}
                type="button"
                onClick={() =>
                  void handleOpenStartupHistory(startup)
                }
              >
                <div>
                  <h3>{startup.name}</h3>

                  <p>{startup.sector || "Setor não informado"}</p>

                  <small>
                    Última análise:{" "}
                    {formatDate(startup.latest_analysis_at)}
                  </small>
                </div>

                <div className="startup-meta">
                  <span>
                    {startup.classification_category ||
                      "Sem classificação"}
                  </span>

                  <strong>
                    Oportunidade NVIDIA:{" "}
                    {startup.nvidia_opportunity_score ?? "-"}
                  </strong>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {loadingStartupHistory && (
        <section className="panel result-panel">
          <p>Carregando análises salvas...</p>
        </section>
      )}

      {selectedStartupHistory && !loadingStartupHistory && (
        <section className="panel result-panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Versões salvas</p>
              <h2>{selectedStartupHistory.startup_name}</h2>
            </div>

            <button
              className="ghost-button"
              type="button"
              onClick={() => {
                setSelectedStartupHistory(null);
                setSelectedAnalysis(null);
              }}
            >
              Fechar
            </button>
          </div>

          {selectedStartupHistory.analyses.length === 0 && (
            <p>Não há análises salvas para esta startup.</p>
          )}

          <div className="analysis-history-list">
            {selectedStartupHistory.analyses.map((analysis) => (
              <button
                className="analysis-history-card"
                key={analysis.analysis_id}
                type="button"
                onClick={() =>
                  void handleOpenSavedAnalysis(analysis.analysis_id)
                }
              >
                <div>
                  <h3>
                    Análise de {formatDate(analysis.created_at)}
                  </h3>

                  <p>
                    {analysis.classification_category ||
                      "Sem classificação"}
                  </p>
                </div>

                <div className="analysis-history-meta">
                  <span>
                    Fontes coletadas: {analysis.sources_successful}
                  </span>

                  <span>Gaps: {analysis.gaps_count}</span>

                  <strong>
                    Oportunidade NVIDIA:{" "}
                    {analysis.nvidia_opportunity_score ?? "-"}
                  </strong>
                </div>
              </button>
            ))}
          </div>
        </section>
      )}

      {loadingSavedAnalysis && (
        <section className="panel result-panel">
          <p>Carregando resultado salvo...</p>
        </section>
      )}

      {selectedAnalysis && !loadingSavedAnalysis && (
        <section className="panel result-panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Resultado</p>
              <h2>{selectedAnalysis.research.startup_name}</h2>
            </div>

            <button
              type="button"
              onClick={() =>
                downloadBriefing(
                  selectedAnalysis.briefing.markdown,
                  selectedAnalysis.research.startup_name,
                )
              }
            >
              Baixar briefing .md
            </button>
          </div>

          <div className="result-tabs">
            <button
              className={
                activeResultTab === "summary"
                  ? "result-tab active"
                  : "result-tab"
              }
              type="button"
              onClick={() => setActiveResultTab("summary")}
            >
              Resumo
            </button>

            <button
              className={
                activeResultTab === "recommendations"
                  ? "result-tab active"
                  : "result-tab"
              }
              type="button"
              onClick={() => setActiveResultTab("recommendations")}
            >
              Recomendações
            </button>

            <button
              className={
                activeResultTab === "evidences"
                  ? "result-tab active"
                  : "result-tab"
              }
              type="button"
              onClick={() => setActiveResultTab("evidences")}
            >
              Fontes e evidências
            </button>

            <button
              className={
                activeResultTab === "briefing"
                  ? "result-tab active"
                  : "result-tab"
              }
              type="button"
              onClick={() => setActiveResultTab("briefing")}
            >
              Briefing
            </button>
          </div>

          {activeResultTab === "summary" && (
            <div className="tab-content">
              <div className="score-grid">
                <article>
                  <span>Classificação</span>
                  <strong>
                    {selectedAnalysis.research.classification.category}
                  </strong>
                </article>

                <article>
                  <span>AI-native</span>
                  <strong>
                    {
                      selectedAnalysis.research.classification
                        .ai_native_score
                    }
                  </strong>
                </article>

                <article>
                  <span>Wrapper risk</span>
                  <strong>
                    {
                      selectedAnalysis.research.classification
                        .wrapper_risk_score
                    }
                  </strong>
                </article>

                <article>
                  <span>Oportunidade NVIDIA</span>
                  <strong>
                    {
                      selectedAnalysis.research.classification
                        .nvidia_opportunity_score
                    }
                  </strong>
                </article>
              </div>

              <div className="summary-details">
                <article>
                  <span>Fontes coletadas</span>
                  <strong>
                    {selectedAnalysis.research.sources_successful}
                  </strong>
                </article>

                <article>
                  <span>Evidências validadas</span>
                  <strong>
                    {selectedAnalysis.research.evidences.length}
                  </strong>
                </article>

                <article>
                  <span>Gaps públicos</span>
                  <strong>
                    {selectedAnalysis.research.gaps.length}
                  </strong>
                </article>
              </div>

              <h3>Gaps e limites públicos</h3>

              {selectedAnalysis.research.gaps.length === 0 && (
                <p>Nenhum gap público relevante foi identificado.</p>
              )}

              <div className="gap-list">
                {selectedAnalysis.research.gaps.map((gap) => (
                  <article className="gap-card" key={gap.category}>
                    <strong>{gap.category}</strong>
                    <p>{gap.message}</p>
                  </article>
                ))}
              </div>
            </div>
          )}

          {activeResultTab === "recommendations" && (
            <div className="tab-content">
              <h3>Recomendações NVIDIA</h3>

              <div className="recommendation-list">
                {selectedAnalysis.recommendations.recommendations.map(
                  (recommendation) => (
                    <article
                      className="recommendation-card"
                      key={recommendation.technology_id}
                    >
                      <div className="recommendation-header">
                        <h4>{recommendation.technology_name}</h4>

                        <span>{recommendation.priority}</span>
                      </div>

                      <p>
                        <strong>Complexidade:</strong>{" "}
                        {recommendation.complexity}
                      </p>

                      <p>
                        <strong>Justificativa técnica:</strong>{" "}
                        {recommendation.technical_reason}
                      </p>

                      <p>
                        <strong>Justificativa de negócio:</strong>{" "}
                        {recommendation.business_reason}
                      </p>

                      <p>
                        <strong>Próxima ação:</strong>{" "}
                        {recommendation.next_action}
                      </p>

                      <details className="recommendation-evidences">
                        <summary>
                          Ver evidências que sustentam esta recomendação
                        </summary>

                        <div className="recommendation-evidence-grid">
                          <section>
                            <h5>Evidências da startup</h5>

                            {recommendation.startup_evidences.map((evidence) => (
                              <article
                                className="recommendation-evidence-card"
                                key={evidence.evidence_id}
                              >
                                <span>{evidence.evidence_id}</span>

                                <blockquote>{evidence.quote}</blockquote>

                                <a
                                  href={evidence.source_url}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  Abrir fonte
                                </a>
                              </article>
                            ))}
                          </section>

                          <section>
                            <h5>Evidências NVIDIA</h5>

                            {recommendation.nvidia_evidences.map((evidence) => (
                              <article
                                className="recommendation-evidence-card"
                                key={evidence.evidence_id}
                              >
                                <span>{evidence.evidence_id}</span>

                                <blockquote>{evidence.quote}</blockquote>

                                <a
                                  href={evidence.source_url}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  Abrir documentação NVIDIA
                                </a>
                              </article>
                            ))}
                          </section>
                        </div>
                      </details>
                    </article>
                  ),
                )}
              </div>
            </div>
          )}

          {activeResultTab === "evidences" && (
            <div className="tab-content">
              <h3>Fontes públicas</h3>

              <div className="source-list">
                {selectedAnalysis.research.sources.map((source) => (
                  <article className="source-card" key={source.url}>
                    <div>
                      <h4>{source.title || "Fonte sem título"}</h4>

                      <p>
                        Status: <strong>{source.status}</strong>
                      </p>

                      {source.word_count && (
                        <p>{source.word_count} palavras extraídas</p>
                      )}
                    </div>

                    <a
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Abrir fonte
                    </a>
                  </article>
                ))}
              </div>

              <h3>Evidências validadas</h3>

              <div className="evidence-list">
                {selectedAnalysis.research.evidences.map(
                  (evidence, index) => (
                    <details
                      className="evidence-card"
                      key={`${evidence.source_url}-${index}`}
                    >
                      <summary>
                        <strong>{evidence.category}</strong>
                        <span>{evidence.claim}</span>
                      </summary>

                      <p>
                        <strong>Trecho encontrado:</strong>
                      </p>

                      <blockquote>{evidence.quote}</blockquote>

                      <a
                        href={evidence.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Abrir evidência na fonte
                      </a>
                    </details>
                  ),
                )}
              </div>
            </div>
          )}

          {activeResultTab === "briefing" && (
            <div className="tab-content">
              <div className="briefing-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {selectedAnalysis.briefing.markdown}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </section>
      )}
    </main>
  );
}

export default App;