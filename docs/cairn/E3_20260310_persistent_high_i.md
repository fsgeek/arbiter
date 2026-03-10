# E3 — Persistent-High-I Pilot (Run 1)

Date: 2026-03-10  
Model/provider: `openai/gpt-4o-mini` via OpenRouter  
Pilot budget: 10 cases x 2 passes

## Objective

Detect whether any cells satisfy a bounded persistent-high-I criterion.

## Criterion Used

- `tau_i = 0.60`
- `epsilon = 0.03`
- pass count = 2

Cell is persistent-high-I if:
- it appears in all passes,
- all pass values satisfy `I >= tau_i`,
- `max(I)-min(I) < epsilon`.

## Results

- Evaluated keys (all passes): 10
- Persistent-high-I keys: 1
- Persistent ratio: 10.00%
- Rule/tier map:
  - `scope-overlap-redundancy | Tier.system->Tier.system`: 1

Parseability in this pilot:
- JSON parse fail rate: 0.00%
- Optional-channel rates: 95%+ for `t/i/f`, `evidence_quality`, `declared_losses`

## Interpretation

Pilot evidence supports non-zero persistent-high-I regions, but this is not yet a full E3 confirmation because canon/context mutation sweeps were not included.

## Next

1. Scale to larger case budget.
2. Add canon/context mutation sweeps.
3. Run second model family for stability.

## Artifacts

- `scripts/run_e3_persistent_high_i.py`
- `data/analysis/e3_persistent_high_i_report.json`
- `data/analysis/e3_persistent_high_i_report.md`
- `docs/cairn/HC-20260310-persistent-high-i-pilot-v1.md`
