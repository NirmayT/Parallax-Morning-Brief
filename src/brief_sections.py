"""Minimal editorial section renderers."""
NAVY, MUTE, TINT = "#1f4e79", "#6b7280", "#f3f6fb"


def _h(value):
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _sentence_case(value):
    text = str(value or "").strip()
    if not text:
        return ""
    return text[0].upper() + text[1:]


def txt_summary(data):
    overview = str(data.get("overview", "") or "").strip()
    if not overview:
        return ""
    return f"\nMARKET READ\n{overview}"


def txt_parallax(data):
    title = str(data.get("title", "") or "").strip()
    text = str(data.get("text", "") or "").strip()
    if not title or not text:
        return ""
    return f"\nTHE PARALLAX\n{title}\n{text}"


def txt_headlines(items):
    lines = ["", "WORTH KNOWING"]
    for item in items:
        lines += [
            item.get("headline", ""),
            item.get("summary", ""),
            item.get("source", ""),
            "",
        ]
    return "\n".join(lines)


def txt_moving(data):
    story = str(data.get("story", "") or "").strip()
    watch = data.get("watch", []) or []
    if not story and not watch:
        return ""
    lines = ["", "WHAT'S MOVING"]
    if story:
        lines.append(story)
    if watch:
        lines.append("On the radar")
        lines.extend(f"* {_sentence_case(x)}" for x in watch)
    return "\n".join(lines)


def txt_question(data):
    question = str(data.get("question", "") or "").strip()
    answer = str(data.get("answer", "") or "").strip()
    if not question or not answer:
        return ""
    return f"\nTHE OPEN QUESTION\n{question}\n{answer}"


def html_summary(data):
    overview = str(data.get("overview", "") or "").strip()
    if not overview:
        return ""
    return (
        f'<div style="font-size:12px;font-weight:700;color:{NAVY};margin:20px 0 6px;'
        f'letter-spacing:.6px;text-transform:uppercase;">Market read</div>'
        f'<p style="font-size:15px;line-height:1.65;margin:0 0 10px;">{_h(overview)}</p>'
    )


def html_parallax(data):
    title = str(data.get("title", "") or "").strip()
    text = str(data.get("text", "") or "").strip()
    if not title or not text:
        return ""
    return (
        f'<div style="background:{TINT};border-left:4px solid {NAVY};padding:14px 16px;margin:20px 0;">'
        f'<div style="font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:{NAVY};">The Parallax</div>'
        f'<div style="font-size:15px;font-weight:700;margin:6px 0;">{_h(title)}</div>'
        f'<p style="font-size:14px;line-height:1.65;margin:0;">{_h(text)}</p></div>'
    )


def html_headlines(items):
    if not items:
        return ""
    parts = [
        f'<div style="font-size:13px;font-weight:700;color:{NAVY};margin:22px 0 10px;">Worth knowing</div>'
    ]
    for item in items:
        parts += [
            f'<p style="font-size:15px;font-weight:700;margin:14px 0 3px;">{_h(item.get("headline"))}</p>',
            f'<p style="font-size:14px;line-height:1.65;margin:2px 0;">{_h(item.get("summary"))}</p>',
            f'<p style="font-size:11.5px;color:{MUTE};margin:0;">{_h(item.get("source"))}</p>',
        ]
    return "\n".join(parts)


def html_moving(data):
    story = str(data.get("story", "") or "").strip()
    watch = data.get("watch", []) or []
    if not story and not watch:
        return ""
    parts = [
        f'<div style="font-size:13px;font-weight:700;color:{NAVY};margin:24px 0 8px;">What\'s moving</div>'
    ]
    if story:
        parts.append(
            f'<p style="font-size:14px;line-height:1.6;margin:0 0 10px;">{_h(story)}</p>'
        )
    if watch:
        parts += [
            f'<p style="font-size:12px;font-weight:700;color:{MUTE};margin:0;">On the radar</p>',
            '<ul style="font-size:14px;line-height:1.6;padding-left:18px;">',
        ]
        parts += [
            f'<li>{_h(_sentence_case(item))}</li>'
            for item in watch
        ] + ['</ul>']
    return "\n".join(parts)


def html_question(data):
    question = str(data.get("question", "") or "").strip()
    answer = str(data.get("answer", "") or "").strip()
    if not question or not answer:
        return ""
    return (
        f'<div style="font-size:13px;font-weight:700;color:{NAVY};margin:24px 0 8px;">The open question</div>'
        f'<p style="font-size:15px;font-weight:700;margin:0 0 6px;">{_h(question)}</p>'
        f'<p style="font-size:14px;line-height:1.65;margin:0;">{_h(answer)}</p>'
    )
