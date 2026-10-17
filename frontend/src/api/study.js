import axiosClient from "./axiosClient";

/** kind: "quiz" | "flashcards"; options: { topic?, document_id?, count, difficulty, model? } */
export const generateStudy = async (kind, options) => (await axiosClient.post(`/study/${kind}`, options)).data;

export const runCode = async (code, stdin = "") =>
  (await axiosClient.post("/study/run", { code, stdin, language: "python" })).data;
