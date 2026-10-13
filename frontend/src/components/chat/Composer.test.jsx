import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Composer from "./Composer";

const setup = (props = {}) => {
  const handlers = { onSend: vi.fn(), onStop: vi.fn(), onUpload: vi.fn() };
  render(<Composer streaming={false} uploading={false} {...handlers} {...props} />);
  return handlers;
};

describe("Composer", () => {
  it("sends trimmed text on Enter and clears the box", async () => {
    const { onSend } = setup();
    const box = screen.getByLabelText("Message");
    await userEvent.type(box, "  hello world  {Enter}");
    expect(onSend).toHaveBeenCalledWith("hello world");
    expect(box).toHaveValue("");
  });

  it("adds a new line on Shift+Enter instead of sending", async () => {
    const { onSend } = setup();
    const box = screen.getByLabelText("Message");
    await userEvent.type(box, "line one{Shift>}{Enter}{/Shift}line two");
    expect(onSend).not.toHaveBeenCalled();
    expect(box).toHaveValue("line one\nline two");
  });

  it("disables send for empty input", () => {
    setup();
    expect(screen.getByLabelText("Send message")).toBeDisabled();
  });

  it("shows a stop button while streaming", async () => {
    const { onStop } = setup({ streaming: true });
    await userEvent.click(screen.getByLabelText("Stop generating"));
    expect(onStop).toHaveBeenCalled();
    expect(screen.queryByLabelText("Send message")).not.toBeInTheDocument();
  });

  it("passes uploaded files on", async () => {
    const { onUpload } = setup();
    const file = new File(["notes"], "notes.txt", { type: "text/plain" });
    await userEvent.upload(document.querySelector('input[type="file"]'), file);
    expect(onUpload).toHaveBeenCalledWith(file);
  });
});
