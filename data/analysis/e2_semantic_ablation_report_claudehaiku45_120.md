# E2 Semantic-Augmented Ablation Report

Model: `anthropic/claude-haiku-4.5` (openrouter)
Run tag: `claudehaiku45_120`
Pending LLM cases available: 721
LLM cases executed: 120
Tensor entries total: 441

## Discrimination

- Compared: 441
- Different decisions: 31
- Discrimination rate: 7.03%

## Transition counts

- accept->accept: 378
- accept->rewrite: 4
- reject->clarify: 3
- reject->reject: 2
- reject->rewrite: 1
- rewrite->clarify: 23
- rewrite->rewrite: 30

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