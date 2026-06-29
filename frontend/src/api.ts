const API_URL = import.meta.env.VITE_API_URL;

if (!API_URL) {
  throw new Error("VITE_API_URL não configurada.");
}

export type StartupHistoryItem = {
  startup_id: string;
  name: string;
  sector: string | null;
  created_at: string;
  latest_analysis_id: string | null;
  latest_analysis_at: string | null;
  classification_category: string | null;
  nvidia_opportunity_score: number | null;
};

type StartupListResponse = {
  startups: StartupHistoryItem[];
};

export type Recommendation = {
  technology_id: string;
  technology_name: string;
  priority: "ALTA" | "MEDIA" | "BAIXA";
  complexity: "ALTA" | "MEDIA" | "BAIXA";
  technical_reason: string;
  business_reason: string;
  next_action: string;
};

export type FullAnalysisResponse = {
  analysis_id: string;
  research: {
    startup_name: string;
    sources_successful: number;
    classification: {
      category: string;
      ai_native_score: number;
      wrapper_risk_score: number;
      nvidia_opportunity_score: number;
    };
    gaps: {
      category: string;
      status: string;
      message: string;
    }[];
  };
  recommendations: {
    model: string;
    recommendations: Recommendation[];
    limitations: string[];
  };
  briefing: {
    startup_name: string;
    generated_at: string;
    recommendation_count: number;
    markdown: string;
  };
};

export async function getStartups(): Promise<
  StartupHistoryItem[]
> {
  const response = await fetch(`${API_URL}/startups`);

  if (!response.ok) {
    throw new Error("Não foi possível carregar o histórico.");
  }

  const data: StartupListResponse = await response.json();

  return data.startups;
}

export async function createFullAnalysis(payload: {
  startup_name: string;
  sector?: string;
  max_sources: number;
}): Promise<FullAnalysisResponse> {
  const response = await fetch(`${API_URL}/research/full`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);

    throw new Error(
      error?.detail || "Não foi possível executar a análise.",
    );
  }

  return response.json();
}

export async function getAnalysis(
  analysisId: string,
): Promise<FullAnalysisResponse> {
  const response = await fetch(
    `${API_URL}/analyses/${analysisId}`,
  );

  if (!response.ok) {
    throw new Error("Não foi possível carregar a análise salva.");
  }

  return response.json();
}