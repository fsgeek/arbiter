# Arbiter Dual-Track Research Plan (2026)

Last updated: March 10, 2026

## 1. Purpose

This document defines the operating research plan for Arbiter.

Core objective:
- Minimize prompt-induced "cognitive dissonance" (conflicting and ambiguous requirements) in LLM agents.

Working framing:
- Prompts are contracts.
- Contract interpretation is precedence-bound and context-dependent.
- Contradiction handling must be explicit, testable, and auditable.

Scope note on the contract metaphor:
- In this program, "contract" means precedence-bound interpretation with explicit conflict adjudication.
- It does not imply bilateral negotiation, legal remedy, or "meeting of the minds."
- Standing for adjudication is implementation-defined: Arbiter is the adjudicator, users and operators are policy stakeholders.

## 2. Program Structure

Arbiter runs as a dual-track program:

1. Track A: Engineering Utility Under Uncertainty
- Build adjudication tooling that improves real-world reliability now.

2. Track B: Epistemic Limits and Scientific Characterization
- Measure where adjudication is fundamentally unstable, ambiguous, or low-agreement.

The tracks are coupled:
- Track B identifies boundaries and uncertainty regimes.
- Track A uses those boundaries to route behavior (`accept`, `clarify`, `rewrite`, `reject`).

## 3. Normative Architecture (Three Tiers)

Tier hierarchy:
1. System tier: constitutional invariants (highest precedence)
2. Domain tier: domain-specific obligations (must cohere with system tier)
3. User/application tier: case-specific requests (admissible if coherent under tiers 1-2)

Decision principle:
- Higher-tier contradictions are not silently reconciled by the model.
- Lower-tier content is transformed or refused when it violates higher-tier constraints.

## 4. Research Questions

RQ1 (effect):
- Do explicit conflict adjudication policies reduce failure rates compared to ungoverned prompt execution?

RQ2 (mechanism):
- Which interference classes most strongly predict degraded agent behavior?

RQ3 (limits):
- What proportion of cases remain high-indeterminacy even with improved rules and context?

RQ4 (governance):
- Can iterative LLM refinement loops improve adjudication policy without overfitting or drift?

RQ5 (high-risk operation):
- In mission-critical settings, does a panel/court-style adjudication layer materially improve safety and auditability?

RQ6 (governance semantics):
- How should drafter identity and authority be modeled when ambiguity can be interpreted against the drafter?

## 5. Hypotheses

H1:
- Increasing conflict load (especially direct contradiction + priority ambiguity) decreases task success and increases unstable behavior.

H2:
- Tier-aware adjudication (`accept/clarify/rewrite/reject`) outperforms direct execution on reliability and policy compliance.

H3:
- A non-trivial subset of cases will exhibit persistent high indeterminacy (high-I), even with richer rules and context.

H4:
- Iterative, move-constrained hypothesis refinement improves policy quality faster than ad hoc manual rule editing.

H5:
- For high-risk scenarios, court-style multi-adjudicator review reduces catastrophic error rate at acceptable additional cost/latency.

H6:
- Scalar-only adjudication outputs will exhibit representational collapse in some conflict classes; adding structured declared losses will recover actionable distinctions.

## 6. Data and Assets Already Available

Primary in-repo assets:
- Prompt corpora: `data/prompts/`
- Prompt AST artifacts: `data/prompt_ast/`
- Scourer outputs (multi-pass, multi-model): `data/scourer/`
- Cross-vendor analysis: `data/analysis/cross_vendor_analysis.json`, `data/analysis/cross_vendor_report.md`
- Episode data: `data/episodes/episodes.json`
- Existing tests and characterization harnesses: `tests/`

Code assets to extend:
- Block schema and interference taxonomy: `src/arbiter/prompt_blocks.py`
- Rule compiler/evaluator hooks: `src/arbiter/rules.py`, `src/arbiter/block_evaluator.py`
- Tensor representation: `src/arbiter/interference_tensor.py`
- Pipeline orchestration: `src/arbiter/pipeline.py`
- Scourer analysis tooling: `scripts/analyze_scourer_data.py`

## 7. Track A Plan (Utility)

## A1. Adjudication State Extension

Extend tensor entries from scalar conflict score to contextual adjudication state:
- T: compatibility/support
- I: indeterminacy/ambiguity
- F: conflict/violation
- Context tags (tier pair, scope class, rule source)
- Evidence quality score

Deliverable:
- New tensor schema and serializer compatibility path.

Declared loss channel (required for full mode):
- `loss_what`: what cannot be reliably adjudicated
- `loss_why`: why this limitation applies in context
- `loss_severity`: impact on adjudication quality [0.0, 1.0]

## A2. Tier-Gated Runtime Decision Policy

Define deterministic policy function over (T, I, F, tier, scope):
- `accept`
- `clarify`
- `rewrite`
- `reject`

Required policy canons (initial set):
- higher-tier-over-lower-tier
- explicit-over-implicit
- specific-over-general
- ambiguity-against-drafter (candidate canon; evaluate empirically)

