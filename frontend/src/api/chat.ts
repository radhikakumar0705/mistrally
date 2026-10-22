import axiosClient, { API_BASE, authHeader, endSession, refreshSession } from "./axiosClient";
import { parseSSE } from "../lib/sse";
import type { ApiError, ChatMessage, ChatSession, ModelList, StreamEvent } from "./types";

export const getChatSessions = async () => (await axiosClient.get<ChatSession[]>("/chat/sessions")).data;

export const createSession = async (body: { title?: string; model?: string | null } = {}) =>
  (await axiosClient.post<ChatSession>("/chat/sessions", body)).data;

export const updateSession = async (sessionId: number, changes: { title?: string; model?: string | null }) =>
  (await axiosClient.patch<ChatSession>(`/chat/sessions/${sessionId}`, changes)).data;

export const deleteSession = (sessionId: number) => axiosClient.delete(`/chat/sessions/${sessionId}`);

export const getSessionMessages = async (sessionId: number) =>
  (await axiosClient.get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`)).data;

export const getModels = async () => (await axiosClient.get<ModelList>("/chat/models")).data;

/** Download a conversation as Markdown; returns the file and the name the server suggests. */
export const exportSession = async (sessionId: number) => {
  const response = await axiosClient.get<Blob>(`/chat/sessions/${sessionId}/export`, { responseType: "blob" });
  return { blob: response.data, disposition: response.headers["content-disposition"] as string | undefined };
};

export interface StreamOptions {
  signal: AbortSignal;
  onEvent: (event: StreamEvent) => void;
}

/**
 * POST to a streaming endpoint and call onEvent for every server-sent event.
 * fetch is used instead of axios/EventSource because we need POST, auth headers,
 * incremental reads and cancellation through an AbortSignal.
 */
async function streamRequest(path: string, body: object, { signal, onEvent }: StreamOptions): Promise<void> {
  const send = () =>
    fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify(body),
      signal,
    });

  let response = await send();
  if (response.status === 401) {
    // The access token expired mid-session: refresh once and retry
    try {
      await refreshSession();
      response = await send();
    } catch {
      endSession({ expired: true });
    }
  }

  if (!response.ok || !response.body) {
    let message = `Request failed (${response.status})`;
    try {
      message = ((await response.json()) as ApiError).error || message;
    } catch {
      // not JSON
    }
    throw new Error(message);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const { events, rest } = parseSSE<StreamEvent>(buffer);
    buffer = rest;
    events.forEach(onEvent);
  }
}

export const streamMessage = (sessionId: number, message: string, options: StreamOptions) =>
  streamRequest(`/chat/sessions/${sessionId}/messages`, { message }, options);

export const streamRegenerate = (sessionId: number, options: StreamOptions) =>
  streamRequest(`/chat/sessions/${sessionId}/regenerate`, {}, options);
