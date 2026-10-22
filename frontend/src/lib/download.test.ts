import { describe, expect, it } from "vitest";
import { filenameFromDisposition } from "./download";

describe("filenameFromDisposition", () => {
  it("reads quoted and unquoted file names", () => {
    expect(filenameFromDisposition('attachment; filename="recursion-help.md"', "x.md")).toBe("recursion-help.md");
    expect(filenameFromDisposition("attachment; filename=notes.md", "x.md")).toBe("notes.md");
  });

  it("falls back when the header is missing or has no name", () => {
    expect(filenameFromDisposition(null, "conversation.md")).toBe("conversation.md");
    expect(filenameFromDisposition("attachment", "conversation.md")).toBe("conversation.md");
  });
});
