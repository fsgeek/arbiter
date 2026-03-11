# E2 Semantic-Augmented Ablation Report

Model: `google/gemini-2.0-flash-001` (openrouter)
Run tag: `gemini20_120`
Pending LLM cases available: 721
LLM cases executed: 120
Tensor entries total: 432

## Discrimination

- Compared: 432
- Different decisions: 32
- Discrimination rate: 7.41%

## Transition counts

- accept->accept: 364
- accept->clarify: 1
- accept->rewrite: 1
- reject->accept: 4
- reject->clarify: 3
- reject->reject: 3
- reject->rewrite: 4
- rewrite->accept: 13
- rewrite->clarify: 5
- rewrite->reject: 1
- rewrite->rewrite: 33

## Parseability

- JSON parse fail rate: 1.67%
- t present rate: 39.17%
- i present rate: 46.67%
- f present rate: 55.83%
- evidence_quality present rate: 84.17%
- declared_losses present rate: 52.50%
- decision present rate: 89.17%
- drafter_identity present rate: 72.50%
- malformed declared-loss rate: 0.00%