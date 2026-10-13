import axiosClient from "./axiosClient";

export const getChatSessions = async () =>
  (await axiosClient.get("/chat/sessions")).data;

export const createSession = async () =>
  (await axiosClient.post("/chat/sessions", {})).data;

export const deleteSession = (sessionId) =>
  axiosClient.delete(`/chat/sessions/${sessionId}`);

export const getSessionMessages = async (sessionId) =>
  (await axiosClient.get(`/chat/sessions/${sessionId}/messages`)).data;

export const sendMessage = async (sessionId, message) =>
  (await axiosClient.post(`/chat/sessions/${sessionId}/messages`, { message })).data;

export const uploadDocument = async (file) => {
  const form = new FormData();
  form.append("file", file);
  return (await axiosClient.post("/chat/upload", form)).data;
};
