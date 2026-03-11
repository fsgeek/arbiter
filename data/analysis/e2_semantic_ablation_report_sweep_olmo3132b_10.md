# E2 Semantic-Augmented Ablation Report

Model: `allenai/olmo-3.1-32b-instruct` (openrouter)
Run tag: `sweep_olmo3132b_10`
Pending LLM cases available: 721
LLM cases executed: 10
Tensor entries total: 334

## Discrimination

- Compared: 334
- Different decisions: 2
- Discrimination rate: 0.60%

## Transition counts

- accept->accept: 319
- accept->clarify: 1
- reject->reject: 2
- rewrite->accept: 1
- rewrite->rewrite: 11

## Parseability

- JSON parse fail rate: 0.00%
- t present rate: 50.00%
- i present rate: 50.00%
- f present rate: 50.00%
- evidence_quality present rate: 70.00%
- declared_losses present rate: 70.00%
- decision present rate: 80.00%
- drafter_identity present rate: 80.00%
- malformed declared-loss rate: 0.00%