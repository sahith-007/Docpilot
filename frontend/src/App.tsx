import {
  Activity,
  AlertTriangle,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  Database,
  FlaskConical,
  FileText,
  Loader2,
  LogOut,
  MessageSquareText,
  PanelLeftClose,
  PanelLeftOpen,
  Pill,
  Search,
  Send,
  ShieldCheck,
  Stethoscope,
  UserPlus,
  UserRound
} from "lucide-react";
import { FormEvent, KeyboardEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { ApiError, api } from "./api";
import type {
  BenchmarkResponse,
  ChatMessage,
  ClinicalCase,
  ClinicalCaseDetail,
  FeedbackStatus,
  SummaryResponse,
  User
} from "./types";

type Session = {
  token: string;
  user: User;
};

type FeedbackUiState = {
  status?: FeedbackStatus | null;
  message?: string;
  saving?: FeedbackStatus | null;
  error?: string;
};

type View = "summary" | "timeline" | "clinical" | "notes" | "benchmarks";

const sessionKey = "docpilot.session";

function readStoredSession(): Session | null {
  const raw = localStorage.getItem(sessionKey);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    localStorage.removeItem(sessionKey);
    return null;
  }
}

export default function App() {
  const [session, setSession] = useState<Session | null>(() => readStoredSession());
  const [cases, setCases] = useState<ClinicalCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [caseDetail, setCaseDetail] = useState<ClinicalCaseDetail | null>(null);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [benchmark, setBenchmark] = useState<BenchmarkResponse | null>(null);
  const [view, setView] = useState<View>("summary");
  const [question, setQuestion] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [benchmarking, setBenchmarking] = useState(false);
  const [error, setError] = useState("");
  const [authNotice, setAuthNotice] = useState("");
  const [feedbackState, setFeedbackState] = useState<Record<string, FeedbackUiState>>({});

  useEffect(() => {
    if (!session) return;

    setLoading(true);
    api
      .listCases(session.token)
      .then((items) => {
        setCases(items);
        if (!selectedCaseId && items.length > 0) {
          setSelectedCaseId(items[0].id);
        }
      })
      .catch(handleRequestError)
      .finally(() => setLoading(false));
  }, [session, selectedCaseId]);

  useEffect(() => {
    if (!session || !selectedCaseId) return;

    setLoading(true);
    setChatLoading(true);
    setQuestion("");
    setError("");
    setChatMessages([]);
    setFeedbackState({});
    Promise.all([
      api.getCase(session.token, selectedCaseId),
      api.summarize(session.token, selectedCaseId),
      api.getConversation(session.token, selectedCaseId)
    ])
      .then(([detail, summaryResponse, conversation]) => {
        setCaseDetail(detail);
        setSummary(summaryResponse);
        setChatMessages(conversation.messages);
      })
      .catch(handleRequestError)
      .finally(() => {
        setLoading(false);
        setChatLoading(false);
      });
  }, [session, selectedCaseId]);

  const selectedCase = useMemo(
    () => cases.find((item) => item.id === selectedCaseId) ?? null,
    [cases, selectedCaseId]
  );

  function handleSession(nextSession: Session) {
    setAuthNotice("");
    setError("");
    setSession(nextSession);
    localStorage.setItem(sessionKey, JSON.stringify(nextSession));
  }

  function clearSession(notice = "") {
    localStorage.removeItem(sessionKey);
    setSession(null);
    setCases([]);
    setSelectedCaseId("");
    setCaseDetail(null);
    setSummary(null);
    setChatMessages([]);
    setBenchmark(null);
    setFeedbackState({});
    setError("");
    setAuthNotice(notice);
  }

  function logout() {
    clearSession();
  }

  function handleRequestError(err: unknown) {
    if (err instanceof ApiError && err.status === 401) {
      clearSession("Your session expired. Please sign in again.");
      return;
    }
    setError(err instanceof Error ? err.message : "Request failed");
  }

  async function askQuestion(event: FormEvent) {
    event.preventDefault();
    if (!session || !selectedCaseId || question.trim().length < 8) return;

    setAsking(true);
    setError("");
    setFeedbackState({});
    const currentQuestion = question.trim();
    try {
      const response = await api.ask(session.token, selectedCaseId, currentQuestion);
      setChatMessages((current) => [...current, ...api.messageFromAsk(currentQuestion, response)]);
      setQuestion("");
    } catch (err) {
      handleRequestError(err);
    } finally {
      setAsking(false);
    }
  }

  async function submitFeedback(answerId: string, status: FeedbackStatus) {
    if (!session) return;

    const previousState = feedbackState[answerId];
    setFeedbackState((current) => ({
      ...current,
      [answerId]: {
        ...current[answerId],
        saving: status,
        error: ""
      }
    }));
    try {
      const response = await api.feedback(session.token, answerId, status);
      setFeedbackState((current) => ({
        ...current,
        [answerId]: {
          status: response.status,
          message: response.message,
          saving: null,
          error: ""
        }
      }));
      setChatMessages((current) =>
        current.map((message) =>
          message.answer_id === answerId
            ? {
                ...message,
                feedback_status: response.status,
                feedback_message: response.message,
                feedback_updated_at: response.updated_at
              }
            : message
        )
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        clearSession("Your session expired. Please sign in again.");
        return;
      }
      setFeedbackState((current) => ({
        ...current,
        [answerId]: {
          ...previousState,
          saving: null,
          error: err instanceof Error ? err.message : "Review failed"
        }
      }));
    }
  }

  function submitOnEnter(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  }

  async function runBenchmark() {
    if (!session) return;

    setBenchmarking(true);
    setError("");
    try {
      const response = await api.runBenchmark(session.token);
      setBenchmark(response);
      setView("benchmarks");
    } catch (err) {
      handleRequestError(err);
    } finally {
      setBenchmarking(false);
    }
  }

  if (!session) {
    return <LoginScreen notice={authNotice} onLogin={handleSession} />;
  }

  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <aside className={`sidebar ${sidebarCollapsed ? "collapsed" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <Stethoscope size={20} aria-hidden="true" />
          </div>
          <div className="brand-text">
            <strong>DocPilot</strong>
            <span>Clinical review</span>
          </div>
          <button
            className="icon-button collapse-button"
            onClick={() => setSidebarCollapsed((value) => !value)}
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
          </button>
        </div>

        <div className="case-list-label">
          <span>Cases</span>
          <span>{cases.length}</span>
        </div>

        <div className="case-list">
          {cases.map((clinicalCase) => (
            <button
              className={`case-row ${selectedCaseId === clinicalCase.id ? "active" : ""}`}
              key={clinicalCase.id}
              onClick={() => {
                setSelectedCaseId(clinicalCase.id);
                setQuestion("");
                setError("");
                setView("summary");
              }}
              title={clinicalCase.patient_name}
            >
              <span className={`risk-dot ${clinicalCase.risk_level}`} />
              <span className="case-initials">{patientInitials(clinicalCase.patient_name)}</span>
              <span>
                <strong>{clinicalCase.patient_name}</strong>
                <small>{clinicalCase.primary_concern}</small>
              </span>
            </button>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="user-chip">
            <UserRound size={16} aria-hidden="true" />
            <span>
              {session.user.full_name}
              <small>{session.user.specialty}</small>
            </span>
          </div>
          <button className="icon-button" onClick={logout} title="Log out" aria-label="Log out">
            <LogOut size={18} />
          </button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">Synthetic case workspace</p>
            <h1>{selectedCase?.patient_name ?? "Loading case"}</h1>
          </div>
        </header>

        {error && (
          <div className="notice error">
            <AlertTriangle size={17} aria-hidden="true" />
            {error}
          </div>
        )}

        {loading && !caseDetail ? (
          <div className="loading-state">
            <Loader2 className="spin" size={24} />
          </div>
        ) : (
          <div className="workspace">
            <section className="patient-strip">
              <Metric label="Age" value={selectedCase?.age.toString() ?? "--"} />
              <Metric label="Concern" value={selectedCase?.primary_concern ?? "--"} wide />
              <Metric label="Status" value={selectedCase?.status ?? "--"} />
              <Metric label="Risk" value={selectedCase?.risk_level ?? "--"} tone={selectedCase?.risk_level} />
            </section>

            <div className="workspace-grid">
              <section className="left-panel">
                <div className="tabs" role="tablist" aria-label="Case views">
                  <TabButton active={view === "summary"} onClick={() => setView("summary")}>
                    <ClipboardCheck size={16} />
                    Summary
                  </TabButton>
                  <TabButton active={view === "timeline"} onClick={() => setView("timeline")}>
                    <CalendarDays size={16} />
                    Timeline
                  </TabButton>
                  <TabButton active={view === "clinical"} onClick={() => setView("clinical")}>
                    <FlaskConical size={16} />
                    Labs & Meds
                  </TabButton>
                  <TabButton active={view === "notes"} onClick={() => setView("notes")}>
                    <FileText size={16} />
                    Notes
                  </TabButton>
                  <TabButton active={view === "benchmarks"} onClick={() => setView("benchmarks")}>
                    <Database size={16} />
                    Benchmarks
                  </TabButton>
                </div>

                {view === "summary" && <SummaryPanel summary={summary} />}
                {view === "timeline" && <TimelinePanel detail={caseDetail} />}
                {view === "clinical" && <ClinicalPanel detail={caseDetail} />}
                {view === "notes" && <NotesPanel detail={caseDetail} />}
                {view === "benchmarks" && (
                  <BenchmarkPanel
                    benchmark={benchmark}
                    onRun={runBenchmark}
                    loading={benchmarking}
                  />
                )}
              </section>

              <section className="right-panel">
                <ChatPanel
                  asking={asking}
                  feedbackState={feedbackState}
                  loading={chatLoading}
                  messages={chatMessages}
                  onFeedback={submitFeedback}
                  onQuestionChange={setQuestion}
                  onSubmit={askQuestion}
                  onTextareaKeyDown={submitOnEnter}
                  question={question}
                  suggestedQuestions={selectedCase?.suggested_questions ?? []}
                />
              </section>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function LoginScreen({
  notice,
  onLogin
}: {
  notice: string;
  onLogin: (session: Session) => void;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [fullName, setFullName] = useState("Dr. Aisha Morgan");
  const [email, setEmail] = useState("maya.chen@docpilot.health");
  const [password, setPassword] = useState("demo-clinical");
  const [specialty, setSpecialty] = useState("Hospital Medicine");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response =
        mode === "register"
          ? await api.register(fullName, email, password, specialty)
          : await api.login(email, password);
      onLogin({ token: response.access_token, user: response.user });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="brand large">
          <div className="brand-mark">
            <Stethoscope size={22} aria-hidden="true" />
          </div>
          <div>
            <strong>DocPilot</strong>
            <span>{mode === "register" ? "Create doctor account" : "Synthetic clinical assistant"}</span>
          </div>
        </div>

        <form onSubmit={submit} className="login-form">
          {mode === "register" && (
            <>
              <label>
                Full name
                <input value={fullName} onChange={(event) => setFullName(event.target.value)} />
              </label>
              <label>
                Specialty
                <input value={specialty} onChange={(event) => setSpecialty(event.target.value)} />
              </label>
            </>
          )}
          <label>
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            Password
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
            />
          </label>
          {notice && <div className="notice info">{notice}</div>}
          {error && <div className="notice error">{error}</div>}
          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? (
              <Loader2 className="spin" size={18} />
            ) : mode === "register" ? (
              <UserPlus size={18} />
            ) : (
              <ShieldCheck size={18} />
            )}
            {mode === "register" ? "Create account" : "Sign in"}
          </button>
          <button
            className="text-button"
            type="button"
            onClick={() => {
              setMode((current) => (current === "login" ? "register" : "login"));
              setError("");
            }}
          >
            {mode === "register" ? "Use existing demo login" : "Create account"}
          </button>
        </form>
      </section>
    </main>
  );
}

function Metric({
  label,
  value,
  wide,
  tone
}: {
  label: string;
  value: string;
  wide?: boolean;
  tone?: string;
}) {
  return (
    <div className={`metric ${wide ? "wide" : ""}`}>
      <span>{label}</span>
      <strong className={tone ? `tone-${tone}` : ""}>{value}</strong>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button className={`tab-button ${active ? "active" : ""}`} onClick={onClick} type="button">
      {children}
    </button>
  );
}

function SummaryPanel({ summary }: { summary: SummaryResponse | null }) {
  if (!summary) return <EmptyState icon={<Activity size={22} />} label="Summary pending" />;

  return (
    <div className="summary-list">
      {Object.entries(summary.sections).map(([heading, value]) => (
        <article className="summary-item" key={heading}>
          <h3>{heading}</h3>
          <p>{value}</p>
        </article>
      ))}
    </div>
  );
}

function TimelinePanel({ detail }: { detail: ClinicalCaseDetail | null }) {
  if (!detail) return <EmptyState icon={<CalendarDays size={22} />} label="Timeline pending" />;

  return (
    <div className="timeline-list">
      {detail.timeline.map((event) => (
        <article className="timeline-item" key={`${event.date}-${event.label}`}>
          <time>{event.date}</time>
          <div>
            <h3>{event.label}</h3>
            <p>{event.detail}</p>
          </div>
        </article>
      ))}
    </div>
  );
}

function ClinicalPanel({ detail }: { detail: ClinicalCaseDetail | null }) {
  if (!detail) return <EmptyState icon={<FlaskConical size={22} />} label="Clinical data pending" />;

  return (
    <div className="clinical-grid">
      <section className="clinical-section">
        <h3>Active Problems</h3>
        <div className="problem-list">
          {detail.active_problems.map((problem) => (
            <span key={problem}>{problem}</span>
          ))}
        </div>
      </section>

      <section className="clinical-section">
        <h3>
          <Pill size={16} />
          Medications
        </h3>
        {detail.medications.map((medication) => (
          <ClinicalRow
            key={`${medication.name}-${medication.dose}`}
            label={medication.name}
            value={medication.dose}
            flag={medication.status}
          />
        ))}
      </section>

      <section className="clinical-section">
        <h3>
          <FlaskConical size={16} />
          Labs
        </h3>
        {detail.labs.map((lab) => (
          <ClinicalRow key={`${lab.name}-${lab.value}`} label={lab.name} value={lab.value} flag={lab.flag} />
        ))}
      </section>

      <section className="clinical-section">
        <h3>Vitals / Diagnostics</h3>
        {detail.vitals.map((vital) => (
          <ClinicalRow
            key={`${vital.name}-${vital.value}`}
            label={vital.name}
            value={vital.value}
            flag={vital.flag}
          />
        ))}
      </section>
    </div>
  );
}

function ClinicalRow({ label, value, flag }: { label: string; value: string; flag: string }) {
  return (
    <div className="clinical-row">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{flag}</small>
    </div>
  );
}

function NotesPanel({ detail }: { detail: ClinicalCaseDetail | null }) {
  if (!detail) return <EmptyState icon={<FileText size={22} />} label="Notes pending" />;

  return (
    <div className="notes-list">
      {detail.notes.map((note) => (
        <article className="note-card" key={note.id}>
          <div className="note-header">
            <span>{noteTypeLabel(note.note_type)}</span>
            <time>{note.note_date}</time>
          </div>
          <h3>{note.title}</h3>
          <p>{note.body}</p>
        </article>
      ))}
    </div>
  );
}

function ChatPanel({
  asking,
  feedbackState,
  loading,
  messages,
  onFeedback,
  onQuestionChange,
  onSubmit,
  onTextareaKeyDown,
  question,
  suggestedQuestions
}: {
  asking: boolean;
  feedbackState: Record<string, FeedbackUiState>;
  loading: boolean;
  messages: ChatMessage[];
  onFeedback: (answerId: string, status: FeedbackStatus) => void;
  onQuestionChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  onTextareaKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  question: string;
  suggestedQuestions: string[];
}) {
  return (
    <div className="chat-shell">
      <div className="chat-header">
        <div>
          <p className="eyebrow">Ask DocPilot</p>
          <h2>Case chat</h2>
        </div>
        <MessageSquareText size={19} aria-hidden="true" />
      </div>

      <div className="suggestion-row" aria-label="Suggested clinical questions">
        {suggestedQuestions.map((suggestion) => (
          <button key={suggestion} type="button" onClick={() => onQuestionChange(suggestion)}>
            {suggestion}
          </button>
        ))}
      </div>

      <div className="chat-thread" aria-live="polite">
        {loading ? (
          <EmptyState icon={<Loader2 className="spin" size={22} />} label="Loading case chat" />
        ) : messages.length === 0 ? (
          <EmptyState icon={<Search size={22} />} label="Ask a question to start the case thread" />
        ) : (
          messages.map((message) => (
            <ChatMessageCard
              feedbackState={message.answer_id ? feedbackState[message.answer_id] : undefined}
              key={message.id}
              message={message}
              onFeedback={onFeedback}
            />
          ))
        )}
        {asking && (
          <div className="message-row assistant">
            <article className="message-bubble assistant pending">
              <Loader2 className="spin" size={17} />
              Reviewing retrieved evidence...
            </article>
          </div>
        )}
      </div>

      <form className="chat-composer" onSubmit={onSubmit}>
        <textarea
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          onKeyDown={onTextareaKeyDown}
          rows={4}
          aria-label="Clinical question"
          placeholder="Ask a case-specific clinical question..."
        />
        <button className="primary-button" type="submit" disabled={asking || question.trim().length < 8}>
          {asking ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
          Send
        </button>
      </form>
    </div>
  );
}

function ChatMessageCard({
  feedbackState,
  message,
  onFeedback
}: {
  feedbackState?: FeedbackUiState;
  message: ChatMessage;
  onFeedback: (answerId: string, status: FeedbackStatus) => void;
}) {
  const isAssistant = message.role === "assistant";
  const activeFeedback = feedbackState?.status ?? message.feedback_status ?? null;
  const feedbackMessage = feedbackState?.message ?? message.feedback_message ?? "";
  const feedbackError = feedbackState?.error ?? "";
  const savingFeedback = feedbackState?.saving ?? null;
  const limitationItems = formatLimitations(message.limits);

  return (
    <div className={`message-row ${message.role}`}>
      <article className={`message-bubble ${message.role}`}>
        {isAssistant && (
          <div className="answer-header">
            <span className={`confidence ${message.confidence ?? "medium"}`}>
              {message.confidence ?? "medium"}
            </span>
            <span>{getAssistantLabel(message.model, message.provider_used === "demo")}</span>
            <span>{message.evidence.length} sources</span>
          </div>
        )}

        <p>{message.content}</p>

        {isAssistant && limitationItems.length > 0 && (
          <div className="limits">
            <AlertTriangle size={16} aria-hidden="true" />
            <ul>
              {limitationItems.map((limit) => (
                <li key={limit}>{limit}</li>
              ))}
            </ul>
          </div>
        )}

        {isAssistant && message.evidence.length > 0 && (
          <details className="evidence-details">
            <summary>
              <FileText size={16} />
              Evidence review
            </summary>
            <div className="evidence-cards">
              {message.evidence.map((chunk, index) => (
                <article className="evidence-card" key={chunk.chunk_id}>
                  <div className="note-header">
                    <span>
                      [{index + 1}] {chunk.title}
                    </span>
                    <strong>{Math.round(chunk.score * 100)}%</strong>
                  </div>
                  <p>{chunk.text}</p>
                  <small>
                    {chunk.note_id} · {noteTypeLabel(chunk.note_type)} · {chunk.note_date}
                  </small>
                </article>
              ))}
            </div>
          </details>
        )}

        {isAssistant && message.answer_id && (
          <>
            <div className="feedback-actions">
              <button
                className={activeFeedback === "accepted" ? "selected" : ""}
                onClick={() => onFeedback(message.answer_id!, "accepted")}
                disabled={savingFeedback === "accepted"}
                type="button"
              >
                {savingFeedback === "accepted" ? (
                  <Loader2 className="spin" size={16} />
                ) : (
                  <CheckCircle2 size={16} />
                )}
                Accept
              </button>
              <button
                className={activeFeedback === "review" ? "selected" : ""}
                onClick={() => onFeedback(message.answer_id!, "review")}
                disabled={savingFeedback === "review"}
                type="button"
              >
                {savingFeedback === "review" ? (
                  <Loader2 className="spin" size={16} />
                ) : (
                  <AlertTriangle size={16} />
                )}
                Review
              </button>
              <button
                className={activeFeedback === "rejected" ? "selected" : ""}
                onClick={() => onFeedback(message.answer_id!, "rejected")}
                disabled={savingFeedback === "rejected"}
                type="button"
              >
                {savingFeedback === "rejected" ? (
                  <Loader2 className="spin" size={16} />
                ) : (
                  <ShieldCheck size={16} />
                )}
                Reject
              </button>
            </div>
            {(feedbackMessage || feedbackError || savingFeedback) && (
              <span className={`feedback-state ${feedbackError ? "error-text" : ""}`}>
                {feedbackError || (savingFeedback ? "Saving decision..." : feedbackMessage)}
              </span>
            )}
          </>
        )}

        <time className="message-time">{formatMessageTime(message.created_at)}</time>
      </article>
    </div>
  );
}

function formatMessageTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function getAssistantLabel(model?: string | null, demoMode = false) {
  if (demoMode || model === "demo-local") return "DocPilot Demo";
  return "DocPilot AI";
}

function formatLimitations(rawLimits?: string[] | string | null) {
  const rawItems = Array.isArray(rawLimits) ? rawLimits : rawLimits ? [rawLimits] : [];
  return rawItems
    .flatMap(splitLimitationText)
    .map(cleanLimitationText)
    .filter(Boolean);
}

function splitLimitationText(value: string) {
  return value
    .replace(/\r/g, "\n")
    .replace(/\s+(no\s+(?:direct|definitive|documented|supporting|positive|clear)\b)/gi, "\n$1")
    .split(/\n|;|(?:^|\s)[\-•]\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function cleanLimitationText(value: string) {
  const lowerValue = value.toLowerCase();
  if (
    !lowerValue ||
    lowerValue === "none" ||
    lowerValue === "n/a" ||
    lowerValue === "no limitations" ||
    lowerValue === "no meaningful limitations"
  ) {
    return "";
  }

  let cleaned = value
    .replace(/^\s*[-•]\s*/, "")
    .replace(/\s+/g, " ")
    .trim();
  cleaned = cleaned.replace(/\s+provided$/i, " are provided");
  cleaned = cleaned.replace(/\s+documented$/i, " are documented");
  cleaned = cleaned.replace(
    /^no definitive wound infection symptoms such as (.+)$/i,
    "No definitive wound infection symptoms, such as $1, are documented"
  );
  cleaned = cleaned.replace(
    /^no direct diagnostic evidence for (.+)$/i,
    "No direct diagnostic evidence confirms $1"
  );
  cleaned = cleaned.replace(
    /^no direct signs of atelectasis provided$/i,
    "No direct signs of atelectasis are provided"
  );
  cleaned = cleaned.replace(/^no documented (.+)$/i, (_, item: string) => {
    return `${item.charAt(0).toUpperCase()}${item.slice(1)} are not documented`;
  });
  cleaned = cleaned.replace(
    /^no positive culture results yet$/i,
    "Culture results are not yet positive"
  );

  cleaned = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  if (!/[.!?]$/.test(cleaned)) cleaned += ".";
  return cleaned;
}

function BenchmarkPanel({
  benchmark,
  loading,
  onRun
}: {
  benchmark: BenchmarkResponse | null;
  loading: boolean;
  onRun: () => void;
}) {
  if (!benchmark) {
    return (
      <div className="benchmark-empty">
        <EmptyState icon={<BarChart3 size={22} />} label="No benchmark run in this session" />
        <button className="secondary-button" onClick={onRun} disabled={loading}>
          {loading ? <Loader2 className="spin" size={17} /> : <BarChart3 size={17} />}
          Run benchmark
        </button>
      </div>
    );
  }

  return (
    <div className="benchmark-panel">
      <div className="benchmark-score">
        <div>
          <span>Acceptance</span>
          <strong>{benchmark.acceptance_rate}%</strong>
        </div>
        <div>
          <span>Improvement</span>
          <strong>+{benchmark.improvement_from_baseline}%</strong>
        </div>
        <div>
          <span>Cases</span>
          <strong>
            {benchmark.accepted}/{benchmark.total}
          </strong>
        </div>
      </div>

      <div className="benchmark-results">
        {benchmark.results.map((result) => (
          <article className="benchmark-row" key={result.id}>
            <div>
              <strong>{result.question}</strong>
              <small>{result.matched_evidence.join(", ")}</small>
            </div>
            <span className={result.accepted ? "passed" : "missed"}>{result.score}%</span>
          </article>
        ))}
      </div>
    </div>
  );
}

function EmptyState({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <div className="empty-state">
      {icon}
      <span>{label}</span>
    </div>
  );
}

function noteTypeLabel(noteType: string) {
  return noteType
    .split("_")
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function patientInitials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}
