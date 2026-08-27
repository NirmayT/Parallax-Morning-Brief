"""Parallax edition renderer with market snapshot and compliance footer."""
import config
import utils
import brief_sections as bs

NAVY, MUTE, GREEN, RED = "#1f4e79", "#6b7280", "#137333", "#c5221f"
WRAP = "font-family:Georgia,'Times New Roman',serif;max-width:600px;margin:0 auto;padding:20px 18px;color:#1a1a1a;line-height:1.55;"


def _color(value, neutral=False):
    if neutral or value in (None, 0):
        return MUTE
    return GREEN if value > 0 else RED


def _rows(group, rate=False, neutral=False):
    rows = []
    for name, item in group.items():
        latest, previous = item.get("latest"), item.get("prev")
        if latest is None:
            rows.append((name, "n/a", "n/a", MUTE, item.get("session_date")))
        elif rate:
            direction = None if previous is None else latest - previous
            rows.append(
                (
                    name,
                    utils.format_rate(latest),
                    "n/a" if direction is None else f"{direction * 100:+.0f}",
                    _color(direction),
                    item.get("session_date"),
                )
            )
        else:
            rows.append(
                (
                    name,
                    utils.format_level(latest, item.get("decimals", 2)),
                    utils.format_pct(
                        item.get("ret_1d"),
                        2 if item.get("decimals") else 1,
                    ),
                    _color(item.get("ret_1d"), neutral),
                    item.get("session_date"),
                )
            )
    return rows


def _table(label, value_label, move_label, rows):
    if not rows:
        return ""

    head = (
        "padding:7px 4px;font-size:11px;font-weight:700;color:#6b7280;"
        "text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #ddd;"
    )
    out = [
        f'<table role="presentation" width="100%" style="border-collapse:collapse;margin:18px 0 6px;border-top:1px solid #eee;">'
        f'<tr><td style="{head}">{label}</td>'
        f'<td style="{head}text-align:right;">{value_label}</td>'
        f'<td style="{head}text-align:right;width:78px;">{move_label}</td></tr>'
    ]

    for i, (name, value, move, color, _) in enumerate(rows):
        border = "" if i == len(rows) - 1 else "border-bottom:1px solid #f4f4f4;"
        out.append(
            f'<tr>'
            f'<td style="padding:7px 4px;font-size:13.5px;{border}">{bs._h(name)}</td>'
            f'<td style="padding:7px 4px;font-size:13.5px;text-align:right;{border}"><strong>{bs._h(value)}</strong></td>'
            f'<td style="padding:7px 4px;font-size:13.5px;text-align:right;color:{color};{border}">{bs._h(move)}</td>'
            f'</tr>'
        )

    out.append("</table>")

    dates = sorted({str(row[4]) for row in rows if row[4]})
    if dates:
        out.append(
            f'<p style="font-size:10.5px;color:#9ca3af;margin:2px 0 12px;">'
            f'Latest available session: {", ".join(dates)}</p>'
        )

    return "\n".join(out)


def _snapshot(market):
    return "\n".join(
        [
            _table(
                "Equities",
                "Last",
                "Chg %",
                _rows(market.get("equities", {})),
            ),
            _table(
                "FX",
                "Spot",
                "Chg %",
                _rows(market.get("fx", {}), neutral=True),
            ),
            _table(
                "UST Yields",
                "Yield",
                "Chg bp",
                _rows(market.get("rates", {}), rate=True),
            ),
            '<p style="font-size:10.5px;color:#9ca3af;margin:8px 0 18px;">'
            'Asset groups may reflect different market sessions. '
            'Each uses its latest available observation.</p>',
        ]
    )


def _plain_compliance_footer():
    lines = [
        "",
        config.PUBLISHER_NAME,
        config.SUBSCRIPTION_DISCLOSURE,
        config.PUBLIC_SITE_URL,
        config.COMPLIANCE_CONTACT_EMAIL,
        "",
        config.PROJECT_DISCLAIMER,
        "Prices via Yahoo Finance for this personal prototype and may lag.",
        "This is one morning read, not investment advice.",
    ]
    return "\n".join(line for line in lines if line)


