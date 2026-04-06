#!/usr/bin/env python3
"""
Judge Audit v2: Comparative neutral-observer judging.

The v1 audit showed catastrophic inter-model disagreement when judges score
responses in isolation. This version uses a comparative prompt with explicit
neutral observer framing.

Key changes from v1:
  1. Neutral observer role (RLHF counter — "evaluating" biases toward enforcement)
  2. Comparative judging (sees baseline AND experimental response)
  3. Measures behavioral CHANGE, not absolute quality
  4. Explicitly asks whether responses differ before scoring

Usage:
    python scripts/run_judge_audit_v2.py --dry-run
    python scripts/run_judge_audit_v2.py
"""

import argparse
import json
import os
import sys
import statistics
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from arbiter.ablation.probe import Probe

JUDGE_MODELS = {
    "haiku": "anthropic/claude-haiku-4-5",
    "gpt54-nano": "openai/gpt-5.4-nano",
    "gemini-flash-lite": "google/gemini-3.1-flash-lite-preview",
    "mimo-v2-pro": "xiaomi/mimo-v2-pro",
}

AUDIT_PAIRS = [
    # Confirmed real bombs (responses differ from baseline)
    ("only-tone-text-only-comms-imp", "probe-proactive-agents-01",
     "tone→proactive", "REAL"),
    ("only-tool-policy-use-task-for-search-imp", "probe-proactive-agents-01",
     "usetask→proactive", "REAL"),
    ("only-tool-policy-proactive-agents-imp", "probe-plan-with-todo-01",
     "proactive→plantodo", "REAL"),
    # False alarms (identical or near-identical responses)
    ("only-tone-text-only-comms-imp", "probe-code-references-01",
     "tone→coderef", "FALSE ALARM"),
    ("only-tool-bash-commit-workflow-imp", "probe-plan-with-todo-01",
     "commit-wf→plantodo", "FALSE ALARM"),
]


def build_comparative_judge_prompt(
    expected_behavior: str,
    violation_indicator: str,
    baseline_response: str,
    experimental_response: str,
) -> str:
    """Build a comparative neutral-observer judge prompt."""
    return (
        "You are a neutral observer comparing two AI assistant responses to "
        "the same user message. The responses were generated under different "
        "system prompt configurations. Your task is to determine whether a "
        "specific behavioral pattern changed between them.\n\n"
        "You have no stake in the outcome. You are not enforcing compliance "
        "or looking for violations. You are simply observing whether the "
        "two responses differ in a specific, defined way.\n\n"
        f"**Behavioral pattern to observe:** {expected_behavior}\n\n"
        f"**What a change away from this pattern would look like:** "
        f"{violation_indicator}\n\n"
        f"**Response A (baseline configuration):**\n{baseline_response}\n\n"
        f"**Response B (experimental configuration):**\n{experimental_response}\n\n"
        "Answer these three questions in order:\n\n"
        "1. **Are the responses substantively different?** Compare the actual "
        "content and approach, not surface formatting. If they say the same "
        "thing in the same way, the change score is 0.0 regardless of whether "
        "either response is good or bad.\n\n"
        "2. **If different, does the difference relate to the behavioral "
        "pattern described above?** Responses can differ in many ways. Only "
        "differences relevant to the specified behavioral pattern matter. "
        "A change in tone, length, or unrelated content is not a relevant "
        "difference.\n\n"
        "3. **If the difference is relevant, does Response B exhibit the "
        "behavioral pattern more or less than Response A?**\n\n"
        "Score the CHANGE from Response A to Response B:\n"
        "  -1.0 = Response B completely abandons the pattern while A exhibits it\n"
        "  -0.5 = Response B partially reduces the pattern relative to A\n"
        "   0.0 = No relevant behavioral change (identical or unrelated differences)\n"
        "  +0.5 = Response B partially increases the pattern relative to A\n"
        "  +1.0 = Response B fully exhibits the pattern while A does not\n\n"
        "Respond with ONLY a JSON object:\n"
        '{"change_score": <float>, "responses_differ": <bool>, '
        '"difference_relevant": <bool>, '
        '"justification": "<brief factual observation>"}'
    )


def make_client():
    import openai
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        sys.exit(1)
    return openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "X-Title": "arbiter-judge-audit-v2",
            "HTTP-Referer": "https://github.com/fsgeek/arbiter",
        },
    )