Canon parameterization requirement:
- Ambiguity-against-drafter must include drafter identity (`provider`, `operator`, `user`, `unknown`) and authority level.
- Default behavior when drafter identity is unknown must be conservative and auditable.

Deliverable:
- Executable policy module with threshold configuration.

## A3. Linter + Rewrite Front-End

Build a pre-execution pass that:
- flags conflicts,
- extracts minimal contradiction cores when possible,
- proposes constrained rewrites,
- re-evaluates post-rewrite coherence.

Deliverable:
- CLI path for lint-only and lint+rewrite modes.

## A4. High-Risk Mode (Optional Gate)

For designated high-risk scopes:
- route ambiguous/conflict-heavy cases to panel adjudication (court mode),
- produce an auditable rationale bundle.

Deliverable:
- configuration-gated high-risk workflow.

## 8. Track B Plan (Limits)

## B1. Agreement and Stability Study

Measure:
- human-human agreement,
- model-model agreement,
- human-model agreement,
across clause conflict cases.

Deliverable:
- Agreement atlas by interference type and tier pairing.

## B2. Context Sensitivity Mapping

Perturbation protocols:
- paraphrase invariance,
- clause order permutation,
- scope expansion/restriction,
- lexical intensity changes (MUST vs SHOULD variants where allowed).

Deliverable:
- Sensitivity surface showing where decisions flip.

## B3. Persistent High-I Characterization

Identify cases with durable indeterminacy under:
- added context,
- stricter canons,
- repeated adjudication passes.

Deliverable:
- Catalog of irreducible/near-irreducible ambiguity classes.

Operational persistence criterion:
- A case is labeled persistent-high-I if:
  - `I >= tau_I` after at least `N_min` adjudication passes, and
  - marginal change `|delta I| < epsilon` for `k` consecutive passes, and
  - no canon or context mutation in the allowed set lowers `I` below `tau_I`.
- Initial defaults for pilot studies:
  - `tau_I = 0.60`, `N_min = 3`, `epsilon = 0.03`, `k = 2`
- Thresholds are to be tuned only via pre-registered updates.

## B3b. Representational Collapse Detection

Identify cells where:
- scalar adjudication appears identical or near-identical,
- but declared loss structures differ materially.

Deliverable:
- Collapse atlas (where scalar channels fail to discriminate and tensor channels recover distinction).

## B4. Minimal Unsat Core Extraction

For conflicting clause sets, compute smallest explanatory conflict cores.

Deliverable:
- Benchmark set of minimal cores for regression testing and explanation quality.

## 9. Iterative Refinement Methodology

Use a bounded iterative loop for policy/rule evolution:

1. Generate
- Propose candidate rule/canon/policy deltas.

2. Critique
- Cross-model criticism from independent model families.
- Include scheduled human-adversary review rounds (deliberate spoiler role) to probe shared model blind spots.

3. Adversarialize
- Construct counterexamples and challenge prompts.

4. Evaluate
- Run on frozen benchmark split + held-out split.

5. Accept or Reject
- Promote only if pre-registered metrics improve and regressions are bounded.

6. Archive
- Log a hypothesis card with status: accepted/rejected/deferred.

Guardrails:
- No unbounded free-form policy changes.
- Use move-constrained edits (small, typed modifications).
- Preserve reproducibility with versioned benchmark snapshots.

Translation guardrail:
- Keep epistemic and normative claims separated in reporting.
- Use neutrosophic tensor representation as a transfer of output structure, not as an assertion that epistemic truth and normative validity are identical constructs.
- Do not treat cross-model agreement as sufficient evidence of independence.

## 9b. Translation Framework: Epistemic -> Normative

Source framing (neutrosophic LLM logic):
- T/I/F + declared losses represent epistemic assessment fidelity.

Target framing (Arbiter):
- T/I/F + declared losses represent normative contract adjudication state under tier precedence.

Mapping used in this program:
- `T`: compatibility/support between clauses under active canons
- `I`: unresolved interpretive indeterminacy after canon application
- `F`: normative conflict/violation pressure against higher-precedence constraints
- Declared losses: explicit adjudication limitations, missing context, unresolved scope boundaries, or canon insufficiency

Transfer assumptions:
1. Representation-level transfer is valid (tensorized output can preserve distinctions lost by scalars).
2. Domain semantics differ (epistemic truth vs normative admissibility) and must be evaluated separately.
3. Benefits must be demonstrated empirically within Arbiter tasks, not inferred from external results.

## 10. Evaluation Metrics

Primary metrics:
- Task success rate
- Conflict detection recall/precision
- False reject rate
- Clarification burden (clarifications per task)
- Rewrite faithfulness score
- Severe failure incidence (critical policy breaches)
- Arbiter error recovery latency (time from discovered mis-adjudication to corrected policy/rule rollout)

Secondary metrics:
- Latency overhead
- Cost per adjudicated task
- Decision stability under perturbation
- Inter-rater agreement (kappa or equivalent)
- Scalar-vs-tensor discrimination gain (how often tensor channels separate cases scalar channels collapse)

High-risk metrics:
- Catastrophic error rate
- Audit completeness and explanation quality

## 11. Experimental Design

