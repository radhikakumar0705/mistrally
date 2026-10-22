import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { Quiz } from "../../api/types";
import QuizView from "./QuizView";

const quiz: Quiz = {
  kind: "quiz",
  source: "Lists",
  title: "Lists",
  questions: [
    { question: "Reverse copy?", options: ["a[::-1]", "a.sort()", "a.pop()", "len(a)"], answer_index: 0, explanation: "Slicing." },
    { question: "Append cost?", options: ["O(n^2)", "O(1) amortized", "O(log n)", "O(n)"], answer_index: 1, explanation: "Amortized." },
  ],
};

describe("QuizView", () => {
  it("reveals the answer and explanation, then shows the score", async () => {
    render(<QuizView quiz={quiz} />);
    expect(screen.getByText("Answered 0 of 2")).toBeInTheDocument();

    await userEvent.click(screen.getByText("a[::-1]"));
    expect(screen.getByText("Slicing.")).toBeInTheDocument();
    expect(screen.getByText("a.sort()").closest("button")).toBeDisabled();

    await userEvent.click(screen.getByText("O(n)"));
    expect(screen.getByText("You scored 1/2")).toBeInTheDocument();
  });
});
