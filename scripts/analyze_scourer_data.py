#!/usr/bin/env python3
"""Extract paper-ready analysis artifacts from scourer JSON data.

Produces:
- Convergence curves (findings per pass, cumulative)
- Severity distributions per vendor
- Category taxonomy per vendor
- Model provenance (which model found what)
- Cost estimates
- Cross-vendor comparison tables

Output: data/analysis/ directory with JSON + markdown summaries.
"""

import json
import sys
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "scourer"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "analysis"


def load_stack(filename: str) -> dict:
    path = DATA_DIR / filename
    with open(path) as f:
        return json.load(f)


def extract_per_pass_stats(stack: dict) -> list[dict]:
    """Per-pass: model, finding count, cumulative count, categories, severities."""
    rows = []
    cumulative = 0
    for report in stack["reports"]:
        findings = report["findings"]
        n = len(findings)
        cumulative += n
        severities = Counter(f["severity_guess"].lower() for f in findings)
        categories = Counter(f["category"] for f in findings)
        rows.append({
            "pass": report["pass_number"],
            "model": report.get("model", "unknown"),
            "findings": n,
            "cumulative": cumulative,
            "should_continue": report.get("should_send_another", False),
            "severities": dict(severities),
            "categories": dict(categories),
        })
    return rows


def severity_distribution(stack: dict) -> dict[str, int]:
    """Aggregate severity counts across all passes."""
    counts: Counter = Counter()
    for report in stack["reports"]:
        for f in report["findings"]:
            counts[f["severity_guess"].lower()] += 1
    return dict(counts)


def category_taxonomy(stack: dict) -> dict[str, int]:
    """All categories used, with counts."""
    counts: Counter = Counter()
    for report in stack["reports"]:
        for f in report["findings"]:
            counts[f["category"]] += 1
    return dict(counts.most_common())


def model_provenance(stack: dict) -> dict[str, list[str]]:
    """Which model found which categories of findings."""
    provenance: dict[str, list[str]] = {}
    for report in stack["reports"]:
        model = report.get("model", "unknown")
        categories = set()
        for f in report["findings"]:
            categories.add(f["category"])
        provenance[model] = sorted(categories)
    return provenance


def worst_severity(stack: dict) -> str:
    """Return the worst severity found across all findings."""
    order = ["curious", "notable", "concerning", "alarming", "critical"]
    worst_idx = 0
    for report in stack["reports"]:
        for f in report["findings"]:
            sev = f["severity_guess"].lower()
            if sev in order:
                idx = order.index(sev)
                worst_idx = max(worst_idx, idx)
    return order[worst_idx]


# Cost estimates based on OpenRouter pricing (approximate, session 9 data)
# These are rough — actual costs depend on input/output token splits
COST_ESTIMATES = {
    "claude-opus-4-6": 0.015,       # per-call estimate (subscription, amortized)
    "google/gemini-2.5-flash-preview": 0.003,
    "moonshotai/kimi-k2.5": 0.031,
    "deepseek/deepseek-r1": 0.008,
    "deepseek/deepseek-v3.2": 0.004,
    "x-ai/grok-4.1-fast": 0.006,
    "meta-llama/llama-4-maverick": 0.003,
    "minimax/minimax-m1": 0.005,
    "qwen/qwen3-235b-a22b-2507": 0.004,
    "z-ai/glm-4.7": 0.003,
    "openai/gpt-4.1-mini": 0.003,
}


def estimate_cost(stack: dict) -> dict:
    """Rough cost estimate per model and total."""
    costs = {}
    total = 0.0
    for report in stack["reports"]:
        model = report.get("model", "unknown")
        est = COST_ESTIMATES.get(model, 0.005)  # default fallback
        costs[model] = est
        total += est
    return {"per_model": costs, "total": round(total, 4)}


def generate_markdown_table(vendors: dict[str, dict]) -> str:
    """Generate the cross-vendor comparison table."""
    lines = []
    lines.append("| Metric | Claude Code | Codex | Gemini CLI |")
    lines.append("|--------|-------------|-------|------------|")

    for label, key in [
        ("Lines", "lines"),
        ("Characters", "chars"),
        ("Total findings", "total_findings"),
        ("Passes to convergence", "passes"),
        ("Models used", "models_used"),
        ("Worst severity", "worst_severity"),
        ("Curious", "curious"),
        ("Notable", "notable"),
        ("Concerning", "concerning"),
        ("Alarming", "alarming"),
        ("Critical", "critical"),
        ("Estimated cost", "cost"),
    ]:
        row = f"| {label} |"
        for vendor in ["claude_code", "codex", "gemini_cli"]:
            val = vendors[vendor].get(key, 0)
            if key == "cost":
                row += f" ${val:.3f} |"
            else:
                row += f" {val} |"
        lines.append(row)

    return "\n".join(lines)


