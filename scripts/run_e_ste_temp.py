#!/usr/bin/env python3
"""E-STE follow-on round (declared in prereg_e_ste.md deviations before running): the commit-restrictions
probe ONLY, Haiku, all 4 variants x 4 languages, 10 trials at temperature 0.7. Purpose: the collapse
cells in the main run are 3 deterministic trials at temperature 0; this measures whether they are
stable behaviours or single observations. Output: data/ablation/e_ste_temp/."""
from __future__ import annotations
import argparse, asyncio, statistics, sys, uuid
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src")); sys.path.insert(0, str(project_root / "scripts"))
import run_fragility_experiments as rfe  # noqa: E402
import run_e_ste as ste  # noqa: E402
from arbiter.ablation.battery import load_battery  # noqa: E402
from arbiter.ablation.configuration import build_baseline_config  # noqa: E402
from arbiter.ablation.runner import AblationRun, AblationRunner, save_run  # noqa: E402
from arbiter.llm_caller import LLMCaller  # noqa: E402

COMMIT = "probe-commit-restrictions-01"

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--model", default="haiku"); ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--temperature", type=float, default=0.7); ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--probes", default="commit", choices=["commit", "sampled"],
                    help="commit = the target probe only (round 2); sampled = target + the 6 sealed controls (E-STE-S)")
    ap.add_argument("--experiment", default="e-ste-temp")
    a = ap.parse_args()
    battery = load_battery(project_root / "data/ablation/phase0_battery.json")
    keep = {COMMIT}
    if a.probes == "sampled":
        import json as _json
        keep |= set(_json.load(open(project_root / "data/ablation/e_ste_sampled_controls.json")))
    battery.probes = [p for p in battery.probes if p.id in keep]
    assert len(battery.probes) == len(keep)
    out = project_root / ("data/ablation/e_ste_temp" if a.experiment == "e-ste-temp" else f"data/ablation/{a.experiment.replace('-', '_')}")
    out.mkdir(parents=True, exist_ok=True)
    model_id = ste.MODEL_MAP[a.model]
    for v in ste.VARIANTS:
        for lang in rfe.LANGUAGES:
            corpus = rfe.load_corpus(rfe.corpus_path_for_lang(lang))
            if ste.VARIANTS[v] is not None:
                corpus = rfe.modify_corpus_block(corpus, ste.BLOCK, ste.VARIANTS[v][lang])
            constrained = [b.id for b in corpus.blocks if b.id not in rfe.FREE_BLOCKS]
            config = build_baseline_config(corpus, rfe.FREE_BLOCKS, constrained)
            run = AblationRun(id=f"{a.experiment}-{lang}-{a.model}-{v}-{uuid.uuid4().hex[:8]}", configs=[config], battery=battery,
                              models=[model_id], trials_per_probe=a.trials, temperature=a.temperature,
                              metadata={"experiment": a.experiment, "language": lang, "model": a.model, "model_id": model_id, "variant": v})
            runner = AblationRunner(caller=LLMCaller(rfe.make_client(a.experiment), model_id))
            print(f"{v} {lang} ...", flush=True)
            asyncio.run(runner.run_phase(run, "baseline", corpus=corpus, concurrency=a.concurrency))
            save_run(run, str(out / f"run_{run.id}.json"))
            sc = [r.score for r in run.results if r.score is not None]
            print(f"  n={len(run.results)} mean={statistics.mean(sc) if sc else None:.3f} scores={sc}", flush=True)

if __name__ == "__main__":
    main()
