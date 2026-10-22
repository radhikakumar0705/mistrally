import axiosClient from "./axiosClient";
import type { FlashcardDeck, Quiz, RunResult, StudyKind, StudyRequest } from "./types";

export type StudyResult = Quiz | FlashcardDeck;

export const generateStudy = async (kind: StudyKind, options: StudyRequest) =>
  (await axiosClient.post<StudyResult>(`/study/${kind}`, options)).data;

export const runCode = async (code: string, stdin = "") =>
  (await axiosClient.post<RunResult>("/study/run", { code, stdin, language: "python" })).data;
