import axiosClient, { API_BASE, authHeader, endSession, refreshSession } from "./axiosClient";
import { parseSSE } from "../lib/sse";

export const getChatSessions = async () => (await axiosClient.get("/chat/sessions")).data;

export const createSession = async (body = {}) => (await axiosClient.post("/chat/sessions", body)).data;

export const updateSession = async (sessionId, changes) =>
  (await axiosClient.patch(`/chat/sessions/${sessionId}`, changes)).data;

export const deleteSession = (sessionId) => axiosClient.delete(`/chat/sessions/${sessionId}`);

export const getSessionMessages = async (sessionId) =>
  (await axiosClient.get(`/chat/sessions/${sessionId}/messages`)).data;

export const getModels = async () => (await axiosClient.get("/chat/models")).data;

/**
 * POST to a streaming endpoint and call onEvent for every server-sent event.
 * fetch is used instead of axios/EventSource because we need POST, auth headers,
 * incremental reads and cancellation through an AbortSignal.
 */
async function streamRequest(path, body, { signal, onEvent }) {
  const send = () =>
    fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: JSON.stringify(body ?? {}),
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

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      message = (await response.json()).error || message;
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
    const { events, rest } = parseSSE(buffer);
    buffer = rest;
    events.forEach(onEvent);
  }
}

export const streamMessage = (sessionId, message, options) =>
  streamRequest(`/chat/sessions/${sessionId}/messages`, { message }, options);

export const streamRegenerate = (sessionId, options) =>
  streamRequest(`/chat/sessions/${sessionId}/regenerate`, {}, options);
