# E2 Semantic-Augmented Ablation Report

Model: `openai/gpt-5-mini` (openrouter)
Run tag: `gpt5mini_60`
Pending LLM cases available: 721
LLM cases executed: 60
Tensor entries total: 373

## Discrimination

- Compared: 373
- Different decisions: 10
- Discrimination rate: 2.68%

## Transition counts

- accept->accept: 348
- accept->clarify: 1
- reject->accept: 1
- reject->clarify: 1
- reject->reject: 3
- reject->rewrite: 1
- rewrite->accept: 1
- rewrite->clarify: 5
- rewrite->rewrite: 12

## Parseability

- JSON parse fail rate: 0.00%
- t present rate: 100.00%
- i present rate: 100.00%
- f present rate: 100.00%
- evidence_quality present rate: 100.00%
- declared_losses present rate: 100.00%
- decision present rate: 100.00%
- drafter_identity present rate: 100.00%
- malformed declared-loss rate: 0.00%