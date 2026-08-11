"""
PDF briefing generator for Yavapai Swarm deployments and SHADOW missions.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF


def _ascii(text: str) -> str:
    """Strip non-latin chars for Helvetica compatibility."""
    return (
        text.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )


class BriefingPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, _ascii(self.doc_title), align="L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}  |  {_ascii(self.footer_note)}", align="C")

    def section_title(self, title: str):
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(0, 82, 120)
        self.cell(0, 10, _ascii(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0, 120, 170)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, _ascii(text))
        self.ln(2)

    def bullet(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        self.cell(6, 5.5, "-")
        self.multi_cell(0, 5.5, _ascii(text))
        self.set_x(x)

    def simple_table(self, headers: list[str], rows: list[list[str]], col_widths: list[float]):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(213, 232, 240)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 8, _ascii(h), border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 9)
        fill = False
        for row in rows:
            if fill:
                self.set_fill_color(245, 248, 250)
            else:
                self.set_fill_color(255, 255, 255)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 8, _ascii(str(cell))[:80], border=1, fill=fill)
            self.ln()
            fill = not fill


def generate_shadow_briefing_pdf(result: dict[str, Any], out_path: Path) -> Path:
    """Generate SHADOW agent mission briefing PDF."""
    pdf = BriefingPDF()
    pdf.doc_title = "SHADOW Agent  |  Sedona Military/anomaly Briefing"
    pdf.footer_note = f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Tokens remaining: {result.get('token_budget', {}).get('tokens_remaining', 'N/A')}"
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(40, 20, 80)
    pdf.cell(0, 12, "SHADOW Agent Briefing", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(80, 40, 120)
    pdf.cell(0, 9, "Regional multi-domain anomaly Anomaly Analysis", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 6, f"Mission: {result.get('mission_id', 'unknown')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Activation: {result.get('activation', 'SHADOW')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Completed: {result.get('completed_at', '')[:19]}Z", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Stop reason: {result.get('stop_reason', 'unknown')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    summary = result.get("summary", {})
    budget = result.get("token_budget", {})

    pdf.section_title("1. Executive Summary")
    pdf.body_text(
        f"The SHADOW overlay agent executed {result.get('turns_executed', 0)} analysis turns "
        f"before stopping ({result.get('stop_reason', 'unknown')}). "
        f"Substantial discoveries: {summary.get('substantial_discoveries', 0)}. "
        f"Coupled anomalies: {summary.get('coupled_anomalies', 0)}. "
        f"Highest severity: {summary.get('highest_severity', 0)}."
    )
    pdf.body_text(summary.get("recommendation", ""))

    rl = result.get("recursive_learning") or summary.get("recursive_learning") or {}
    if rl or summary.get("recursive_loop"):
        pdf.section_title("2. Recursive Loop Learning")
        pdf.body_text(
            f"Cycles completed: {result.get('cycles_completed', summary.get('cycles_completed', 0))}. "
            f"Turns absorbed: {rl.get('turns_absorbed', 'N/A')}."
        )
        if rl.get("top_boosted_terms"):
            terms = ", ".join(f"{t}({s})" for t, s in rl["top_boosted_terms"][:8])
            pdf.body_text(f"Boosted terms: {terms}")
        if rl.get("learned_seeds"):
            for seed in rl["learned_seeds"][-5:]:
                pdf.bullet(seed[:100])
        adaptive = rl.get("adaptive_seeds", {})
        if adaptive.get("active_seeds"):
            pdf.ln(2)
            pdf.section_title("Adaptive Evolved Seeds")
            for seed in adaptive["active_seeds"][:5]:
                pdf.bullet(seed[:100])
        trends = rl.get("adsb_trends", {})
        if trends:
            pdf.body_text(
                f"ADS-B trends - KSEZ delta: {trends.get('ksez', {}).get('delta', 0)}, "
                f"PRC latest: {trends.get('prc', {}).get('latest', 0)}"
            )
        for cyc in (rl.get("cycle_log") or [])[-3:]:
            pdf.bullet(f"Cycle {cyc.get('cycle')}: corr={cyc.get('top_correlation')} useful={cyc.get('useful_findings_so_far')}")

    pdf.section_title("3. Token Budget (Final)")
    pdf.simple_table(
        ["Metric", "Value"],
        [
            ["Max tokens", str(budget.get("max_tokens", 0)) + (" (unlimited)" if budget.get("unlimited") else "")],
            ["Max turns", str(result.get("summary", {}).get("max_turns", 0))],
            ["Stop ratio", f"{budget.get('stop_ratio', 0):.2f}"],
            ["Stop threshold", str(budget.get("stop_threshold", ""))],
            ["Tokens used", str(budget.get("tokens_used", ""))],
            ["Tokens remaining", str(budget.get("tokens_remaining", ""))],
            ["Briefing reserve", str(budget.get("briefing_reserve", ""))],
        ],
        col_widths=[60, 120],
    )

    pdf.section_title("4. Useful Findings (Actionable)")
    useful = result.get("useful_findings", [])
    if useful:
        for u in useful:
            pdf.bullet(f"[{u.get('category')}] {u.get('title')} (severity {u.get('severity')})")
            pdf.body_text(u.get("hypothesis", ""))
            for insight in u.get("actionable_insights", [])[:4]:
                pdf.bullet(insight)
            signals = u.get("signals", [])
            if signals:
                pdf.body_text(f"Signals: {', '.join(signals)}")
    else:
        pdf.body_text("No actionable useful findings synthesized.")

    pdf.section_title("5. Other Discoveries")
    discoveries = result.get("discoveries", [])
    if discoveries:
        for d in discoveries:
            pdf.bullet(f"[{d.get('discovery_id')}] {d.get('title')} (severity {d.get('severity')})")
    else:
        pdf.body_text("No secondary discoveries.")

    pdf.section_title("6. Web Intel Fetched")
    web = result.get("web_intel", [])
    if web:
        for w in web[:6]:
            pdf.bullet(f"{w.get('id')}: {w.get('url', '')[:70]}")
            pdf.body_text((w.get("snippet") or "")[:250])
    else:
        pdf.body_text("No web intel fetched.")

    pdf.section_title("7. Sedona ADS-B Snapshot (KSEZ)")
    adsb = result.get("sedona_adsb") or {}
    pdf.simple_table(
        ["Field", "Value"],
        [
            ["Aircraft in bbox", str(adsb.get("aircraft_count", "N/A"))],
            ["Low altitude (<8000ft)", str(adsb.get("low_altitude_under_8000ft", "N/A"))],
            ["Non-GA callsigns", str(adsb.get("non_ga_callsigns", "N/A"))],
            ["Elevated vs baseline", str(adsb.get("elevated_vs_baseline", "N/A"))],
            ["Source", str(adsb.get("source", "OpenSky"))],
        ],
        col_widths=[55, 125],
    )

    pdf.section_title("8. SESP Expanded Terms (Top)")
    terms = result.get("expanded_terms", [])[:10]
    if terms:
        rows = [[t.get("term", ""), str(t.get("score", "")), t.get("reason", "")[:50]] for t in terms]
        pdf.simple_table(["Term", "Score", "Reason"], rows, col_widths=[35, 20, 125])
    else:
        pdf.body_text("No expansion terms recorded.")

    pdf.section_title("9. Memory Hits")
    memory = result.get("memory_hits", [])
    if memory:
        for m in memory[:5]:
            raw = m.get("summary") or m.get("content", "")
            if isinstance(raw, dict):
                import json
                text = json.dumps(raw, default=str)[:200]
            else:
                text = str(raw)[:200]
            pdf.bullet(f"[{m.get('source')}] {text}")
    else:
        pdf.body_text("No memory hits.")

    pdf.section_title("10. Coupled Anomalies")
    coupled = result.get("coupled_anomalies", [])
    if coupled:
        for c in coupled:
            pdf.bullet(f"{c.get('coupling_id')}: {c.get('hypothesis', '')[:180]}")
    else:
        pdf.body_text("No coupled anomalies detected this mission.")

    pdf.section_title("11. Turn Log")
    turns = result.get("turn_log", [])
    rows = []
    for t in turns:
        findings = ", ".join(f["type"] for f in t.get("findings", []))
        rows.append([
            str(t.get("turn")),
            str(t.get("tokens_charged")),
            "YES" if t.get("discovery_made") else "no",
            findings[:60],
        ])
    if rows:
        pdf.simple_table(["Turn", "Tokens", "Discovery", "Actions"], rows, col_widths=[18, 22, 28, 112])

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, _ascii(
        "SHADOW agent operates as an overlay analyst. Findings are pattern-discovery "
        "outputs from public telemetry and SESP keyword/memory layers. Not operational intelligence."
    ))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    return out_path