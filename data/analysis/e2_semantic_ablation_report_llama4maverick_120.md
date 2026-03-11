# E2 Semantic-Augmented Ablation Report

Model: `meta-llama/llama-4-maverick` (openrouter)
Run tag: `llama4maverick_120`
Pending LLM cases available: 721
LLM cases executed: 120
Tensor entries total: 425

## Discrimination

- Compared: 425
- Different decisions: 71
- Discrimination rate: 16.71%

## Transition counts

- accept->accept: 336
- reject->accept: 31
- reject->clarify: 9
- reject->reject: 3
- reject->rewrite: 4
- rewrite->accept: 20
- rewrite->clarify: 7
- rewrite->rewrite: 15

## Parseability

- JSON parse fail rate: 0.00%
- t present rate: 97.50%
- i present rate: 100.00%
- f present rate: 100.00%
- evidence_quality present rate: 100.00%
- declared_losses present rate: 100.00%
- decision present rate: 100.00%
- drafter_identity present rate: 100.00%
- malformed declared-loss rate: 0.00%