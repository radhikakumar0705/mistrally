import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DocumentRecord } from "../../api/types";
import StudyDialog from "./StudyDialog";

const ready: DocumentRecord[] = [
  {
    id: "d1",
    filename: "notes.md",
    file_type: "md",
    size_bytes: 120,
    status: "ready",
    progress: 100,
    pages: null,
    chunks: 1,
    error: null,
    uploaded_at: null,
  },
];

describe("StudyDialog", () => {
  it("defaults to studying from a document once documents have loaded", () => {
    // Mounted closed with no documents (as on first render of the chat page)...
    const { rerender } = render(<StudyDialog open={false} onClose={() => {}} documents={[]} model="m" />);
    // ...then opened after the documents arrived
    rerender(<StudyDialog open onClose={() => {}} documents={ready} model="m" />);
    expect(screen.getByLabelText("One of my documents")).toBeChecked();
    expect(screen.getByLabelText("Document")).toHaveValue("d1");
  });

  it("falls back to a topic when there are no documents", () => {
    render(<StudyDialog open onClose={() => {}} documents={[]} model="m" />);
    expect(screen.getByLabelText("A topic")).toBeChecked();
    expect(screen.getByRole("button", { name: /Generate quiz/ })).toBeDisabled();
  });
});