def analyze_vendor(name: str, filename: str, lines: int, chars: int) -> dict:
    """Full analysis of one vendor's scourer data."""
    stack = load_stack(filename)
    per_pass = extract_per_pass_stats(stack)
    severity = severity_distribution(stack)
    categories = category_taxonomy(stack)
    provenance = model_provenance(stack)
    cost = estimate_cost(stack)
    worst = worst_severity(stack)

    total_findings = sum(r["findings"] for r in per_pass)
    passes = len(per_pass)
    models = [r["model"] for r in per_pass]

    return {
        "name": name,
        "filename": filename,
        "lines": lines,
        "chars": f"{chars // 1000}K",
        "total_findings": total_findings,
        "passes": passes,
        "models_used": passes,  # one model per pass
        "models": models,
        "worst_severity": worst,
        "per_pass": per_pass,
        "severity": severity,
        "curious": severity.get("curious", 0),
        "notable": severity.get("notable", 0),
        "concerning": severity.get("concerning", 0),
        "alarming": severity.get("alarming", 0),
        "critical": severity.get("critical", 0),
        "categories": categories,
        "provenance": provenance,
        "cost": cost["total"],
        "cost_breakdown": cost["per_model"],
    }


def convergence_table(vendor: dict) -> str:
    """Markdown table showing findings per pass."""
    lines = []
    lines.append(f"### {vendor['name']} — Convergence")
    lines.append("")
    lines.append("| Pass | Model | New | Cumulative | Continue? |")
    lines.append("|------|-------|-----|------------|-----------|")
    for p in vendor["per_pass"]:
        model_short = p["model"].split("/")[-1] if "/" in p["model"] else p["model"]
        cont = "yes" if p["should_continue"] else "**no**"
        lines.append(
            f"| {p['pass']} | {model_short} | {p['findings']} "
            f"| {p['cumulative']} | {cont} |"
        )
    lines.append("")
    return "\n".join(lines)


def provenance_table(vendor: dict) -> str:
    """Markdown table showing what each model found."""
    lines = []
    lines.append(f"### {vendor['name']} — Model Provenance")
    lines.append("")
    lines.append("| Model | Categories Found |")
    lines.append("|-------|-----------------|")
    for model, cats in vendor["provenance"].items():
        model_short = model.split("/")[-1] if "/" in model else model
        lines.append(f"| {model_short} | {', '.join(cats)} |")
    lines.append("")
    return "\n".join(lines)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Analyze all three vendors
    vendors = {}

    vendors["claude_code"] = analyze_vendor(
        "Claude Code v2.1.50", "10pass_gptoss.json",
        lines=1490, chars=78000,
    )
    vendors["codex"] = analyze_vendor(
        "Codex GPT-5.2", "codex_pass2_grok.json",
        lines=298, chars=22000,
    )
    vendors["gemini_cli"] = analyze_vendor(
        "Gemini CLI", "gemini_pass3_glm.json",
        lines=245, chars=27000,
    )

    # Write raw analysis JSON
    with open(OUTPUT_DIR / "cross_vendor_analysis.json", "w") as f:
        json.dump(vendors, f, indent=2, default=str)

    # Write markdown report
    report_lines = []
    report_lines.append("# Cross-Vendor Scourer Analysis")
    report_lines.append("")
    report_lines.append("Generated from scourer convergence data.")
    report_lines.append("")

    # Main comparison table
    report_lines.append("## Summary")
    report_lines.append("")
    report_lines.append(generate_markdown_table(vendors))
    report_lines.append("")

    # Total cost
    total_cost = sum(v["cost"] for v in vendors.values())
    report_lines.append(f"**Total estimated API cost: ${total_cost:.3f}**")
    report_lines.append("")

    # Convergence tables
    report_lines.append("## Convergence")
    report_lines.append("")
    for v in vendors.values():
        report_lines.append(convergence_table(v))

    # Severity distribution
    report_lines.append("## Severity Distribution")
    report_lines.append("")
    report_lines.append("| Severity | Claude Code | Codex | Gemini CLI |")
    report_lines.append("|----------|-------------|-------|------------|")
    for sev in ["curious", "notable", "concerning", "alarming", "critical"]:
        row = f"| {sev} |"
        for key in ["claude_code", "codex", "gemini_cli"]:
            row += f" {vendors[key]['severity'].get(sev, 0)} |"
        report_lines.append(row)
    report_lines.append("")

    # Model provenance
    report_lines.append("## Model Provenance")
    report_lines.append("")
    for v in vendors.values():
        report_lines.append(provenance_table(v))

    # Category counts
    report_lines.append("## Category Taxonomy")
    report_lines.append("")
    for v in vendors.values():
        report_lines.append(f"### {v['name']} ({len(v['categories'])} categories)")
        report_lines.append("")
        for cat, count in sorted(v["categories"].items(), key=lambda x: -x[1]):
            report_lines.append(f"- {cat}: {count}")
        report_lines.append("")

    report_text = "\n".join(report_lines)
    with open(OUTPUT_DIR / "cross_vendor_report.md", "w") as f:
        f.write(report_text)

    print(report_text)
    print(f"\n--- Files written to {OUTPUT_DIR}/ ---")


if __name__ == "__main__":
    main()
