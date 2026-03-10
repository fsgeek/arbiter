# Benchmark Freeze Manifest: `benchmark_v0`

Date: 2026-03-10  
Source commit: `e51cd61`

This manifest freezes the initial benchmark slices for the dual-track
research program. It is the comparison baseline for Track A policy
iterations and Track B limits characterization.

## Included Slices

1. `directed_ground_truth`
- `data/prompts/claude-code/v2.1.50_blocks.json`
- `data/prompts/claude-code/v2.1.50_interference.json`

2. `prompt_corpus_cross_vendor`
- `data/prompts/claude-code/v2.1.50_prompt.md`
- `data/prompts/codex/gpt5.2_system_prompt.md`
- `data/prompts/gemini-cli/gemini_cli_system_prompt.txt`

3. `scourer_final_stacks`
- `data/scourer/10pass_gptoss.json`
- `data/scourer/codex_pass2_grok.json`
- `data/scourer/gemini_pass3_glm.json`

4. `derived_cross_vendor_analysis`
- `data/analysis/cross_vendor_analysis.json`
- `data/analysis/cross_vendor_report.md`

5. `characterization_outputs`
- `docs/cairn/system_prompt_characterization.json`
- `docs/cairn/semantic_characterization.json`
- `docs/cairn/adversarial_characterization.json`
- `docs/cairn/executor_mode_characterization.json`

## Integrity

Canonical machine-readable manifest with byte counts, line counts, and
SHA256 checksums:

- `docs/cairn/benchmark_v0_manifest_20260310.json`

## Policy

- Treat these files as immutable for baseline comparisons.
- For any dataset refresh, create `benchmark_v1` rather than mutating
  `benchmark_v0`.
- Always run a fixed sentinel subset from each slice in every
  refinement cycle.
