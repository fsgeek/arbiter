# Independent Review Task: Phase 1 Pairwise Ablation Script

## What to review

`scripts/run_phase1.py` — a new script for running Phase 1 of the ablation study.
It was written by Claude Opus 4.6 (session 16) and has NOT been independently reviewed.

## Context

Phase 0 (`scripts/run_phase0.py`) removes one block at a time from a system prompt
and measures behavioral change. Phase 1 uses NIST covering arrays to test pairwise
combinations — removing multiple blocks simultaneously to detect interaction effects.

Phase 0 has been run 3 times successfully on Haiku with consistent results.

## Review criteria

### 1. API correctness
- Does `run_phase1.py` correctly call `build_phase1_configs()`? Check the actual
  signature in `src/arbiter/ablation/configuration.py`.
- Does `build_baseline_config()` get the right arguments?
- Compare against `run_phase0.py` which is known-working.

### 2. Covering array → tensor path
- Phase 0 configs have exactly 1 absent block each. Phase 1 configs have many.
- Does `AblationTensor.from_ablation_run()` in `src/arbiter/ablation/tensor.py`
  handle configs with multiple absent blocks? Or is it hardcoded for Phase 0?
- This is the most likely failure point.

### 3. Probe execution with absent target blocks
- The battery has 22 probes, each targeting a specific block.
- In Phase 1, a probe's target block may be absent from some configs.
- Does `AblationRunner.run_phase()` in `src/arbiter/ablation/runner.py` still
  run that probe? What happens when it does? Is that the correct behavior?

### 4. Analysis functions
- `detect_suppression()`, `detect_competition_patterns()`, `classify_blocks()`
  in `src/arbiter/ablation/analysis.py` — were they designed for Phase 1 data
  or only Phase 0? Will they produce meaningful results?

### 5. Edge cases
- Row 0 of the covering array removes ALL 22 free blocks. Will the runner,
  probe scoring, and tensor assembly handle a prompt with zero behavioral blocks?
- Row 1 removes NONE (identical to baseline). Redundant but should not crash.

### 6. Test coverage
- The existing ablation tests in `tests/test_ablation_*.py` were written by the
  same instance that wrote the code (same commit: 9a86623). They have not been
  independently reviewed. If you find bugs in the tests, report them.

## Files to read

- `scripts/run_phase1.py` (the file under review)
- `scripts/run_phase0.py` (working reference)
- `src/arbiter/ablation/configuration.py` (config builders)
- `src/arbiter/ablation/covering_array.py` (array generation)
- `src/arbiter/ablation/runner.py` (execution engine)
- `src/arbiter/ablation/tensor.py` (result assembly — most likely failure point)
- `src/arbiter/ablation/analysis.py` (analysis functions)
- `src/arbiter/ablation/battery.py` (probe battery)
- `src/arbiter/ablation/probe.py` (probe scoring)

## Output

Report bugs, incorrect assumptions, and missing edge case handling.
If the tensor assembly path won't work for Phase 1, describe exactly what
needs to change and why.