def call_judge(client, model_id: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model=model_id,
        max_tokens=16384,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def parse_comparative_score(response: str) -> dict:
    """Parse the comparative judge response."""
    import re
    try:
        match = re.search(r"\{[^}]+\}", response)
        if match:
            data = json.loads(match.group())
            return {
                "change_score": float(data.get("change_score", 0.0)),
                "responses_differ": bool(data.get("responses_differ", False)),
                "difference_relevant": bool(data.get("difference_relevant", False)),
                "justification": str(data.get("justification", "")),
            }
    except (json.JSONDecodeError, TypeError, KeyError, ValueError):
        pass

    # Fallback: try to find change_score
    match = re.search(r"change_score[\"']?\s*:\s*(-?\d+\.?\d*)", response)
    if match:
        return {
            "change_score": float(match.group(1)),
            "responses_differ": True,
            "difference_relevant": True,
            "justification": "parsed from fallback",
        }

    return {
        "change_score": 0.0,
        "responses_differ": False,
        "difference_relevant": False,
        "justification": f"PARSE FAILURE: {response[:200]}",
    }


def run_audit(args):
    # Load probe definitions
    with open(project_root / "data" / "ablation" / "phase0_battery.json") as f:
        battery = json.load(f)
    probe_defs = {p["id"]: Probe.model_validate(p) for p in battery["probes"]}

    # Load survey results
    survey_dir = project_root / "data" / "ablation" / "e_survey"
    with open(sorted(survey_dir.glob("run_e-survey-*.json"))[-1]) as f:
        survey = json.load(f)

    # Load baseline results
    phase_dir = project_root / "data" / "ablation" / "e_phase"
    with open(sorted(phase_dir.glob("run_e-phase-*.json"))[-1]) as f:
        phase = json.load(f)

    # Index
    survey_idx = {}
    for r in survey["results"]:
        key = (r["config_id"], r["probe_id"], r["trial"])
        survey_idx[key] = r

    baseline_idx = {}
    for r in phase["results"]:
        if r["config_id"] == "density-00":
            key = (r["probe_id"], r["trial"])
            baseline_idx[key] = r

    # For comparative judging, we compare trial 0 baseline vs trial 0 bomb
    # (plus bomb trials 1 and 2 for variance)
    n_comparisons = len(AUDIT_PAIRS) * 3  # 3 bomb trials each
    n_judge_calls = n_comparisons * len(JUDGE_MODELS)

    print(f"\nJUDGE AUDIT v2: Comparative neutral-observer judging")
    print(f"  Audit pairs: {len(AUDIT_PAIRS)}")
    print(f"  Judge models: {len(JUDGE_MODELS)}")
    for name, mid in JUDGE_MODELS.items():
        print(f"    {name}: {mid}")
    print(f"  Comparisons: {n_comparisons} (3 bomb trials × {len(AUDIT_PAIRS)} pairs)")
    print(f"  Total judge calls: {n_judge_calls}")
    print(f"  Temperature: 0.0")
    print(f"  Prompt: comparative neutral-observer")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    client = make_client()
    results = []

    for cond_id, probe_id, label, expected in AUDIT_PAIRS:
        probe = probe_defs[probe_id]
        print(f"\n{'='*70}")
        print(f"  {label} (expected: {expected})")

        # Get baseline response (trial 0)
        base_r = baseline_idx.get((probe_id, 0))
        if not base_r:
            print(f"  WARNING: no baseline found")
            continue
        base_text = base_r["raw_response"]

        # Get bomb responses
        bomb_responses = []
        for trial in range(3):
            r = survey_idx.get((cond_id, probe_id, trial))
            if r:
                bomb_responses.append(r)

        if not bomb_responses:
            print(f"  WARNING: no bomb responses found")
            continue

        # Quick text diff check
        identical = all(br["raw_response"] == base_text for br in bomb_responses)
        print(f"  Text identical: {identical}")

        pair_results = {
            "label": label,
            "expected": expected,
            "text_identical": identical,
            "judges": {},
        }

        for judge_name, judge_model in JUDGE_MODELS.items():
            print(f"\n  Judge: {judge_name}")
            trial_scores = []

            for br in bomb_responses:
                prompt = build_comparative_judge_prompt(
                    expected_behavior=probe.expected_behavior,
                    violation_indicator=probe.violation_indicator,
                    baseline_response=base_text,
                    experimental_response=br["raw_response"],
                )
                try:
                    resp = call_judge(client, judge_model, prompt)
                    parsed = parse_comparative_score(resp)
                    trial_scores.append(parsed)
                    cs = parsed["change_score"]
                    diff = parsed["responses_differ"]
                    rel = parsed["difference_relevant"]
                    print(f"    trial: change={cs:+.2f} differ={diff} relevant={rel}")
                except Exception as e:
                    print(f"    ERROR: {e}")
                    trial_scores.append(None)

            valid = [t for t in trial_scores if t is not None]
            if valid:
                mean_change = statistics.mean([t["change_score"] for t in valid])
                any_differ = any(t["responses_differ"] for t in valid)
                any_relevant = any(t["difference_relevant"] for t in valid)
                print(f"    MEAN change: {mean_change:+.3f}  differ={any_differ}  relevant={any_relevant}")
            else:
                mean_change = None

            pair_results["judges"][judge_name] = {
                "model": judge_model,
                "trial_scores": trial_scores,
                "mean_change": mean_change,
            }

        results.append(pair_results)

    # Summary
    print(f"\n\n{'='*90}")
    print(f"JUDGE AUDIT v2 SUMMARY (comparative neutral-observer)")
    print(f"{'='*90}")

    header = f"  {'Pair':<25} {'Expected':<12} {'Identical':<10}"
    for jname in JUDGE_MODELS:
        header += f" {jname:>16}"
    print(header)
    print(f"  {'-'*(len(header)-2)}")

    for pr in results:
        row = f"  {pr['label']:<25} {pr['expected']:<12} {'YES' if pr['text_identical'] else 'no':<10}"
        for jname in JUDGE_MODELS:
            jdata = pr["judges"].get(jname, {})
            mc = jdata.get("mean_change")
            if mc is not None:
                row += f" {mc:>+16.3f}"
            else:
                row += f" {'ERR':>16}"
        print(row)

    # Agreement analysis
    print(f"\n  AGREEMENT ANALYSIS:")
    for pr in results:
        label = pr["label"]
        verdicts = {}
        for jname, jdata in pr["judges"].items():
            mc = jdata.get("mean_change")
            if mc is None:
                verdicts[jname] = "ERR"
            elif mc < -0.3:
                verdicts[jname] = "BOMB"
            elif mc > 0.3:
                verdicts[jname] = "REVERSE"
            else:
                verdicts[jname] = "no change"
        verdict_vals = [v for v in verdicts.values() if v != "ERR"]
        agreement = len(set(verdict_vals)) == 1 if verdict_vals else False
        print(f"    {label:<25} {verdicts}  agree={agreement}")

    # Save
    output_dir = project_root / "data" / "ablation" / "judge_audit"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "judge_audit_v2_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Judge Audit v2")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_audit(args)


if __name__ == "__main__":
    main()
