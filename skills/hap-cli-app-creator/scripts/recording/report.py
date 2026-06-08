"""Markdown + HTML archival report under ``runs/<runId>/``."""
from __future__ import annotations

import html
from collections import OrderedDict
from pathlib import Path

from scripts.executor import STATUS_ERR, STATUS_OK, STATUS_SKIP, RunSummary, StepRecord

_MARK = {STATUS_OK: "✅", STATUS_ERR: "❌", STATUS_SKIP: "⏭️"}


def _mark(rec: StepRecord) -> str:
    """Three-state mark: ✅ ok / ⚠️ created-but-unfinished / ❌ not created /
    ⏭️ skipped. A failed step that still captured a ``created_id`` means the
    entity exists but configuring/publishing it failed — repairable in place.
    """
    if rec.status == STATUS_ERR and rec.created_id:
        return "⚠️"
    return _MARK.get(rec.status, "?")


def _needs_repair(records: list[StepRecord]) -> list[StepRecord]:
    """Steps the user may want to fix: anything not ok."""
    return [r for r in records if r.status != STATUS_OK]


def _group(records: list[StepRecord]) -> "OrderedDict[str, list[StepRecord]]":
    groups: "OrderedDict[str, list[StepRecord]]" = OrderedDict()
    for rec in records:
        groups.setdefault(rec.phase, []).append(rec)
    return groups


def render_markdown(summary: RunSummary, *, ts: str = "", design: str = "") -> str:
    verdict = "PASS ✅" if summary.passed else "FAIL ❌"
    lines = [
        f"# Live-Test Report — {summary.app_name or summary.run_id}",
        "",
        f"- **Verdict**: {verdict}",
        f"- **Run**: `{summary.run_id}`  ({ts})",
        f"- **Design**: `{design}`",
        f"- **App**: `{summary.app_id}`",
        f"- **Org**: `{summary.org_id}`",
        f"- **Counts**: {summary.ok} ok / {summary.err} err / {summary.skip} skip",
        "",
        "## Steps",
        "",
    ]
    for phase, recs in _group(summary.records).items():
        lines.append(f"### {phase}")
        lines.append("")
        lines.append("| | Step | Created id | ms | Detail |")
        lines.append("|---|---|---|---|---|")
        for r in recs:
            detail = (r.error or r.summary or "").replace("|", "\\|")
            lines.append(
                f"| {_mark(r)} | {r.name} | "
                f"`{r.created_id or ''}` | {r.duration_ms or ''} | "
                f"{detail} |"
            )
        lines.append("")

    # failures-to-repair section — the actionable hand-off to hap-cli-app-editor.
    failures = _needs_repair(summary.records)
    lines.append("## 需修复项 (failures to repair)")
    lines.append("")
    if not failures:
        lines.append("无失败项 ✅ —— 全部创建成功。")
        lines.append("")
    else:
        lines.append(
            "下列元素未完全建成。**在原位按真实 id 修复（用 hap-cli-app-editor），"
            "不要重跑 build。** ⚠️ = 已创建但配置/发布失败（带 id，可原位修）；"
            "❌ = 未建成；⏭️ = 因上游失败被跳过。")
        lines.append("")
        lines.append("| | Kind | Name | Id (修复目标) | Phase | 原因 |")
        lines.append("|---|---|---|---|---|---|")
        for r in failures:
            reason = (r.error or "").replace("|", "\\|")
            lines.append(
                f"| {_mark(r)} | {r.kind} | {r.name} | "
                f"`{r.created_id or ''}` | {r.phase} | {reason} |"
            )
        lines.append("")

    # resource map appendix
    lines.append("## Resource map (logical name → real id)")
    lines.append("")
    lines.append("| Kind | Name | Id |")
    lines.append("|---|---|---|")
    for r in summary.records:
        if r.status == STATUS_OK and r.created_id:
            lines.append(f"| {r.kind} | {r.name} | `{r.created_id}` |")
    lines.append("")
    return "\n".join(lines)


def render_html(summary: RunSummary, *, ts: str = "", design: str = "") -> str:
    verdict = "PASS" if summary.passed else "FAIL"
    color = "#1a7f37" if summary.passed else "#cf222e"
    rows = []
    for phase, recs in _group(summary.records).items():
        rows.append(f'<tr class="phase"><td colspan="5">{html.escape(phase)}</td></tr>')
        for r in recs:
            detail = html.escape(r.error or r.summary or "")
            rows.append(
                f"<tr class='{r.status}'><td>{_mark(r)}</td>"
                f"<td>{html.escape(r.name)}</td>"
                f"<td><code>{html.escape(r.created_id or '')}</code></td>"
                f"<td>{r.duration_ms or ''}</td>"
                f"<td>{detail}</td></tr>"
            )
    body = "\n".join(rows)
    return f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>Live-Test {html.escape(summary.app_name or summary.run_id)}</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:2rem;color:#1f2328}}
 h1{{font-size:1.3rem}}
 .verdict{{color:{color};font-weight:700}}
 table{{border-collapse:collapse;width:100%;margin-top:1rem;font-size:.9rem}}
 td,th{{border:1px solid #d0d7de;padding:.35rem .5rem;text-align:left}}
 tr.phase td{{background:#f6f8fa;font-weight:600}}
 tr.err td{{background:#ffebe9}}
 tr.skip td{{color:#8c959f}}
 code{{font-size:.85em}}
 ul{{line-height:1.6}}
</style></head><body>
<h1>Live-Test Report — {html.escape(summary.app_name or summary.run_id)}</h1>
<p class="verdict">{verdict}</p>
<ul>
 <li>Run: <code>{html.escape(summary.run_id)}</code> ({html.escape(ts)})</li>
 <li>Design: <code>{html.escape(design)}</code></li>
 <li>App: <code>{html.escape(summary.app_id or '')}</code></li>
 <li>Org: <code>{html.escape(summary.org_id)}</code></li>
 <li>Counts: {summary.ok} ok / {summary.err} err / {summary.skip} skip</li>
</ul>
<table><thead><tr><th></th><th>Step</th><th>Created id</th><th>ms</th><th>Detail</th></tr></thead>
<tbody>
{body}
</tbody></table>
</body></html>
"""


class ReportRecorder:
    """Writes ``report.md`` and ``report.html`` on finish."""

    def __init__(self, run_dir: Path, *, ts: str = "", design: str = "") -> None:
        self.run_dir = Path(run_dir)
        self.ts = ts
        self.design = design

    def on_step(self, rec: StepRecord) -> None:  # noqa: D401 — no-op per step
        pass

    def on_finish(self, summary: RunSummary) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "report.md").write_text(
            render_markdown(summary, ts=self.ts, design=self.design), encoding="utf-8"
        )
        (self.run_dir / "report.html").write_text(
            render_html(summary, ts=self.ts, design=self.design), encoding="utf-8"
        )
