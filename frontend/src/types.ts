export type User = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  specialty: string;
};

export type ClinicalCase = {
  id: string;
  patient_name: string;
  mrn: string;
  age: number;
  sex: string;
  primary_concern: string;
  risk_level: "high" | "watch" | "stable" | string;
  status: string;
  admitted_at: string;
  suggested_questions: string[];
};

export type ClinicalNote = {
  id: string;
  case_id: string;
  note_type: string;
  author_role: string;
  note_date: string;
  title: string;
  body: string;
};

export type ClinicalCaseDetail = ClinicalCase & {
  notes: ClinicalNote[];
  timeline: Array<{ date: string; label: string; detail: string }>;
  active_problems: string[];
  medications: Array<{ name: string; dose: string; status: string }>;
  labs: Array<{ name: string; value: string; flag: string }>;
  vitals: Array<{ name: string; value: string; flag: string }>;
};

export type EvidenceChunk = {
  note_id: string;
  case_id: string;
  note_type: string;
  note_date: string;
  title: string;
  chunk_id: string;
  text: string;
  score: number;
};

export type Citation = {
  source_number: number;
  note_id: string;
  chunk_id: string;
  title: string;
  note_type: string;
  note_date: string;
};

export type AskResponse = {
  answer_id: string;
  question_id: string;
  answer: string;
  confidence: string;
  model: string;
  provider_used: string;
  created_at: string;
  evidence: EvidenceChunk[];
  citations: Citation[];
  limits: string[];
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  answer_id?: string | null;
  confidence?: string | null;
  model?: string | null;
  provider_used?: string | null;
  evidence: EvidenceChunk[];
  citations: Citation[];
  limits: string[];
};

export type ConversationResponse = {
  case_id: string;
  messages: ChatMessage[];
};

export type SummaryResponse = {
  case_id: string;
  sections: Record<string, string>;
  evidence: EvidenceChunk[];
};

export type BenchmarkResponse = {
  run_id: string;
  label: string;
  total: number;
  accepted: number;
  acceptance_rate: number;
  improvement_from_baseline: number;
  results: Array<{
    id: string;
    case_id: string;
    question: string;
    accepted: boolean;
    score: number;
    expected_evidence: string[];
    matched_evidence: string[];
  }>;
};
