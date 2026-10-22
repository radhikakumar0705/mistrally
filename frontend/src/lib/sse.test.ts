import { describe, expect, it } from "vitest";
import { parseSSE } from "./sse";

describe("parseSSE", () => {
  it("parses complete events and keeps the partial remainder", () => {
    const buffer = 'data: {"type":"start"}\n\ndata: {"type":"token","content":"Hi"}\n\ndata: {"type":"tok';
    const { events, rest } = parseSSE(buffer);
    expect(events).toEqual([{ type: "start" }, { type: "token", content: "Hi" }]);
    expect(rest).toBe('data: {"type":"tok');
  });

  it("reassembles an event split across network chunks", () => {
    const first = parseSSE('data: {"type":"token",');
    expect(first.events).toEqual([]);
    const second = parseSSE(first.rest + '"content":"lo"}\n\n');
    expect(second.events).toEqual([{ type: "token", content: "lo" }]);
    expect(second.rest).toBe("");
  });

  it("handles CRLF line endings and skips malformed events", () => {
    const { events } = parseSSE('data: not json\r\n\r\ndata: {"type":"done"}\r\n\r\n');
    expect(events).toEqual([{ type: "done" }]);
  });
});
