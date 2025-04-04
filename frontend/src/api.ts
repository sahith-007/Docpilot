import type {
  AskResponse,
  BenchmarkResponse,
  ChatMessage,
  ClinicalCase,
  ClinicalCaseDetail,
  ConversationResponse,
  FeedbackResponse,
  FeedbackStatus,
  SummaryResponse,
  User
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type LoginResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers
    }
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = formatErrorDetail(payload.detail);
    throw new ApiError(response.status, detail ?? `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function formatErrorDetail(detail: unknown): string | undefined {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const first = detail[0];
    if (first && typeof first === "object" && "msg" in first) {
      return String(first.msg);
    }
    return "Please check the form fields and try again.";
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as { message: unknown }).message);
  }
  return undefined;
}

export const api = {
  login(email: string, password: string) {
    return request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
  },
  register(fullName: string, email: string, password: string, specialty: string) {
    return request<LoginResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        full_name: fullName,
        email,
        password,
        specialty
      })
    });
  },
  listCases(token: string) {
    return request<ClinicalCase[]>("/cases", {}, token);
  },
  getCase(token: string, caseId: string) {
    return request<ClinicalCaseDetail>(`/cases/${caseId}`, {}, token);
  },
  getConversation(token: string, caseId: string) {
    return request<ConversationResponse>(`/assistant/conversations/${caseId}`, {}, token);
  },
  summarize(token: string, caseId: string) {
    return request<SummaryResponse>(
      "/assistant/summary",
      {
        method: "POST",
        body: JSON.stringify({ case_id: caseId })
      },
      token
    );
  },
  ask(token: string, caseId: string, question: string) {
    return request<AskResponse>(
      "/assistant/ask",
      {
        method: "POST",
        body: JSON.stringify({ case_id: caseId, question, max_evidence: 5 })
      },
      token
    );
  },
  messageFromAsk(question: string, response: AskResponse): ChatMessage[] {
    const createdAt = response.created_at;
    return [
      {
        id: response.question_id,
        role: "user",
        content: question,
        created_at: createdAt,
        evidence: [],
        citations: [],
        limits: []
      },
      {
        id: response.answer_id,
        role: "assistant",
        content: response.answer,
        created_at: response.created_at,
        answer_id: response.answer_id,
        confidence: response.confidence,
        model: response.model,
        provider_used: response.provider_used,
        evidence: response.evidence,
        citations: response.citations,
        limits: response.limits
      }
    ];
  },
  feedback(token: string, answerId: string, status: FeedbackStatus, notes = "") {
    return request<FeedbackResponse>(
      "/feedback",
      {
        method: "POST",
        body: JSON.stringify({
          answer_id: answerId,
          status,
          notes
        })
      },
      token
    );
  },
  runBenchmark(token: string) {
    return request<BenchmarkResponse>(
      "/benchmarks/run",
      {
        method: "POST"
      },
      token
    );
  }
};
