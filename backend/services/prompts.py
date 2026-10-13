"""Prompt construction shared by every model provider."""

SYSTEM_PROMPT = (
    "You are Mistrally, a helpful AI teaching assistant for programmers. "
    "Give simple, clear explanations, and include code examples whenever the question calls for them. "
    "Format answers in Markdown and put code in fenced code blocks with a language tag."
)


def build_messages(history, context_chunks, user_message):
    """
    Build an Ollama /api/chat message list: system prompt (plus any retrieved
    document excerpts), the previous turns of this conversation, then the new message.
    """
    system = SYSTEM_PROMPT
    if context_chunks:
        excerpts = "\n\n".join(f"[{c['source']}]\n{c['text']}" for c in context_chunks)
        system += (
            "\n\nThe user has uploaded documents. These excerpts may help; use them when they are "
            "relevant and mention the document name you used:\n\n" + excerpts
        )

    messages = [{"role": "system", "content": system}]
    for turn in history:
        messages.append({"role": "user", "content": turn.user_message})
        messages.append({"role": "assistant", "content": turn.bot_response})
    messages.append({"role": "user", "content": user_message})
    return messages
