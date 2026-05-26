"""Cross-run theme aggregation (focusgroup report themes).

Walks runs/ and produces an aggregate report:
- clustered open-ended feedback
- failures segmented by persona axis
- diff against previous report (regressions)
- always-fail vs sometimes-fail per requirement

Cluster strategy: cheap keyword bucketing by default. Set
FOCUSGROUP_THEMES_MODE=anthropic, claude, or codex for LLM-based clustering.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from runner import codex_client
from runner.loader import load_personas_dir
from runner.transcript import read_state


def _iter_runs(runs_dir: Path, since: datetime | None):
    if not runs_dir.exists():
        return
    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        state = read_state(run_dir / "state.json")
        if not state:
            continue
        started = state.get("started_at")
        if since and started and datetime.fromtimestamp(started) < since:
            continue
        result_path = run_dir / "result.json"
        results = []
        if result_path.exists():
            results = json.loads(result_path.read_text())
        yield run_dir, state, results


_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "to", "of", "in", "on", "at", "for", "with", "as", "this", "that",
    "it", "its", "be", "by", "from", "i", "me", "my", "you", "your",
}


def _keyword_cluster(texts: list[str], top_k: int = 8) -> list[tuple[str, int]]:
    bag = Counter()
    for t in texts:
        for word in re.findall(r"[a-zA-Z]{4,}", t.lower()):
            if word in _STOPWORDS:
                continue
            bag[word] += 1
    return bag.most_common(top_k)


def _anthropic_cluster(texts: list[str]) -> str:
    try:
        import anthropic
    except ImportError:
        return ""
    if not texts:
        return ""
    client = anthropic.Anthropic()
    prompt = _cluster_prompt(texts)
    model = os.environ.get("FOCUSGROUP_THEMES_MODEL", "claude-sonnet-4-6")
    msg = client.messages.create(
        model=model, max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if hasattr(b, "text"))


def _codex_cluster(texts: list[str]) -> str:
    if not texts:
        return ""
    prompt = _cluster_prompt(texts)
    model = os.environ.get("FOCUSGROUP_THEMES_MODEL") or os.environ.get("FOCUSGROUP_CODEX_MODEL")
    return codex_client.complete_text(prompt, model=model)


def _cluster_prompt(texts: list[str]) -> str:
    return (
        "You are synthesizing open-ended feedback from a series of user tests. "
        "Below are quotes from different test participants. Identify 3-6 RECURRING THEMES. "
        "For each theme, give a short label and quote 1-2 example snippets. "
        "Be concise. No preamble.\n\n"
        + "\n\n---\n\n".join(texts[:50])
    )


def _llm_cluster(texts: list[str], mode: str) -> str:
    if mode == "codex":
        return _codex_cluster(texts)
    if mode in ("anthropic", "claude"):
        return _anthropic_cluster(texts)
    return ""


def report(project_dir: Path, since: datetime | None = None) -> str:
    runs_dir = project_dir / "runs"
    personas = load_personas_dir(project_dir / "personas")

    pain_points: list[str] = []
    stuck_points: list[str] = []
    one_changes: list[str] = []
    per_req_pass: dict[str, list[bool]] = defaultdict(list)
    per_persona_per_req: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))

    total_runs = 0
    for run_dir, state, results in _iter_runs(runs_dir, since):
        total_runs += 1
        debrief = state.get("debrief") or {}
        if debrief.get("pain_points"):
            pain_points.append(str(debrief["pain_points"]))
        if debrief.get("stuck_points"):
            stuck_points.append(str(debrief["stuck_points"]))
        if debrief.get("one_change"):
            one_changes.append(str(debrief["one_change"]))
        for r in results:
            per_req_pass[r["requirement_id"]].append(r["passed"])
            persona_id = state.get("persona_id", "unknown")
            per_persona_per_req[persona_id][r["requirement_id"]].append(r["passed"])

    out: list[str] = []
    out.append(f"# focusgroup themes report")
    out.append("")
    out.append(f"_Generated {time.strftime('%Y-%m-%d %H:%M:%S')}_")
    out.append("")
    out.append(f"**Runs analyzed:** {total_runs}")
    if since:
        out.append(f"**Since:** {since.isoformat()}")
    out.append("")

    # Per-requirement summary
    out.append("## Requirements")
    out.append("")
    out.append("| Requirement | Pass rate | Pattern |")
    out.append("|---|---|---|")
    for rid in sorted(per_req_pass):
        passes = per_req_pass[rid]
        rate = sum(passes) / len(passes) if passes else 0.0
        if rate == 1.0:
            pattern = "always passes"
        elif rate == 0.0:
            pattern = "always fails"
        elif rate < 0.5:
            pattern = "fails most of the time"
        else:
            pattern = "sometimes fails"
        out.append(f"| {rid} | {rate*100:.0f}% ({sum(passes)}/{len(passes)}) | {pattern} |")
    out.append("")

    # Failures segmented by persona axis
    out.append("## Failures segmented by persona")
    out.append("")
    out.append("| Persona | Requirement | Pass rate |")
    out.append("|---|---|---|")
    for pid in sorted(per_persona_per_req):
        for rid, passes in sorted(per_persona_per_req[pid].items()):
            rate = sum(passes) / len(passes) if passes else 0.0
            if rate < 1.0:
                out.append(f"| {pid} | {rid} | {rate*100:.0f}% ({sum(passes)}/{len(passes)}) |")
    out.append("")

    # Themes
    mode = os.environ.get("FOCUSGROUP_THEMES_MODE", "keyword")
    out.append("## Themes from open-ended feedback")
    out.append("")
    if mode in ("anthropic", "claude", "codex"):
        out.append("### Pain points")
        out.append(_llm_cluster(pain_points, mode) or "_(no themes extracted)_")
        out.append("")
        out.append("### Stuck points")
        out.append(_llm_cluster(stuck_points, mode) or "_(no themes extracted)_")
        out.append("")
        out.append("### What participants would change")
        out.append(_llm_cluster(one_changes, mode) or "_(no themes extracted)_")
        out.append("")
    else:
        for label, texts in (
            ("Pain points", pain_points),
            ("Stuck points", stuck_points),
            ("What participants would change", one_changes),
        ):
            out.append(f"### {label}")
            kw = _keyword_cluster(texts)
            if not kw:
                out.append("_(no feedback)_")
            else:
                out.append("Top keywords: " + ", ".join(f"`{w}` (×{n})" for w, n in kw))
            out.append("")

    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="focusgroup-themes")
    p.add_argument("--project-dir", default=".")
    p.add_argument("--since", help="ISO-8601 date; runs before this are excluded")
    p.add_argument("--out", help="output file (default: reports/<ts>.md)")
    args = p.parse_args(argv)

    project_dir = Path(args.project_dir).resolve()
    since = datetime.fromisoformat(args.since) if args.since else None
    text = report(project_dir, since)

    if args.out:
        out_path = Path(args.out)
    else:
        reports_dir = project_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        out_path = reports_dir / f"{time.strftime('%Y%m%dT%H%M%S')}.md"
    out_path.write_text(text)
    print(f"Wrote {out_path}")
    print()
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
