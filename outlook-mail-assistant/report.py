"""產生單封信的 Markdown 紀錄，以及定時彙整報告（Markdown + HTML）。"""

from html import escape

PRIORITY_LABEL = {"P1": "🔴 P1 緊急", "P2": "🟠 P2 高", "P3": "🟡 P3 一般", "P4": "⚪ P4 參考"}
STATUS_LABEL = {"skipped": "已略過（過濾規則）", "sensitive": "🔒 機密，需人工處理", "failed": "⚠️ 分析失敗"}


def _md_cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def mail_entry_md(mail: dict, a: dict) -> str:
    lines = [
        f"### {PRIORITY_LABEL[a['priority']]}｜{mail['subject']}",
        "",
        "| 欄位 | 內容 |",
        "|---|---|",
        f"| 寄件者 | {_md_cell(mail['sender_name'])} <{mail['sender_email']}> |",
        f"| 收件時間 | {mail['received']} |",
        f"| 我的身分 | {mail['my_role']} |",
        f"| 分類 | {a['category']} |",
        f"| 期限 | {_md_cell(a['deadline']) or '未提及'} |",
        f"| 等級原因 | {_md_cell(a['priority_reason'])} |",
        "",
        f"**摘要**：{a['summary']}",
        "",
    ]
    if a["key_points"]:
        lines += ["**重點**", ""] + [f"- {p}" for p in a["key_points"]] + [""]
    if a["suggested_actions"] or a["materials_to_prepare"] or a["people_to_consult"]:
        lines += ["| 類型 | 內容 |", "|---|---|"]
        lines += [f"| 建議動作 | {_md_cell(x)} |" for x in a["suggested_actions"]]
        lines += [f"| 準備資料 | {_md_cell(x)} |" for x in a["materials_to_prepare"]]
        lines += [f"| 找人協助 | {_md_cell(p['who'])}：{_md_cell(p['reason'])} |" for p in a["people_to_consult"]]
        lines.append("")
    if a["risks"]:
        lines += ["**⚠️ 風險**", ""] + [f"- {r}" for r in a["risks"]] + [""]
    if a["reply_needed"] and a["reply_draft"]:
        lines += ["**建議回覆**", "", "```text", a["reply_draft"], "```", ""]
    return "\n".join(lines) + "\n---\n\n"


def simple_entry_md(mail: dict, status: str, note: str = "") -> str:
    return (
        f"### {STATUS_LABEL[status]}｜{mail['subject']}\n\n"
        f"寄件者：{mail['sender_name']} <{mail['sender_email']}>　收件時間：{mail['received']}"
        + (f"\n\n{note}" if note else "")
        + "\n\n---\n\n"
    )


def _counts(rows: list) -> dict:
    counts = {p: 0 for p in PRIORITY_LABEL}
    for r in rows:
        if r["priority"] in counts:
            counts[r["priority"]] += 1
    return counts


def digest_md(title: str, rows: list, followups: list) -> str:
    counts = _counts(rows)
    out = [f"# {title}", "", "| 等級 | 封數 |", "|---|---|"]
    out += [f"| {PRIORITY_LABEL[p]} | {n} |" for p, n in counts.items()]
    out += ["", "## 新信件", ""]
    if not rows:
        out.append("這段期間沒有新信件。")
    else:
        out += ["| 等級 | 收件時間 | 寄件者 | 主旨 | 摘要 | 下一步 |", "|---|---|---|---|---|---|"]
        for r in rows:
            a = r["analysis"]
            label = PRIORITY_LABEL.get(r["priority"], r["priority"])
            if r["status"] != "analyzed":
                label = STATUS_LABEL.get(r["status"], r["status"])
            next_step = "；".join(a.get("suggested_actions", [])[:2])
            out.append(
                f"| {label} | {r['received']} | {_md_cell(r['sender'])} | {_md_cell(r['subject'])} "
                f"| {_md_cell(a.get('summary', ''))} | {_md_cell(next_step)} |"
            )
    out += ["", "## 尚未回覆的高優先信件", ""]
    if not followups:
        out.append("沒有待回覆的 P1/P2 信件。")
    else:
        out += ["| 等級 | 收件時間 | 寄件者 | 主旨 | 期限 |", "|---|---|---|---|---|"]
        for r in followups:
            out.append(
                f"| {PRIORITY_LABEL[r['priority']]} | {r['received']} | {_md_cell(r['sender'])} "
                f"| {_md_cell(r['subject'])} | {_md_cell(r['analysis'].get('deadline')) or '未提及'} |"
            )
    return "\n".join(out) + "\n"


def digest_html(title: str, rows: list, followups: list) -> str:
    style = "border:1px solid #ccc;padding:6px;vertical-align:top;font-size:13px"
    th = lambda cols: "<tr>" + "".join(f'<th style="{style};background:#f0f0f0">{c}</th>' for c in cols) + "</tr>"
    td = lambda cols: "<tr>" + "".join(f'<td style="{style}">{escape(str(c))}</td>' for c in cols) + "</tr>"
    table = lambda head, body: f'<table style="border-collapse:collapse;margin-bottom:16px">{th(head)}{"".join(body)}</table>'

    counts = _counts(rows)
    parts = [f"<h2>{escape(title)}</h2>", table(["等級", "封數"], [td([PRIORITY_LABEL[p], n]) for p, n in counts.items()])]

    parts.append("<h3>新信件</h3>")
    body = []
    for r in rows:
        a = r["analysis"]
        label = PRIORITY_LABEL.get(r["priority"], r["priority"]) if r["status"] == "analyzed" else STATUS_LABEL.get(r["status"], r["status"])
        actions = "；".join(a.get("suggested_actions", []))
        people = "；".join(f"{p['who']}（{p['reason']}）" for p in a.get("people_to_consult", []))
        body.append(td([label, r["received"], r["sender"], r["subject"], a.get("summary", ""), actions, people]))
    parts.append(table(["等級", "收件時間", "寄件者", "主旨", "摘要", "建議動作", "找誰"], body) if body else "<p>這段期間沒有新信件。</p>")

    parts.append("<h3>尚未回覆的高優先信件</h3>")
    body = [td([PRIORITY_LABEL[r["priority"]], r["received"], r["sender"], r["subject"], r["analysis"].get("deadline") or "未提及"]) for r in followups]
    parts.append(table(["等級", "收件時間", "寄件者", "主旨", "期限"], body) if body else "<p>沒有待回覆的 P1/P2 信件。</p>")
    return "<html><body style=\"font-family:'Microsoft JhengHei',sans-serif\">" + "".join(parts) + "</body></html>"
