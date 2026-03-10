# E2 Semantic-Augmented Ablation Report

Model: `google/gemini-2.0-flash-001` (openrouter)
Run tag: `gemini20_40`
Pending LLM cases available: 721
LLM cases executed: 40
Tensor entries total: 360

## Discrimination

- Compared: 360
- Different decisions: 6
- Discrimination rate: 1.67%

## Transition counts

- accept->accept: 330
- reject->accept: 2
- reject->reject: 3
- reject->rewrite: 1
- rewrite->accept: 3
- rewrite->rewrite: 21

## Parseability

- JSON parse fail rate: 0.00%
- t present rate: 42.50%
- i present rate: 50.00%
- f present rate: 50.00%
- evidence_quality present rate: 90.00%
- declared_losses present rate: 35.00%
- decision present rate: 90.00%
- drafter_identity present rate: 72.50%
- malformed declared-loss rate: 0.00%