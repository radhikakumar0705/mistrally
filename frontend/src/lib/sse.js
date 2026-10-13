/**
 * Split a server-sent-events buffer into complete events.
 * Returns the parsed `data:` payloads and whatever partial event is left over,
 * which the caller keeps and prepends to the next network chunk.
 */
export function parseSSE(buffer) {
  const normalized = buffer.replace(/\r\n/g, "\n");
  const blocks = normalized.split("\n\n");
  const rest = blocks.pop();
  const events = [];

  for (const block of blocks) {
    const data = block
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) continue;
    try {
      events.push(JSON.parse(data));
    } catch {
      // Ignore malformed events rather than breaking the whole stream
    }
  }
  return { events, rest };
}
