# E2 Semantic-Augmented Ablation Report

Model: `meta-llama/llama-4-maverick` (openrouter)
Run tag: `sweep_llama4maverick_10`
Pending LLM cases available: 721
LLM cases executed: 10
Tensor entries total: 335

## Discrimination

- Compared: 335
- Different decisions: 5
- Discrimination rate: 1.49%

## Transition counts

- accept->accept: 317
- reject->accept: 3
- reject->reject: 1
- rewrite->accept: 2
- rewrite->rewrite: 12

## Parseability

- JSON parse fail rate: 0.00%
- t present rate: 90.00%
- i present rate: 100.00%
- f present rate: 90.00%
- evidence_quality present rate: 100.00%
- declared_losses present rate: 100.00%
- decision present rate: 100.00%
- drafter_identity present rate: 100.00%
- malformed declared-loss rate: 0.00%