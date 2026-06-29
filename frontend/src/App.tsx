import { useEffect, useState, type FormEvent } from "react";
import {
  createFullAnalysis,
  getAnalysis,
  getStartups,
  type FullAnalysisResponse,
  type StartupHistoryItem,
} from "./api";
import "./App.css";

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

  const [selectedAnalysis, setSelectedAnalysis] =
    useState<FullAnalysisResponse | null>(null);

  const [startupName, setStartupName] = useState("");
  const [sector, setSector] = useState("");

  const [showNewAnalysisForm, setShowNewAnalysisForm] =
    useState(false);

  const [loadingHistory, setLoadingHistory] = useState(true);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [error, setError] = useState("");

  async function loadHistory() {
    try {
      setError("");

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

    try {
      setError("");
      setLoadingAnalysis(true);
      setSelectedAnalysis(null);

      const analysis = await createFullAnalysis({
        startup_name: startupName.trim(),
        sector: sector.trim() || undefined,
        max_sources: 4,
      });

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
      setLoadingAnalysis(false);
    }
  }

  async function handleOpenLatestAnalysis(
    startup: StartupHistoryItem,
  ) {
    if (!startup.latest_analysis_id) {
      setError("Essa startup ainda não tem análise salva.");
      return;
    }

    try {
      setError("");
      setLoadingAnalysis(true);

      const analysis = await getAnalysis(startup.latest_analysis_id);

      setSelectedAnalysis(analysis);
      setShowNewAnalysisForm(false);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Ocorreu um erro inesperado.",
      );
    } finally {
      setLoadingAnalysis(false);
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
          <div className="loading-box">
            <strong>Análise em andamento...</strong>
            <p>
              Pesquisando fontes públicas, extraindo evidências,
              consultando o RAG NVIDIA, gerando recomendações e
              salvando no Supabase.
            </p>
          </div>
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
                onClick={() => void handleOpenLatestAnalysis(startup)}
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

      {selectedAnalysis && (
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

                  <p>{recommendation.technical_reason}</p>

                  <p>
                    <strong>Próxima ação:</strong>{" "}
                    {recommendation.next_action}
                  </p>
                </article>
              ),
            )}
          </div>

          <h3>Briefing Markdown</h3>

          <pre className="markdown-preview">
            {selectedAnalysis.briefing.markdown}
          </pre>
        </section>
      )}
    </main>
  );
}

export default App;