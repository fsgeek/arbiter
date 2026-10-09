#!/usr/bin/env python3
"""Run one pre-registered scourer control arm (prereg_scourer_same_model_control.md).

    python scripts/run_scourer_control.py --arm same-deepseek \
        --models deepseek/deepseek-v3.2 --max-passes 10

    python scripts/run_scourer_control.py --arm permuted \
        --models m1 m2 ... m8 --max-passes 8

Persists after every pass: data/scourer/control/<arm>.json (ScourerStack),
<arm>_raw.jsonl (every raw response, usage, generation id), <arm>_log.txt.
Stop rule: three consecutive should_send_another=false, or --max-passes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from arbiter.scourer import Scourer, ScourerStack  # noqa: E402

ROOT = Path(__file__).parent.parent
PROMPT_FILE = ROOT / "docs" / "claude-code-system-prompt.md"
OUT_DIR = ROOT / "data" / "scourer" / "control"


def call_openrouter(prompt: str, model: str, pass_number: int, arm: str):
    import openai

    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
        default_headers={
            "X-Title": "arbiter-scourer-control",
            "HTTP-Referer": "https://github.com/fsgeek/arbiter",
        },
        timeout=1800,
    )
    t0 = time.time()
    resp = client.chat.completions.create(
        model=model,
        max_tokens=65536,  # identical to the original OpenRouter path
        messages=[{"role": "user", "content": prompt}],
        extra_body={
            "transforms": [],
            "route": "fallback",
            "metadata": {"label": f"{arm}-pass{pass_number}", "model": model},
        },
    )
    text = resp.choices[0].message.content or ""
    usage = resp.usage.model_dump() if resp.usage else None
    return text, {
        "generation_id": resp.id,
        "served_model": resp.model,
        "usage": usage,
        "finish_reason": resp.choices[0].finish_reason,
        "seconds": round(time.time() - t0, 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--models", nargs="+", required=True,
                    help="one model = same-model chain; N models = one per pass in order")
    ap.add_argument("--max-passes", type=int, required=True)
    ap.add_argument("--consecutive-no", type=int, default=3)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stack_path = OUT_DIR / f"{args.arm}.json"
    raw_path = OUT_DIR / f"{args.arm}_raw.jsonl"
    log_path = OUT_DIR / f"{args.arm}_log.txt"

    def log(msg: str) -> None:
        line = f"{datetime.now(timezone.utc).isoformat()} {msg}"
        print(line, flush=True)
        with open(log_path, "a") as fh:
            fh.write(line + "\n")

    prompt_text = PROMPT_FILE.read_text()
    scourer = Scourer()
    if stack_path.exists():  # resume after a crash; never re-run a completed pass
        prior = ScourerStack.model_validate_json(stack_path.read_text())
        for r in prior.reports:
            scourer.add_report(r)
        log(f"resumed {len(prior.reports)} prior pass(es)")

    log(f"arm={args.arm} models={args.models} max_passes={args.max_passes} "
        f"prompt_chars={len(prompt_text)} stop=consecutive_no>={args.consecutive_no}")

    consecutive_no = 0
    for r in scourer.stack.reports:
        consecutive_no = 0 if r.should_send_another else consecutive_no + 1

    while len(scourer.stack.reports) < args.max_passes:
        n = len(scourer.stack.reports) + 1
        model = args.models[0] if len(args.models) == 1 else args.models[n - 1]
        prompt = scourer.build_prompt(prompt_text)
        log(f"pass {n} model={model} prompt_chars={len(prompt)}")
        report = None
        for attempt in (1, 2):
            text, meta = call_openrouter(prompt, model, n, args.arm)
            rec = {"arm": args.arm, "pass": n, "attempt": attempt, "model": model,
                   "ts": datetime.now(timezone.utc).isoformat(), "meta": meta, "raw": text}
            with open(raw_path, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            try:
                report = scourer.parse_response(text, model=model)
                break
            except ValueError as e:
                log(f"pass {n} attempt {attempt} parse failure: {str(e)[:200]}")
        if report is None:
            log(f"pass {n} FAILED twice; halting arm (fail-stop)")
            sys.exit(2)
        scourer.add_report(report)
        stack_path.write_text(scourer.stack.model_dump_json(indent=2))
        consecutive_no = 0 if report.should_send_another else consecutive_no + 1
        log(f"pass {n} findings={len(report.findings)} unexplored={len(report.unexplored)} "
            f"again={report.should_send_another} consecutive_no={consecutive_no} "
            f"usage={meta['usage']} gen={meta['generation_id']}")
        if consecutive_no >= args.consecutive_no:
            log(f"stop rule met at pass {n}")
            break
    log(f"done: passes={len(scourer.stack.reports)} findings={scourer.stack.finding_count()}")


if __name__ == "__main__":
    main()
