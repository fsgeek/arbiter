# Arbiter: Detecting Interference in LLM Agent System Prompts
## A Cross-Vendor Analysis of Architectural Failure Modes

### Abstract

System prompts for LLM-based coding agents are software artifacts that
govern agent behavior, yet lack the testing infrastructure applied to
conventional software. We present Arbiter, a framework combining formal
evaluation rules with multi-model LLM scouring to detect interference
patterns in system prompts. Applied to three major coding agent system
prompts — Claude Code (Anthropic), Codex (OpenAI), and Gemini CLI
(Google) — we identify 152 findings including 4 critical contradictions
and 2 structurally guaranteed failures. We show that prompt architecture
(monolithic, flat, modular) predicts the *class* of failure but not its
*severity*, and that multi-model evaluation discovers categorically
different vulnerability classes than single-model analysis. Total cost
of cross-vendor analysis: under $1 USD.


### 1. Introduction

- LLM coding agents (Claude Code, Codex, Gemini CLI) are governed by
  system prompts ranging from 298 to 1,490 lines
- These prompts are software artifacts: they specify behavior, encode
  precedence hierarchies, define tool contracts, and manage state
- Unlike conventional software, they have no type checker, no linter,
  no test suite — contradictions are resolved silently by the executing LLM
- **Thesis**: The agent that resolves the conflict cannot be the agent
  that detects it. External evaluation against formal rules is required.
- Contribution: taxonomy of failure modes, cross-vendor empirical evidence,
  methodology for systematic prompt analysis


### 2. Background and Related Work

- Prompt engineering literature (few address system prompt *quality*)
- Prompt injection / security (orthogonal — we analyze the prompt itself,
  not adversarial inputs to it)
- Software architecture failure modes (monolith vs microservices analogy)
- LLM-as-judge / LLM evaluation (we extend to multi-model convergent analysis)


### 3. Methodology

#### 3.1 Directed Evaluation: Rules + Interference Tensor
- EvaluationRule: formal rules compiled into consistent rule sets
- Block decomposition: LLM-based prompt → PromptBlock[]
- Block-pair evaluation: structural (free) + LLM (per-rule prompts)
- InterferenceTensor: sparse (block_a, block_b, rule) → score
- Pre-filtering reduces O(n²×R) to manageable evaluations

#### 3.2 Undirected Evaluation: Multi-Model Scouring
- Scourer: vague prompt, no predefined categories
- Map-passing composition: pass N receives all findings from 1..N-1
- Multi-model: each model brings different training biases/expertise
- Convergent termination: calibrated stopping criteria, 2+ consecutive
  "no" votes from independent models
- Model provenance tracked per finding

#### 3.3 Complementarity
- Directed rules: exhaustive within defined search frame (scope overlaps)
- Undirected scouring: discovers what's outside the search frame
  (security architecture, economic exploitation, operational risks)
- Not competing — two phases of same analysis

#### 3.4 Corpus
- Claude Code v2.1.50: 1,490 lines, 78K chars (from npm package)
- Codex GPT-5.2: 298 lines, 22K chars (from open-source repo)
- Gemini CLI: 245 lines, 27K chars (composed from TypeScript render functions)


### 4. Results

#### 4.1 Quantitative Summary

| Vendor | Lines | Findings | Passes | Models | Critical/Alarming |
|--------|-------|----------|--------|--------|-------------------|
| Claude Code | 1,490 | 116 | 10 | 10 | 4 critical |
| Codex | 298 | 15 | 2 | 2 | 0 |
| Gemini CLI | 245 | 21 | 3 | 3 | 2 alarming |

Total API cost: <$1 USD across all three analyses.

#### 4.2 Architecture-Determined Failure Modes

**Monolith (Claude Code)**: Growth-level bugs.
- Subsystems developed independently, contradictions at boundaries
- 4 critical: TodoWrite tool instructions directly contradict commit workflow
- 13 scope overlaps: redundant instructions with subtle differences
- Verbatim policy duplication (security section copy-pasted)
- Recursive agent spawning vulnerability (Tools: * includes Task tool)

**Flat (Codex)**: Simplicity trade-off.
- Identity confusion: model identity vs tool identity
- Empty section headers (truncation artifacts)
- Sequential plan status vs parallel tool execution tension
- Leaked implementation details (inline citation format suppression)

**Modular (Gemini CLI)**: Composition-seam bugs.
- ALARMING: save_memory data deleted during history compression
  (compression schema lacks field for persisted preferences)
- ALARMING: "Explain Before Acting" + "<3 lines output" = structurally
  impossible to satisfy simultaneously
- Ghost parameter: tool described with capabilities from different version
- Git diff context bomb: unbounded token generation violating efficiency rules
- Skill activation has no deactivation lifecycle

#### 4.3 Universal Patterns
- Autonomy vs restraint (all three, fundamental tension)
- Precedence hierarchy ambiguity (config files vs system instructions)
- State-dependent behavioral modes (approval presets change rules)

#### 4.4 Multi-Model Complementarity
- Different models find categorically different vulnerability classes
- Claude Opus: structural contradictions, security surfaces
- DeepSeek V3.2: identity confusion, hierarchy conflicts
- Grok 4.1: prompt structure gaps, efficiency enforcement
- Qwen: architectural fragility, cost paradoxes
- GLM: data integrity bugs, instructional drift
- Not "more findings" — *different kinds* of findings

#### 4.5 Convergence Properties
- Smaller prompts converge faster (2-3 passes vs 10)
- Stopping criteria calibration transfers across vendors
- Three consecutive "no" votes = reliable termination signal


### 5. Discussion

#### 5.1 Prompts as Software Artifacts
- Same taxonomy applies: monolith/flat/modular → failure mode prediction
- Growth patterns mirror conventional software evolution
- Missing: testing infrastructure, type checking, CI/CD for prompts

#### 5.2 The Observer's Paradox
- Executing LLM smooths over contradictions via "judgment"
- External evaluator with formal rules surfaces what execution hides
- Analogous to static analysis catching what unit tests miss

#### 5.3 Evidential Marking and Epistemic Provenance
- Severity levels map to epistemic confidence
- "Curious" = inference from pattern (-chá); "Alarming" = structural proof (-mi)
- Multi-model provenance: which model found which finding, and why that matters

#### 5.4 Limitations
- Static analysis only — no runtime behavior validation
- Scourer findings are LLM-generated (could fabricate; mitigated by multi-model)
- Gemini CLI prompt was composed from source, not captured at runtime
- Ground truth only exists for Claude Code (21 hand-labeled patterns)

#### 5.5 Responsible Disclosure
- Gemini save_memory deletion: data loss affecting real users
- Claude Code recursive agent spawning: security surface
- Both companies' repos are open source; findings derived from public artifacts


### 6. Conclusion

System prompts are the least-tested, most-consequential software artifacts
in modern AI systems. Three architectural patterns produce three characteristic
failure modes. Multi-model evaluation discovers what single-model analysis
misses. The total cost of comprehensive cross-vendor analysis is under one
dollar. The tools exist. The data is damning. Nobody is checking.


### Appendices

A. Full finding catalogs (JSON, by vendor)
B. Scourer prompt templates (first pass + subsequent pass)
C. Model list with per-finding provenance
D. Cost breakdown by model and vendor
E. Convergence curves (findings per pass)
