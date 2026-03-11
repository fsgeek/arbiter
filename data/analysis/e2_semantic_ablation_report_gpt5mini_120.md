# E2 Semantic-Augmented Ablation Report

Model: `openai/gpt-5-mini` (openrouter)
Run tag: `gpt5mini_120`
Pending LLM cases available: 721
LLM cases executed: 120
Tensor entries total: 429

## Discrimination

- Compared: 429
- Different decisions: 32
- Discrimination rate: 7.46%

## Transition counts

- accept->accept: 379
- accept->clarify: 1
- reject->accept: 3
- reject->clarify: 6
- reject->reject: 4
- reject->rewrite: 3
- rewrite->accept: 8
- rewrite->clarify: 11
- rewrite->rewrite: 14

## Parseability

- JSON parse fail rate: 0.83%
- t present rate: 99.17%
- i present rate: 99.17%
- f present rate: 99.17%
- evidence_quality present rate: 99.17%
- declared_losses present rate: 99.17%
- decision present rate: 99.17%
- drafter_identity present rate: 99.17%
- malformed declared-loss rate: 0.00%