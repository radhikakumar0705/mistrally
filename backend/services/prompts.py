"""Prompt construction shared by every model provider."""

SYSTEM_PROMPT = (
    "You are Mistrally, a helpful AI teaching assistant for programmers. "
    "Give simple, clear explanations, and include code examples whenever the question calls for them. "
    "Format answers in Markdown and put code in fenced code blocks with a language tag."
)


def _cite(chunk):
    """How an excerpt is labelled for the model, e.g. "notes.pdf, page 3"."""
    label = chunk["source"]
    if chunk.get("page"):
        label += f", page {chunk['page']}"
    return label


def build_messages(history, context_chunks, user_message):
    """
    Build a chat message list: system prompt (plus any retrieved document excerpts),
    the previous turns of this conversation, then the new message.
    """
    system = SYSTEM_PROMPT
    if context_chunks:
        excerpts = "\n\n".join(f"[{_cite(c)}]\n{c['text']}" for c in context_chunks)
        system += (
            "\n\nThe user has uploaded documents. These excerpts may help; use them when they are "
            "relevant and mention the document (and page) you used:\n\n" + excerpts
        )

    messages = [{"role": "system", "content": system}]
    for turn in history:
        messages.append({"role": "user", "content": turn.user_message})
        messages.append({"role": "assistant", "content": turn.bot_response})
    messages.append({"role": "user", "content": user_message})
    return messages
