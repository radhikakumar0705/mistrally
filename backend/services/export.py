"""Export a conversation as a Markdown document (e.g. to keep as study notes)."""
import json
import re

MAX_SLUG_LENGTH = 80


def _one_line(text: str) -> str:
    """Collapse whitespace so user-controlled text can't start new Markdown blocks."""
    return " ".join((text or "").split())


def _sources(raw) -> list[str]:
    if not raw:
        return []
    labels = []
    for source in json.loads(raw):
        if isinstance(source, str):  # answers saved by older versions stored plain file names
            labels.append(source)
        elif source.get("page"):
            labels.append(f"{source['document']} (p. {source['page']})")
        else:
            labels.append(source["document"])
    return labels


def to_markdown(session, messages) -> str:
    """A readable Markdown transcript: title, metadata, then each question and answer with its sources."""
    lines = [f"# {_one_line(session.title)}", ""]
    meta = f"_Exported from Mistrally · {len(messages)} message{'s' if len(messages) != 1 else ''}"
    if session.model:
        meta += f" · model: {_one_line(session.model)}"
    lines += [meta + "_", ""]

    if not messages:
        lines.append("_No messages yet._")
    for message in messages:
        asked = f" ({message.timestamp:%Y-%m-%d %H:%M} UTC)" if message.timestamp else ""
        lines += ["---", "", f"**You:**{asked}", "", message.user_message, "", "**Mistrally:**", "", message.bot_response]
        sources = _sources(message.sources)
        if sources:
            lines += ["", f"Sources: {', '.join(sources)}"]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_filename(title: str) -> str:
    """A safe download name: lowercase letters, digits and dashes only (no paths, no quotes)."""
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")[:MAX_SLUG_LENGTH].strip("-")
    return f"{slug or 'conversation'}.md"
