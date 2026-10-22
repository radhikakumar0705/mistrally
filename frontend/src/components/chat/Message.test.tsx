import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { UiMessage } from "../../hooks/useChat";
import Message from "./Message";

describe("Message", () => {
  it("renders assistant markdown with a labelled code block and sources", () => {
    const content = "Use **slicing**:\n\n```python\nnums[::-1]\n```";
    render(
      <Message
        message={{ id: "a1", role: "assistant", content, sources: [{ document: "notes.pdf", page: 3 }, "old.txt"] }}
        isLast
        streaming={false}
        onRegenerate={() => {}}
      />
    );
    expect(screen.getByText("slicing").tagName).toBe("STRONG");
    expect(screen.getByText("python")).toBeInTheDocument();
    expect(screen.getByLabelText("Copy code")).toBeInTheDocument();
    expect(screen.getByText("notes.pdf · p. 3")).toBeInTheDocument();
    expect(screen.getByText("old.txt")).toBeInTheDocument();
  });

  it("offers regenerate only on the last finished answer", async () => {
    const onRegenerate = vi.fn();
    const message: UiMessage = { id: "a1", role: "assistant", content: "Hi", sources: [] };
    const { rerender } = render(<Message message={message} isLast streaming={false} onRegenerate={onRegenerate} />);
    await userEvent.click(screen.getByLabelText("Regenerate"));
    expect(onRegenerate).toHaveBeenCalled();

    rerender(<Message message={message} isLast={false} streaming={false} onRegenerate={onRegenerate} />);
    expect(screen.queryByLabelText("Regenerate")).not.toBeInTheDocument();
  });

  it("shows a typing indicator before the first token and errors after", () => {
    const { rerender } = render(
      <Message message={{ id: "a1", role: "assistant", content: "", pending: true }} isLast streaming />
    );
    expect(screen.getByLabelText("Mistrally is thinking")).toBeInTheDocument();

    rerender(
      <Message message={{ id: "a1", role: "assistant", content: "", error: "Model unavailable" }} isLast streaming={false} />
    );
    expect(screen.getByText("Model unavailable")).toBeInTheDocument();
  });

  it("renders user text as plain text, not markdown", () => {
    render(<Message message={{ id: "u1", role: "user", content: "**not bold**" }} />);
    expect(screen.getByText("**not bold**")).toBeInTheDocument();
  });
});
