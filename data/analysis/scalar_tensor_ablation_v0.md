# Scalar vs Tensor Ablation (v0)

Manifest: `docs/cairn/benchmark_v0_manifest_20260310.json`

## Real Structural Slice

- Compared: 327
- Decision differences: 0
- Discrimination rate: 0.00%

## Synthetic Collapse Slice

- Compared: 6
- Decision differences: 3
- Discrimination rate: 50.00%

## Transition Counts (synthetic)

- reject->reject: 1
- rewrite->clarify: 3
- rewrite->rewrite: 2

## Notes

- Real slice uses structural analysis output over frozen prompt corpus.
- Synthetic slice stress-tests scalar-collapse conditions with controlled fixtures.
- This is a baseline harness for future evaluator-native declared-loss experiments.