Baseline arms:
1. Raw execution (no adjudication)
2. Structural-only adjudication
3. Full adjudication (single model)
4. Full adjudication (panel mode; high-risk only)
5. Scalar-only vs tensor+declared-loss ablation

Key factors:
- Conflict load
- Interference type composition
- Tier location of conflict
- Context regime (normal vs adversarially perturbed)

Statistical guidance:
- Pre-register hypotheses and stopping criteria for each run family.
- Report effect sizes and confidence intervals, not only point estimates.
- Separate exploratory and confirmatory analyses.
- Use fractional factorial or adaptive sampling when full crossing is computationally infeasible.
- Maintain a fixed sentinel set that is always evaluated each iteration for comparability.

Failure-handling protocol:
- If post-hoc review identifies confident mis-adjudication:
  - create an incident record with affected scope/tier/rules,
  - add a regression case to benchmark,
  - apply hotfix policy/rule patch behind feature flag,
  - re-run sentinel suite before full promotion.

## 12. Milestones (11-Week Rolling Horizon)

Phase 0 (Week 1): Program setup
- Freeze benchmark v0 from existing corpora and scourer outputs.
- Lock metric definitions and experiment logging format.

Phase 1 (Weeks 2-4): Track A baseline
- Implement tier-gated decision policy over current tensor outputs.
- Ship lint-only CLI and baseline reports.

Phase 2 (Weeks 3-6): Track B baseline characterization
- Run agreement and perturbation studies on benchmark v0.
- Publish first high-I map.
- Run first human-adversary spoiler round.

Phase 3 (Weeks 5-8): Iterative refinement cycle v1
- Execute 2-3 refinement loops with strict promotion gates.
- Integrate accepted policy/rule deltas.

Phase 4 (Weeks 8-11): High-risk mode pilot
- Enable court-mode workflow on selected high-risk scenarios.
- Compare catastrophic error rate vs single-adjudicator mode.

## 13. Decision Gates

Gate G1 (after Phase 1):
- Proceed if Track A baseline shows measurable reliability improvement without unacceptable false rejects.

Gate G2 (after Phase 2):
- Proceed if Track B identifies stable high-I regions with reproducible evidence.

Gate G3 (after Phase 3):
- Promote refinement loop to default only if net improvements hold on held-out data.

Gate G4 (after Phase 4):
- Adopt high-risk court mode if safety gains justify operational overhead.

## 14. Risks and Mitigations

Risk:
- Overfitting to benchmark artifacts.
Mitigation:
- Held-out slices, periodic refresh, adversarial challenge sets.

Risk:
- Metric gaming via aggressive rejection behavior.
Mitigation:
- Joint optimization on success + false reject + clarification burden.

Risk:
- Spurious confidence from single-model evaluators.
Mitigation:
- Cross-model critics and provenance logging.

Risk:
- Shared blind spots across model families create false consensus.
Mitigation:
- Periodic human-adversary spoiler rounds and adversarial benchmark expansion.

Risk:
- Contract metaphor overreach introduces conceptual confusion in review.
Mitigation:
- Keep explicit scope note (interpretive machinery only) in all formal writeups.

Risk:
- Upstream context compaction/paging changes observable clause structure.
Mitigation:
- Evaluate on both raw and compacted/processed context variants when integration applies.

Risk:
- Drift from reproducible science into anecdotal iteration.
Mitigation:
- Hypothesis cards, pre-registered gates, archived results.

## 15. Reference Methods to Integrate

Iterative/refinement methods relevant to this program:
- Self-Refine (2023): iterative self-feedback loops
- Reflexion (2023): verbal reinforcement and retry policies
- Tree of Thoughts (2023): deliberate branch-and-evaluate search
- PromptBreeder (2023): evolutionary prompt optimization
- 2026 fast-loop work: confidence-gated and principle-evolution style refinement

Uncertainty representation precedent:
- Neutrosophic Description Logic (2006): explicit truth/indeterminacy/falsity representation.
- 2026 neutrosophic tensor extension with declared losses (submitted March 9, 2026): representation-level evidence that scalar channels can collapse distinctions recovered by tensor outputs.

## 16. Immediate Next Actions

1. Create benchmark freeze manifest (`benchmark_v0`) from current datasets.
2. Add hypothesis card template under `docs/cairn/`.
3. Define tensor extension proposal (T/I/F + context tags + declared losses) in a short technical spec.
4. Implement baseline tier-gated policy using existing scalar tensor as temporary proxy.
5. Add scalar-vs-tensor collapse benchmark slice.
6. Start Phase 2 agreement pilot with existing characterization harnesses.
7. Define drafter-identity schema and ambiguity-canon decision table.
8. Define incident-response template for mis-adjudication recovery.

## 17. Integration Dependencies and Scope Boundaries

Pichay/context-compaction dependency:
- If Arbiter is used downstream of context compaction or demand paging systems, adjudication inputs may differ materially from raw context.
- This can change conflict detectability and indeterminacy profile.

Scope in this plan:
- Core experiments run on frozen prompt artifacts and controlled perturbations.
- Integration experiments with compaction/paging systems are tracked as a dependent workstream and reported separately unless explicitly included in a phase gate.
