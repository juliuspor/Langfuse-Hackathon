import { DebateTurn, getMockTurnsForTopic, type NewsHeadline } from "./mockData";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";
export const DEFAULT_TURNS = 4;

export interface DebateSummary {
  conversation_id: string;
  topic: string;
  status: string;
  turns: DebateTurn[];
  meta?: {
    warnings?: string[];
    total_turns?: number;
    news_context?: unknown;
    [key: string]: unknown;
  };
}

export interface LiveDebateCallbacks {
  onConnected?: (data: { status?: string; request_id?: string }) => void;
  onConversation?: (data: {
    conversation_id: string;
    topic: string;
    status: string;
    news_context?: unknown;
  }) => void;
  onTurn?: (turn: DebateTurn) => void;
  onCompleted?: (data: DebateSummary) => void;
  onError?: (error: string) => void;
}

export interface NewsFeedResponse {
  status: string;
  provider: string;
  category: string;
  cached?: boolean;
  fetched_at?: string;
  headlines: NewsHeadline[];
}

export async function healthCheck(): Promise<{ status: string }> {
  return apiRequest<{ status: string }>("/health");
}

export async function fetchHeadlines(
  category: string,
  limit = 10
): Promise<NewsFeedResponse> {
  const params = new URLSearchParams({
    category,
    limit: String(limit),
  });
  return apiRequest<NewsFeedResponse>(`/api/news/headlines?${params}`);
}

export async function startDebate(
  topic: string,
  turns = DEFAULT_TURNS,
  includeAudio = true
): Promise<DebateSummary> {
  const debate = await apiRequest<DebateSummary>("/api/debate/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      topic,
      turns,
      language: "de",
      include_audio: includeAudio,
    }),
  });
  return normalizeDebate(debate);
}

export async function getDebate(conversationId: string): Promise<DebateSummary> {
  const debate = await apiRequest<DebateSummary>(
    `/api/debate/${encodeURIComponent(conversationId)}`
  );
  return normalizeDebate(debate);
}

export function startLiveDebate(
  topic: string,
  turns = DEFAULT_TURNS,
  includeAudio = true,
  headline: NewsHeadline | null = null,
  callbacks: LiveDebateCallbacks = {}
): () => void {
  if (USE_MOCK) {
    return startMockDebate(topic, turns, callbacks);
  }

  const params = new URLSearchParams({
    topic,
    turns: String(turns),
    language: "de",
    include_audio: String(includeAudio),
  });
  addArticleParams(params, headline);

  const es = new EventSource(`${API_BASE}/api/debate/live?${params}`);

  es.addEventListener("connected", (e) => {
    callbacks.onConnected?.(JSON.parse(e.data));
  });

  es.addEventListener("conversation", (e) => {
    callbacks.onConversation?.(JSON.parse(e.data));
  });

  es.addEventListener("turn", (e) => {
    callbacks.onTurn?.(normalizeTurn(JSON.parse(e.data)));
  });

  es.addEventListener("completed", (e) => {
    callbacks.onCompleted?.(normalizeDebate(JSON.parse(e.data)));
    es.close();
  });

  es.addEventListener("error", (e) => {
    if ("data" in e && typeof e.data === "string" && e.data) {
      callbacks.onError?.(JSON.parse(e.data).message);
    } else {
      callbacks.onError?.("Verbindung zum Server verloren");
    }
    es.close();
  });

  return () => es.close();
}

function addArticleParams(params: URLSearchParams, headline: NewsHeadline | null) {
  if (!headline) {
    return;
  }
  if (headline.url) {
    params.set("article_url", headline.url);
  }
  if (headline.source) {
    params.set("article_source", headline.source);
  }
  if (headline.teaser) {
    params.set("article_teaser", headline.teaser);
  }
  if (headline.published_at) {
    params.set("article_published_at", headline.published_at);
  }
}

function startMockDebate(
  _topic: string,
  turns: number,
  callbacks: LiveDebateCallbacks
): () => void {
  let cancelled = false;
  const convId = crypto.randomUUID();

  const allTurns: DebateTurn[] = getMockTurnsForTopic("1").slice(0, turns);

  (async () => {
    await delay(500);
    if (cancelled) return;
    callbacks.onConnected?.({ status: "connected" });
    callbacks.onConversation?.({
      conversation_id: convId,
      topic: _topic,
      status: "running",
    });

    for (let i = 0; i < allTurns.length; i++) {
      await delay(1500 + Math.random() * 2000);
      if (cancelled) return;
      callbacks.onTurn?.(allTurns[i]);
    }

    await delay(500);
    if (cancelled) return;
    callbacks.onCompleted?.({
      conversation_id: convId,
      topic: _topic,
      status: "completed",
      turns: allTurns,
      meta: { total_turns: allTurns.length, warnings: [] },
    });
  })();

  return () => { cancelled = true; };
}

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export function getAudioUrl(conversationId: string, turnIndex: number): string {
  return `${API_BASE}/api/debate/${conversationId}/audio/${turnIndex}.mp3`;
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      payload?.error?.message || "Die Anfrage konnte nicht verarbeitet werden";
    throw new Error(message);
  }

  return payload as T;
}

function normalizeDebate(debate: DebateSummary): DebateSummary {
  return {
    ...debate,
    turns: (debate.turns || []).map(normalizeTurn),
  };
}

function normalizeTurn(turn: DebateTurn): DebateTurn {
  return {
    ...turn,
    audio_url: normalizeUrl(turn.audio_url),
  };
}

function normalizeUrl(url?: string): string | undefined {
  if (!url) {
    return undefined;
  }
  if (/^https?:\/\//i.test(url)) {
    return url;
  }
  return `${API_BASE}${url.startsWith("/") ? "" : "/"}${url}`;
}
