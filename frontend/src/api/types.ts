/**
 * API types, generated from backend/openapi.yaml (`npm run types:api` writes schema.d.ts).
 * CI regenerates schema.d.ts and fails if it differs, so these can't drift from the backend.
 */
import type { components } from "./schema";

type Schemas = components["schemas"];

export type ApiError = Schemas["Error"];
export type FeatureConfig = Schemas["FeatureConfig"];
export type User = Schemas["User"];
export type AuthSession = Schemas["Session"];
export type ModelList = Schemas["ModelList"];
export type ChatSession = Schemas["ChatSession"];
export type ChatMessage = Schemas["ChatMessage"];
export type Source = Schemas["Source"];
export type StreamEvent = Schemas["StreamEvent"];
export type DocumentRecord = Schemas["Document"];
export type StudyRequest = Schemas["StudyRequest"];
export type Quiz = Schemas["Quiz"];
export type QuizQuestion = Schemas["QuizQuestion"];
export type FlashcardDeck = Schemas["FlashcardDeck"];
export type RunResult = Schemas["RunResult"];

export type StudyKind = "quiz" | "flashcards";
