# E2 Semantic-Augmented Ablation Report

Model: `openai/gpt-4o-mini` (openrouter)
Run tag: `gpt4omini_60`
Pending LLM cases available: 721
LLM cases executed: 60
Tensor entries total: 381

## Discrimination

- Compared: 381
- Different decisions: 33
- Discrimination rate: 8.66%

## Transition counts

- accept->accept: 320
- accept->rewrite: 1
- reject->accept: 3
- reject->clarify: 4
- reject->reject: 2
- reject->rewrite: 6
- rewrite->accept: 2
- rewrite->clarify: 16
- rewrite->reject: 1
- rewrite->rewrite: 26

## Parseability

- JSON parse fail rate: 0.00%
- t present rate: 98.33%
- i present rate: 98.33%
- f present rate: 98.33%
- evidence_quality present rate: 98.33%
- declared_losses present rate: 98.33%
- decision present rate: 100.00%
- drafter_identity present rate: 100.00%
- malformed declared-loss rate: 0.00%