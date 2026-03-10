# E2 Semantic-Augmented Ablation Report

Model: `openai/gpt-4o-mini` (openrouter)
Run tag: `gpt4omini_120`
Pending LLM cases available: 721
LLM cases executed: 120
Tensor entries total: 437

## Discrimination

- Compared: 437
- Different decisions: 70
- Discrimination rate: 16.02%

## Transition counts

- accept->accept: 334
- accept->rewrite: 2
- reject->accept: 7
- reject->clarify: 14
- reject->reject: 4
- reject->rewrite: 14
- rewrite->accept: 10
- rewrite->clarify: 22
- rewrite->reject: 1
- rewrite->rewrite: 29

## Parseability

- JSON parse fail rate: 0.00%
- t present rate: 99.17%
- i present rate: 99.17%
- f present rate: 99.17%
- evidence_quality present rate: 99.17%
- declared_losses present rate: 99.17%
- decision present rate: 100.00%
- drafter_identity present rate: 100.00%
- malformed declared-loss rate: 0.00%