#!/usr/bin/env python3
"""
Judge Audit: Re-score existing model outputs through multiple judge models.

The E-SURVEY results showed that 4/9 "bomb effects" were false alarms caused
by judge variance on identical model outputs. This script re-scores a set of
key outputs through multiple judge models at temperature 0.0 to:

1. Quantify inter-judge agreement
2. Determine if bomb effects are judge-model-dependent
3. Identify whether the original Haiku-judging-Haiku setup introduced bias

Usage:
    python scripts/run_judge_audit.py --dry-run
    python scripts/run_judge_audit.py
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

# Judge models to test
JUDGE_MODELS = {
    "haiku": "anthropic/claude-haiku-4-5",
    "qwen3-plus": "qwen/qwen3.6-plus-preview:free",
    "gpt54-nano": "openai/gpt-5.4-nano",
    "gemini-flash-lite": "google/gemini-3.1-flash-lite-preview",
}

# Pairs to audit: (condition_id, probe_id, label, expected_verdict)
AUDIT_PAIRS = [
    # Confirmed real bombs (responses differ from baseline)
    ("only-tone-text-only-comms-imp", "probe-proactive-agents-01",
     "tone→proactive", "REAL"),
    ("only-tool-policy-use-task-for-search-imp", "probe-proactive-agents-01",
     "usetask→proactive", "REAL"),
    ("only-tool-policy-proactive-agents-imp", "probe-plan-with-todo-01",
     "proactive→plantodo", "REAL"),
    # False alarms (identical responses, judge noise)
    ("only-tone-text-only-comms-imp", "probe-code-references-01",
     "tone→coderef", "FALSE ALARM"),
    ("only-tool-bash-commit-workflow-imp", "probe-plan-with-todo-01",
     "commit-wf→plantodo", "FALSE ALARM"),
]


def make_client(model_id: str):
    import openai
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        sys.exit(1)
    return openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "X-Title": "arbiter-judge-audit",
            "HTTP-Referer": "https://github.com/fsgeek/arbiter",
        },
    )


def call_judge(client, model_id: str, judge_prompt: str, temperature: float = 0.0) -> str:
    response = client.chat.completions.create(
        model=model_id,
        max_tokens=16384,
        temperature=temperature,
        messages=[{"role": "user", "content": judge_prompt}],
    )
    return response.choices[0].message.content


def run_audit(args):
    # Load battery for probe definitions
    battery_path = project_root / "data" / "ablation" / "phase0_battery.json"
    with open(battery_path) as f:
        battery = json.load(f)
    probe_defs = {p["id"]: Probe.model_validate(p) for p in battery["probes"]}

    # Load survey results
    survey_dir = project_root / "data" / "ablation" / "e_survey"
    survey_files = sorted(survey_dir.glob("run_e-survey-*.json"))
    with open(survey_files[-1]) as f:
        survey = json.load(f)

    # Load baseline results
    phase_dir = project_root / "data" / "ablation" / "e_phase"
    phase_files = sorted(phase_dir.glob("run_e-phase-*.json"))
    with open(phase_files[-1]) as f:
        phase = json.load(f)

    # Index results
    survey_idx = {}
    for r in survey["results"]:
        key = (r["config_id"], r["probe_id"], r["trial"])
        survey_idx[key] = r

    baseline_idx = {}
    for r in phase["results"]:
        if r["config_id"] == "density-00":
            key = (r["probe_id"], r["trial"])
            baseline_idx[key] = r

    # Count work
    # For each audit pair: 1 baseline response + 3 bomb trials = 4 responses
    # Each response scored by N judge models, 1 call each (temperature 0.0)
    n_responses = len(AUDIT_PAIRS) * 4  # baseline + 3 trials
    n_judge_calls = n_responses * len(JUDGE_MODELS)

    print(f"\nJUDGE AUDIT: Re-scoring bomb pairs through multiple judges")
    print(f"  Audit pairs: {len(AUDIT_PAIRS)}")
    print(f"  Judge models: {len(JUDGE_MODELS)}")
    for name, mid in JUDGE_MODELS.items():
        print(f"    {name}: {mid}")
    print(f"  Responses to score: {n_responses}")
    print(f"  Total judge calls: {n_judge_calls}")
    print(f"  Temperature: 0.0 (deterministic judging)")

    if args.dry_run:
        print("\n  --dry-run: stopping here.")
        return

    client = make_client("judge-audit")
    results = []

    for cond_id, probe_id, label, expected in AUDIT_PAIRS:
        probe = probe_defs[probe_id]
        print(f"\n{'='*70}")
        print(f"  {label} (expected: {expected})")

        # Get baseline response (trial 0)
        base_r = baseline_idx.get((probe_id, 0))
        if not base_r:
            print(f"  WARNING: no baseline found for {probe_id}")
            continue

        # Get bomb responses (all trials)
        bomb_responses = []
        for trial in range(3):
            r = survey_idx.get((cond_id, probe_id, trial))
            if r:
                bomb_responses.append(r)

        if not bomb_responses:
            print(f"  WARNING: no bomb responses found for {cond_id}/{probe_id}")
            continue

        # Check if responses are identical
        base_text = base_r["raw_response"]
        bomb_text = bomb_responses[0]["raw_response"]
        identical = base_text == bomb_text
        print(f"  Responses identical: {identical}")

        # Score through each judge model
        pair_results = {"label": label, "expected": expected, "identical": identical, "judges": {}}

        for judge_name, judge_model in JUDGE_MODELS.items():
            print(f"\n  Judge: {judge_name} ({judge_model})")

            # Score baseline
            judge_prompt = probe.build_judge_prompt(base_text)
            try:
                base_judge_resp = call_judge(client, judge_model, judge_prompt)
                base_score = Probe.parse_judge_score(base_judge_resp)
                print(f"    Baseline score: {base_score:.3f}")
            except Exception as e:
                print(f"    Baseline ERROR: {e}")
                base_score = None

            # Score each bomb trial
            bomb_scores = []
            for br in bomb_responses:
                judge_prompt = probe.build_judge_prompt(br["raw_response"])
                try:
                    bomb_judge_resp = call_judge(client, judge_model, judge_prompt)
                    score = Probe.parse_judge_score(bomb_judge_resp)
                    bomb_scores.append(score)
                except Exception as e:
                    print(f"    Bomb trial ERROR: {e}")
                    bomb_scores.append(None)

            valid_bombs = [s for s in bomb_scores if s is not None]
            if valid_bombs:
                bomb_mean = statistics.mean(valid_bombs)
                print(f"    Bomb scores: {valid_bombs} → mean {bomb_mean:.3f}")
                if base_score is not None:
                    delta = bomb_mean - base_score
                    print(f"    Delta: {delta:+.3f}")
            else:
                bomb_mean = None

            pair_results["judges"][judge_name] = {
                "model": judge_model,
                "baseline_score": base_score,
                "bomb_scores": bomb_scores,
                "bomb_mean": bomb_mean,
            }

        results.append(pair_results)

    # Summary table
    print(f"\n\n{'='*90}")
    print(f"JUDGE AUDIT SUMMARY")
    print(f"{'='*90}")

    header = f"  {'Pair':<25} {'Expected':<12} {'Identical':<10}"
    for jname in JUDGE_MODELS:
        header += f" {jname:>15}"
    print(header)
    print(f"  {'-'*(len(header)-2)}")

    for pr in results:
        row = f"  {pr['label']:<25} {pr['expected']:<12} {'YES' if pr['identical'] else 'no':<10}"
        for jname in JUDGE_MODELS:
            jdata = pr["judges"].get(jname, {})
            base = jdata.get("baseline_score")
            bomb = jdata.get("bomb_mean")
            if base is not None and bomb is not None:
                delta = bomb - base
                row += f" {delta:>+15.3f}"
            else:
                row += f" {'ERR':>15}"
        print(row)

    # Save results
    output_dir = project_root / "data" / "ablation" / "judge_audit"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "judge_audit_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Judge Audit")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_audit(args)


if __name__ == "__main__":
    main()
