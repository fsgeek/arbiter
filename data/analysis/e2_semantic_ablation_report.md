# E2 Semantic-Augmented Ablation Report

Model: `openai/gpt-4o-mini` (openrouter)
Pending LLM cases available: 721
LLM cases executed: 40
Tensor entries total: 361

## Discrimination

- Compared: 361
- Different decisions: 17
- Discrimination rate: 4.71%

## Transition counts

- accept->accept: 323
- accept->rewrite: 1
- reject->accept: 1
- reject->clarify: 3
- reject->reject: 4
- reject->rewrite: 3
- rewrite->accept: 3
- rewrite->clarify: 6
- rewrite->rewrite: 17

## Parseability

- JSON parse fail rate: 0.00%
- t present rate: 95.00%
- i present rate: 95.00%
- f present rate: 95.00%
- evidence_quality present rate: 97.50%
- declared_losses present rate: 97.50%
- decision present rate: 100.00%
- drafter_identity present rate: 100.00%
- malformed declared-loss rate: 0.00%