def _html_compliance_footer():
    publisher = bs._h(config.PUBLISHER_NAME)
    disclosure = bs._h(config.SUBSCRIPTION_DISCLOSURE)
    site = bs._h(config.PUBLIC_SITE_URL)
    contact = bs._h(config.COMPLIANCE_CONTACT_EMAIL)
    disclaimer = bs._h(config.PROJECT_DISCLAIMER)

    return (
        '<div style="border-top:1px solid #e5e7eb;margin-top:26px;padding-top:14px;'
        'font-size:11.5px;line-height:1.6;color:#9ca3af;">'
        f'<strong style="color:#6b7280;">{publisher}</strong><br>'
        f'{disclosure}<br>'
        f'<a href="{site}" style="color:#6b7280;text-decoration:underline;">{site}</a>'
        f' &nbsp;&middot;&nbsp; '
        f'<a href="mailto:{contact}" style="color:#6b7280;text-decoration:underline;">{contact}</a>'
        '<br><br>'
        f'{disclaimer}<br>'
        'Prices via Yahoo Finance for this personal prototype and may lag. '
        'This is one morning read, not investment advice.<br><br>'
        '<span data-parallax-unsubscribe></span>'
        '</div>'
    )


def build_plain_text(reference, market, ai, status):
    return "\n".join(
        filter(
            None,
            [
                ai.get("daily_title", "Markets in Focus"),
                "Every market has multiple angles.",
                f"{reference:%A, %B %d, %Y} | Risk mood: {ai.get('sentiment','Mixed')}",
                ai.get("mood"),
                ai.get("key_line"),
                bs.txt_summary(ai.get("market_summary", {})),
                "MARKET SNAPSHOT\nLatest available observations by asset.",
                bs.txt_parallax(ai.get("parallax", {})),
                bs.txt_headlines(ai.get("top_headlines", [])),
                bs.txt_moving(ai.get("whats_moving", {})),
                bs.txt_question(ai.get("open_question", {})),
                _plain_compliance_footer(),
            ],
        )
    )


def build_html(reference, market, ai, status):
    h = [
        f'<div style="{WRAP}">'
        f'<div style="text-align:center;padding-bottom:14px;border-bottom:1px solid #e5e7eb;">'
        f'<div style="font-size:26px;font-weight:700;line-height:1.2;">'
        f'{bs._h(ai.get("daily_title", "Markets in Focus"))}</div>'
        f'<div style="font-size:13px;font-style:italic;color:{MUTE};margin-top:6px;">'
        f'Every market has multiple angles.</div>'
        f'<div style="font-size:12px;color:#9ca3af;margin-top:10px;">'
        f'{reference:%A, %B %d, %Y} &nbsp;&middot;&nbsp; '
        f'Risk mood: {bs._h(ai.get("sentiment", "Mixed"))}</div></div>'
    ]

    if ai.get("mood"):
        h.append(
            f'<p style="font-size:16px;line-height:1.6;margin:18px 0 6px;">'
            f'{bs._h(ai["mood"])}</p>'
        )

    if ai.get("key_line"):
        h.append(
            f'<p style="font-size:18px;line-height:1.45;font-weight:700;color:{NAVY};margin:16px 0;">'
            f'{bs._h(ai["key_line"])}</p>'
        )

    h += [
        bs.html_summary(ai.get("market_summary", {})),
        _snapshot(market),
        bs.html_parallax(ai.get("parallax", {})),
        bs.html_headlines(ai.get("top_headlines", [])),
        bs.html_moving(ai.get("whats_moving", {})),
        bs.html_question(ai.get("open_question", {})),
        _html_compliance_footer(),
        "</div>",
    ]

    return "\n".join(h)


def build_brief(reference, market, ai, status):
    return (
        build_plain_text(reference, market, ai, status),
        build_html(reference, market, ai, status),
    )
