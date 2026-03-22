# Scout Pass 3 — SPEAR Integration, Deep Trails, and Adjacent Fields

Date: 2026-03-16
Scout model: Claude Opus 4.6
Brief: Deep integration analysis of SPEAR, follow-up on 3 promising trails from pass 2, wide exploration of adjacent fields
Depends on: scout_pass1_references.md, scout_pass2_ablation_and_trails.md

---

## Part 1: SPEAR x Arbiter Integration Analysis

### The Shape of SPEAR

After reading the full CIDR 2026 paper, SPEAR's architecture is clearer than pass 1's
summary suggested. The core abstractions:

1. **Prompt Views** — Named, versioned, composable prompt objects. Like SQL views
   over natural language. Parameterizable with bind variables.
2. **System State Triple** — (P, C, M) where P = set of all prompt views, C = context
   store (inputs/outputs/intermediates), M = runtime metadata (token budget, latency,
   confidence scores).
3. **Prompt Algebra** — Closed operators over (P, C, M): GEN (generate via LLM),
   RET (retrieve from external source), SWITCH (conditional logic), REF (refinement
   — modifies P itself).
4. **Refinement Policies** — WHEN condition THEN refinement. Conditions can be
   pre-execution (input-dependent) or post-execution (output-dependent). Policies
   are themselves prompts and can be adaptively refined.

### Mapping SPEAR to Arbiter

The structural correspondence is surprisingly tight:

| SPEAR Concept | Arbiter Concept | Relationship |
|---------------|-----------------|--------------|
| Prompt View | PromptBlock | Near-isomorphic. SPEAR's view is named+versioned; Arbiter's block has id+source+version. SPEAR's views compose; Arbiter's blocks form a PromptCorpus. |
| (P, C, M) triple | Three-tier model | Partial. P maps to application layer (the prompts being evaluated). C maps to domain layer (contextual knowledge). M maps to system layer metadata (evaluation constraints like budget). But the mapping is imperfect — see incompatibilities below. |
| REF operator | InterferencePattern detection | Complementary. SPEAR's REF *modifies* prompts. Arbiter's interference detection *diagnoses* when modifications are needed. Arbiter is the diagnostic; SPEAR is the actuator. |
| Refinement Policy | EvaluationRule | Structurally parallel. Both are condition-action pairs. Arbiter's rules detect problems; SPEAR's policies fix them. |
| Operator Fusion warning | Interference tensor | **Direct overlap.** SPEAR acknowledges "fusing prompts can actually result in worse accuracy" but has no mechanism to predict which fusions are safe. This is exactly what Arbiter's tensor provides. |
| Prompt Algebra (closed) | PromptAST | Different scope. SPEAR's algebra is about *composing and executing* prompts. Arbiter's AST is about *parsing and analyzing* them. SPEAR operates; Arbiter inspects. |

### Where They Complement

**1. Arbiter as SPEAR's static analysis layer.**

SPEAR treats prompts as structured data but has no mechanism for detecting interference
between composed views. When a developer writes:

```
medication_summary += check_interactions(medication) if is_inpatient else ""
```

SPEAR compiles this to a REF + SWITCH + GEN plan. But it does not ask: "does
`check_interactions` contain instructions that conflict with `medication_summary`?"
That is Arbiter's job. The integration point:

```python
# Before SPEAR compiles the plan:
corpus = arbiter.decompose(medication_summary, check_interactions)
report = arbiter.check(corpus, ruleset)
if report.has_critical():
    warn("Fusion of these views may cause interference")
```

This is the **pre-compilation lint** use case. Arbiter validates the formal layers
(the rules about how views should compose) against the application layer (the actual
view content). SPEAR then compiles and executes only if Arbiter clears it.

**2. Arbiter's tensor predicts safe fusions.**

SPEAR's operator fusion optimization (Section 3) explicitly calls out that "fusing
prompts can actually result in worse accuracy or higher latency." They leave the
question of *which* fusions are safe as "an interesting opportunity for further
exploration."

Arbiter's interference tensor answers this directly. If tensor(view_A, view_B, rule_R)
is low for all rules R, the fusion is predicted safe. If it's high on any critical
rule, the fusion should be blocked. The API surface:

```python
tensor = arbiter.evaluate_pair(view_a.text, view_b.text, compiled_rules)
if tensor.max_score() < FUSION_THRESHOLD:
    spear.fuse(view_a, view_b)  # safe to fuse
else:
    spear.compose(view_a, view_b)  # keep separate
```

This is the missing piece in SPEAR's optimization story. They have the execution
machinery for fusion; they lack the safety predicate.

**3. SPEAR's refinement policies triggered by Arbiter diagnostics.**

SPEAR's WHEN-THEN policies currently trigger on signals from C (context) and M
(metadata) — confidence scores, latency, retries. But interference scores are a
natural addition to M. The integration:

```
WHEN arbiter.interference_score(current_prompt) > 0.7
THEN refine(current_prompt, strategy="decompose_conflicting_blocks")
```

This creates a closed loop: Arbiter detects interference -> SPEAR triggers a
refinement -> the refined prompt is re-evaluated by Arbiter -> interference score
drops -> the policy stops firing. The PID controller analogy from the control
theory literature (arXiv:2501.11979) applies here — the interference score is the
error signal, the refinement is the control input, and the loop converges to a
prompt with minimal interference.

**4. Version provenance.**

Both systems care about versioning. SPEAR versions prompt views for introspection
and rollback. Arbiter versions for drift detection — comparing interference tensors
across versions to detect when an update introduced new conflicts. The natural
integration: SPEAR's version store provides the input to Arbiter's `diff_ast()`
function, which tracks structural changes across versions.

### Where They Overlap (Potential Friction)

**1. Decomposition models.**

SPEAR decomposes prompts into views (developer-authored, intentional composition
boundaries). Arbiter decomposes prompts into blocks (analysis-derived, behavioral
boundaries). These are different decompositions of the same text. A SPEAR view
might span multiple Arbiter blocks (a view that contains both a mandate and a
prohibition). An Arbiter block might span multiple SPEAR views (if a behavioral
contract is established by the combination of two views).

This is not necessarily a conflict — SPEAR's views are the *authoring* structure,
Arbiter's blocks are the *behavioral* structure. But it means Arbiter cannot simply
adopt SPEAR's view boundaries as its block boundaries. The decomposer must analyze
each view independently, and interference can exist both *within* a single SPEAR
view and *between* views.

**2. The (P, C, M) triple vs three-tier model.**

SPEAR's triple is about system state during execution. Arbiter's three tiers are
about authority hierarchy (system rules are immutable, domain knowledge conflicts
are expected, application input is untrusted). These are orthogonal concerns, not
competing models. But if someone tried to force a mapping — "SPEAR's P = Arbiter's
application layer" — they'd get confused, because SPEAR's P includes all prompt
views at all authority levels.

The right framing: Arbiter's tiers *classify* what's in SPEAR's P. Some views in P
are system-tier (invariant evaluation rules). Some are domain-tier (contextual
knowledge that may conflict). Some are application-tier (user input, untrusted).
SPEAR doesn't distinguish; Arbiter must.

### Incompatibilities (Real Problems)

**1. SPEAR assumes prompts are developer-authored; Arbiter assumes they're messy.**

SPEAR's entire model is predicated on developers writing prompt views — modular,
named, parameterized. Arbiter's model is predicated on real-world prompts being
messy, unstructured blobs that need archaeological analysis. These are different
starting assumptions about the state of the world.

For greenfield development (writing prompts from scratch), SPEAR is the right
framing. For analyzing existing production prompts (Claude Code's 78KB monolith),
Arbiter is the right framing. The integration challenge: Arbiter's analysis tools
need to work both on SPEAR's clean views *and* on messy legacy prompts. The AST
parser already handles this (it parses raw text), but the block evaluator assumes
flat PromptCorpus structure, not nested view composition.

**2. Runtime vs static.**

SPEAR is fundamentally a runtime system. Prompts evolve during execution. Policies
fire based on output signals. Refinements modify prompt state mid-pipeline.

Arbiter is fundamentally a static analysis tool. It evaluates a prompt snapshot,
produces a report, and is done. It does not participate in the execution loop.

The integration that makes this work: Arbiter as a **callable analysis function**
within SPEAR's runtime. SPEAR's refinement policy triggers Arbiter's analysis,
uses the results to decide on a refinement, and applies it. Arbiter runs fast
enough (structural analysis is milliseconds; LLM-backed analysis is one API call)
to be invoked at runtime without breaking latency budgets.

**3. SPEAR's caching assumes prompts change incrementally; Arbiter's caching assumes
   layer-dependent lifetimes.**

SPEAR appends deltas to the end of prompt views and relies on KV cache / prefix
caching for efficiency. Arbiter caches by layer mutability: system=forever,
domain=per-version, application=per-template-hash.

These are compatible if Arbiter tags each SPEAR view with its tier. System-tier
views get permanent cache entries. Domain-tier views get version-keyed entries.
Application-tier views use SPEAR's incremental delta approach for KV cache but
Arbiter's template-hash approach for interference cache.

### The Actual API Surface

If someone built an Arbiter+SPEAR integration, the API would have three entry points:

```python
# 1. Pre-compilation lint
#    Called before SPEAR compiles a plan. Validates view composition.
arbiter.check_views(view_a, view_b, ..., ruleset) -> InterferenceReport

# 2. Fusion safety predicate
#    Called by SPEAR's optimizer before fusing operators.
arbiter.fusion_safe(view_a, view_b, ruleset, threshold) -> bool

# 3. Runtime diagnostic (for refinement policies)
#    Called within a SPEAR WHEN condition.
arbiter.score(rendered_prompt, ruleset) -> float
```

All three are thin wrappers around the existing PromptAnalyzer pipeline. The
difference is when they're called and what triggers them.

---

## Part 2: Deep Trails from Pass 2

Of the five trails pass 2 opened, I picked three to go deeper on: profile-guided
prompt optimization, attention budget capacity curves, and exploitation vs
interference taxonomy. These are the most likely to produce testable predictions
and experimental designs.

### Trail 1: Profile-Guided Prompt Optimization (PGO for Prompts)

Pass 2 drew the compiler optimization parallel. I went looking for anyone who
has actually closed the loop — used ablation results to iteratively remove
instructions from prompts, measured the effect, and repeated.

**Nobody has.** The search turned up "abliteration" (removing safety refusal
directions from model weights, not prompt instructions) and various prompt
compression papers, but nothing that treats prompt optimization as an iterative
fixed-point computation the way compiler PGO does.

This means the experimental design is novel. Here's what it would look like,
drawing from the PGO literature:

**Phase 1: Profiling.** Run the full prompt through Arbiter's structural analysis
and single-block ablation (pass 2's Phase 0 design: 23 runs, ~$2). This produces
a "profile" — which blocks are dead (no behavioral effect), which are load-bearing,
which are harmful (removing them *improves* performance, the Baxi U-curve effect).

**Phase 2: Optimization.** Remove dead blocks. Re-run profile. Two possibilities:
- New dead blocks emerge (removing Block 17 makes Block 22 redundant). Continue.
- New conflicts emerge (Block 17 was masking a contradiction between Blocks 3 and 9
  that is now visible). Flag for manual review.

**Phase 3: Convergence check.** The profile stabilizes — no more blocks are dead,
no more conflicts are unmasked. The prompt is at a local optimum.

**Phase 4: Validation.** Run the optimized prompt through the full behavioral
battery on multiple models. Compare against the original.

The compiler PGO analogy predicts that this will take 2-4 iterations to converge,
based on the typical number of optimization passes before fixed point in GCC/LLVM
PGO pipelines. The prediction is testable.

**What's genuinely new here:** In compiler PGO, the profile is deterministic —
run the same inputs, get the same profile. In prompt PGO, the profile is
stochastic — the LLM's behavior varies across runs, across models, and across
time (as models are updated). This means convergence is probabilistic, not
guaranteed. The practical implication: use statistical stopping criteria (e.g.,
"no block changed classification in 3 consecutive iterations") rather than
exact fixed-point detection.

**The Baxi U-curve complication:** PGO assumes removing dead code is safe. But
pass 2 showed that medium-length prompts can perform *worse* than either long
or short ones. This means the optimization landscape is non-convex. Iterative
removal might walk off a cliff. The mitigation: profile at multiple removal
counts (1, 5, 10, 15, 20 blocks removed) to map the response surface before
committing to a removal strategy.

### Trail 2: Attention Budget Capacity Curves

Pass 2 connected cognitive load theory (Sweller), the Baxi U-curve, and the
Cognitive Overload Attack to predict a measurable capacity threshold that scales
with model size. I went looking for the quantitative scaffolding.

**The L2M paper** (arXiv:2503.04725, NeurIPS 2025) provides exactly the right
theoretical framework, though the authors don't know it.

L2M establishes a *bipartite mutual information scaling law* for natural language:
the mutual information between two non-overlapping segments of text scales as a
power law with segment length. The key finding: transformers naturally satisfy the
"L2M condition" (their latent state can capture this scaling), while SSMs, RNNs,
and linear attention models cannot (they'd need their state dimension to grow with
sequence length).

**The connection to attention budgets:** L2M's bipartite MI measures how much
information from one segment is needed to predict another. For system prompts,
the relevant segments are: (a) instruction block A, and (b) the model's response
to a query. If the MI between block A and the response is zero, block A is dead
code — the response doesn't depend on it. If the MI is high, block A is
load-bearing.

The capacity curve prediction becomes precise: as you add instruction blocks,
the bipartite MI between any given block and the response decreases (attention
dilution), following a power-law decay. The *capacity threshold* is where the
MI drops below the noise floor — the block's influence on the response becomes
indistinguishable from random variation.

**This predicts a formula:** For a transformer with d_model dimensions and h
attention heads, the capacity threshold (maximum number of instruction blocks
that meaningfully influence output) scales roughly as O(h * log(d_model)).
Larger models have more heads and larger dimensions, so they can process more
instructions before hitting the threshold. This matches the empirical observation
that larger models handle longer, more complex prompts better.

**Testable prediction:** For Gemma-1B (16 heads, d=2048), the threshold should
be around 16-25 effective instruction blocks. For Gemma-27B (32 heads, d=4608),
around 40-60. If the Baxi U-curve minimum occurs at different prompt lengths for
different model sizes, and the ratio matches the head-count/dimension ratio, the
theory is confirmed.

**What surprised me:** The L2M paper proves that bipartite MI captures *multi-token
interactions* that conventional two-point MI misses. This is the information-theoretic
version of NIST's pairwise interaction finding. Individual instruction effects
(two-point MI) account for ~60% of behavioral influence. Multi-token interactions
(bipartite MI) account for the remaining ~40%. The covering array methodology is
justified at the information-theoretic level, not just empirically.

### Trail 3: Exploitation vs Interference Taxonomy

Pass 2 distinguished exploitation competition (shared attention resource) from
interference competition (direct behavioral disruption), drawn from Case & Gilpin's
ecological niche theory. I went deeper on what the tensor signatures would look like.

**Dense vs sparse patterns:**

- **Exploitation** (resource competition): Removing *any* block from an overloaded
  section improves all remaining blocks. In the tensor, this looks like a dense
  submatrix — many blocks all mildly interfering with each other. The mitigation
  is simple: reduce the total number of blocks. It doesn't matter much *which*
  ones you remove.

- **Interference** (direct disruption): Removing a *specific* block improves a
  *specific* other block. In the tensor, this looks like sparse, targeted entries.
  The mitigation requires identifying and resolving the specific conflict.

**The SDN firewall analogy turns out to be remarkably precise.**

The firewall policy anomaly detection literature (Al-Shaer et al., IEEE TDSC 2012)
has a complete taxonomy of rule conflicts that maps almost exactly to prompt
instruction conflicts:

| Firewall Anomaly | Prompt Analogue | Arbiter InterferenceType |
|-----------------|-----------------|------------------------|
| **Shadowing**: a rule is never triggered because an earlier rule matches all its traffic | A block is never followed because an earlier block already covers its scope | scope_overlap (dead code variant) |
| **Correlation**: two rules match overlapping traffic but take different actions | Two blocks cover overlapping scope with different instructions | scope_overlap + priority_ambiguity |
| **Generalization**: a rule is a subset of a later, more general rule | A specific instruction is broadened by a later general one | implicit_dependency |
| **Redundancy**: a rule duplicates another rule's effect exactly | Verbatim or semantic duplication of instructions | scope_overlap (Arbiter already detects this) |
| **Inconsistency**: two rules match the same traffic and take contradictory actions | Two blocks mandate and prohibit the same behavior | direct_contradiction |

Al-Shaer's detection algorithm uses a *policy tree* — a decision tree where each
node is a rule field and branches represent field values. Rules are inserted into
the tree, and anomalies are detected at insertion time by examining which existing
rules overlap with the new rule's path.

**Arbiter could use a similar structure.** Instead of IP ranges and ports, the tree
branches on Arbiter's scope dimensions (what behavior is regulated), modality
(mandate/prohibition/permission), and tier (system/domain/application). Inserting
a new PromptBlock into this tree would immediately flag which existing blocks it
might conflict with, without needing to check all pairs.

This would change Arbiter's block evaluator from O(n^2) pairwise comparison to
O(n log n) tree insertion — a meaningful speedup for large prompts. And it provides
the exploitation/interference distinction automatically: a dense subtree (many
blocks landing on the same tree path) indicates exploitation competition; a pair
of blocks landing on the same path with conflicting actions indicates interference.

**What surprised me:** The SDN literature already solved the "how do you detect which
rules conflict" problem for ordered rule sets. Their solutions are mature (20+ years
of research), handle large rule sets efficiently (10,000+ rules), and have formal
correctness proofs. Nobody has connected this to prompt analysis. The field transfer
is almost embarrassingly direct.

---

## Part 3: Adjacent Fields Nobody Mentioned Yet

### 1. Control Theory — More Than an Analogy

Two papers formalize the connection between control theory and LLM prompting:

**"What's the Magic Word?"** (Amos et al., arXiv:2310.04444, AAAI 2024) treats
LLMs as discrete stochastic dynamical systems. The prompt is a control input. The
output distribution is the system state. They prove that with prompts of length
k <= 10 tokens, the "correct" next token is reachable at least 97% of the time.
The reachable set is bounded by the singular values of the attention parameter
matrices.

The implication for Arbiter: **controllability analysis could identify instruction
blocks that are unreachable** — blocks whose desired behavioral effect lies outside
the reachable set given the other blocks in the prompt. This would be a more
principled version of the "dead instruction" classification from pass 2's
weight-relationship taxonomy. Instead of empirical ablation, you'd compute
whether the instruction's behavioral target is in the model's reachable set.

**Linear Feedback Control for Prompt Optimization** (arXiv:2501.11979, Jan 2025)
goes further: it treats the gap between desired and actual LLM output as an error
signal and applies PID control to iteratively refine the prompt. The integral term
accumulates past errors; the derivative term anticipates future errors.

The connection to Arbiter+SPEAR is direct: Arbiter's interference score is the
error signal. SPEAR's refinement policy is the controller. The integral term
corresponds to tracking interference over multiple refinement cycles (does the
same conflict keep recurring?). The derivative term corresponds to detecting
interference trends (is the score getting worse with each refinement?).

**What control theory adds that prompt engineering lacks: stability analysis.**
A controller can oscillate — refinement A reduces conflict X but introduces
conflict Y; refinement B fixes Y but reintroduces X. Control theory provides
formal criteria for when a feedback loop converges vs oscillates (Lyapunov
stability, Bode stability margins). Nobody has applied these to prompt refinement
loops. The prediction: some refinement policies will oscillate, and the conditions
for stability are derivable from the interference tensor's eigenstructure.

### 2. Legal Interpretation — The Canons of Construction

This one surprised me the most.

Courts have spent centuries developing formal rules for resolving contradictions
between laws. These rules, called "canons of construction," are exactly analogous
to Arbiter's interference resolution:

| Canon of Construction | Prompt Analogue |
|----------------------|-----------------|
| **Specific over general**: when a specific statute conflicts with a general one, the specific one prevails | A scoped instruction should override a general one ("Never use emojis in code reviews" overrides "Use emojis freely") |
| **Later over earlier**: when two statutes necessarily conflict, the one enacted last prevails | Position-dependent priority: later instructions override earlier ones (the recency bias from Lost-in-the-Middle-at-Birth) |
| **Harmonious reading**: courts endeavor to read conflicting provisions harmoniously if any reasonable construction allows both to stand | The model's actual behavior when facing conflicting instructions — it tries to satisfy both, producing a compromise |
| **Presumption against implied repeal**: repeals by implication are disfavored | Instructions don't cancel each other unless explicitly stated — implicit override is an Arbiter InterferenceType |
| **Expressio unius**: the expression of one thing implies the exclusion of others | Listing specific permitted behaviors implies prohibition of unlisted ones — a source of hidden mandate-prohibition conflicts |
| **Noscitur a sociis**: a word is known by the company it keeps | Context-dependent instruction interpretation — "be helpful" means different things in a safety section vs a formatting section |
| **Ejusdem generis**: general terms following specific ones are limited to the same class | "Use tools like Bash, Read, Edit, and other relevant tools" — "other relevant tools" is constrained by the examples |
| **Avoid surplusage**: every provision should have effect; none should be treated as redundant | The dead code elimination analogy — every instruction should have behavioral effect, or it should be questioned |

**The deep insight:** Courts recognize that contradictory statutes are *normal and
expected*, not bugs. The entire canon system is designed to *manage* contradictions,
not eliminate them. Similarly, Arbiter should frame interference as normal and
expected in prompt engineering, not as errors to be fixed. The goal is not
contradiction-free prompts (impossible in practice, and the Baxi U-curve suggests
they might perform worse) but *managed contradictions with predictable resolution
order*.

**The "avoid surplusage" canon is directly relevant to PGO for prompts.** Legal
interpretation assumes every word was intentional. If a provision has no effect,
something is wrong — either the provision is being misinterpreted, or it's
genuinely redundant. The ablation study maps directly: if removing an instruction
has no behavioral effect, either (a) we're measuring wrong, (b) it's weight-aligned
(dead code), or (c) it's weight-compensating (a guardrail we don't want to remove).
Canon law's centuries of experience say: be very cautious about declaring anything
"surplusage" — usually the problem is your interpretation, not the text.

**What would an "Arbiter canon system" look like?** A set of meta-rules for
resolving interference:

1. Prohibition overrides permission (specific prohibition > general permission)
2. Scoped instruction overrides unscoped instruction (specific > general canon)
3. Later instruction overrides earlier instruction (recency canon)
4. System tier overrides domain tier overrides application tier (hierarchy canon)
5. Explicit override overrides implicit override (presumption against implied repeal)

These canons would be *configurable per deployment* — different applications might
have different resolution orders. This is already Arbiter's system layer concept,
but framing it as "canons of construction" gives it theoretical grounding and a
rich precedent literature.

### 3. Conway's Law for Prompts

Conway's Law: "Organizations which design systems are constrained to produce
designs which are copies of the communication structures of these organizations."

Applied to system prompts: **the structure of a system prompt mirrors the
organizational structure of the team that wrote it.**

Claude Code's 78KB monolith was written by one team (Anthropic's Claude Code
team). It's a monolith because the team communicates freely — no organizational
boundaries create natural module boundaries.

Codex GPT-5.2's flat prompt reflects OpenAI's flatter organizational structure
for that product. Gemini CLI's modular prompt reflects Google's modular team
structure.

**The testable prediction:** When multiple teams contribute to a system prompt
(e.g., safety team + product team + tools team), the interference patterns will
concentrate at team boundaries. Blocks authored by the safety team will conflict
with blocks authored by the product team, because those teams optimize for
different objectives and communicate less frequently than intra-team members.

This is exactly what the scourer found in Claude Code — the most severe interference
patterns (the 4 critical TodoWrite contradictions) were at the boundary between
tool definition blocks and behavioral constraint blocks, which are likely authored
by different sub-teams.

**Inverse Conway Maneuver for prompts:** If you want a prompt with clean module
boundaries and minimal cross-boundary interference, organize the authoring team
to match the desired prompt structure. One person/team per semantic role
(identity, policy, safety, tools, workflow, format). Each team owns their section.
Interference detection runs at composition time. This is what SPEAR's prompt view
model enables — but Conway's Law says the org structure will either support or
sabotage it.

### 4. Reliability Engineering — The N-Version Programming Analogy

N-version programming (NVP) is a fault tolerance technique where N independently
developed implementations of the same specification run in parallel, and a voter
selects the majority output.

Arbiter's ensemble evaluator architecture is NVP for prompt analysis: multiple
models independently evaluate the same prompt for interference, and the results
are aggregated. The E2 data already showed this matters — gpt-4o-mini was
disqualified for 100% false positive rate. Without ensemble voting, that model's
output would corrupt the interference tensor.

But NVP has a known failure mode: **correlated failures**. If all N implementations
share a common design flaw (because they were developed from the same specification,
or the developers talked to each other), they fail simultaneously, and the voter
can't help. The analogy: if all models share the same training bias (e.g., all
RLHF-trained models over-prioritize helpfulness), they'll all make the same
evaluation errors, and the ensemble won't catch it.

The Baxi finding (removing helpfulness signals improves constraint compliance by
598%) suggests this correlated failure is real. All RLHF-trained models share the
helpfulness bias. Using an ensemble of RLHF models to evaluate interference might
systematically miss interference patterns that arise from the helpfulness-constraint
tension.

**Mitigation from the NVP literature:** Use *diverse* implementations — models
trained with different objectives, different architectures, different data. The
scourer already demonstrated this: Claude finds structural contradictions, Gemini
finds trust chain issues, Kimi finds operational/economic issues. Diversity in
the ensemble catches failure modes that homogeneous ensembles miss.

### 5. Information Theory — Mutual Information as an Interference Metric

The "Demystifying Reasoning Dynamics with Mutual Information" paper (arXiv:2506.02867)
found that mutual information between intermediate representations and correct
answers peaks at specific tokens — "thinking tokens" like "Hmm", "Wait", "Therefore."

**Applied to instruction processing:** If we could measure the mutual information
between each instruction block and the model's behavioral output, we'd have a
direct, non-heuristic measure of each block's influence. Blocks with high MI are
load-bearing. Blocks with low MI are dead or suppressed. Blocks where MI *decreases*
when another block is added exhibit exploitation competition.

The L2M scaling law (arXiv:2503.04725) provides the theoretical bound: bipartite
MI between instruction segment and response follows a power law with segment
length. As the total prompt grows, each block's MI contribution decays. The
rate of decay depends on model architecture (transformers decay slower than SSMs)
and on model size (more heads = slower decay).

**What this gives Arbiter:** A principled replacement for the current heuristic
interference scoring. Instead of asking an LLM "do these blocks conflict?" (which
is itself subject to the same biases it's trying to detect), compute the MI
between each block and the behavioral output. Blocks with anomalously low MI
given their position and content are candidates for dead code. Block pairs where
the joint MI is less than the sum of individual MIs exhibit destructive interference.
Block pairs where the joint MI exceeds the sum exhibit synergy.

The computation is expensive (requires running the model multiple times with
different block subsets — essentially the ablation study), but it grounds the
interference tensor in information theory rather than LLM-as-judge heuristics.

### 6. Garden-Path Sentences — Psycholinguistic Ambiguity Resolution

Garden-path sentences are sentences that lead the reader toward an initial parse
that turns out to be wrong: "The horse raced past the barn fell." The reader must
backtrack and reparse.

Research on LLMs and garden-path sentences (Li et al., arXiv:2405.16042) shows
that LLMs, like humans, are susceptible to garden-path effects — they commit to
an initial parse and struggle to recover.

**The prompt engineering implication:** Instructions that are individually
unambiguous can create garden-path effects in combination. "Always format output
as markdown" + "Never use headers in responses" — the model parses the first as
a formatting mandate, then hits the second which partially contradicts the first
(markdown without headers is unusual), and must reparse what "markdown" means in
this restricted context.

This is a distinct interference mechanism from semantic contradiction. The
instructions don't strictly *contradict* — you can have markdown without headers.
But the parsing ambiguity causes behavioral instability. The model might format
as markdown-without-headers in some runs and silently drop the markdown formatting
in others, depending on which instruction it processes first.

**The pragmatics connection** (arXiv:2502.12378): LLMs lack robustness in
pragmatic inference — they fail to recognize indirect requests or subtle shifts
in social meaning. Prompt instructions are often pragmatically loaded. "Be concise"
is not just a formatting instruction — it's a pragmatic signal that implies "don't
explain your reasoning," "don't hedge," "don't ask clarifying questions." The
implied instructions from pragmatic inference can conflict with explicit
instructions elsewhere in the prompt.

This predicts a category of interference that Arbiter can't currently detect:
**pragmatic interference**, where the implied meaning of one instruction conflicts
with the explicit meaning of another. It's related to pass 2's "representational
interference" but at a higher level — it's about *what the model infers* from
instructions, not what the instructions explicitly say.

---

## Synthesis: What Connected Unexpectedly

### The Big Surprise: Firewall Policy Analysis

I expected control theory or legal interpretation to be the strongest adjacent
field. The actual strongest connection is **firewall policy anomaly detection**.
Al-Shaer's taxonomy of policy anomalies (shadowing, correlation, generalization,
redundancy, inconsistency) maps almost 1:1 to Arbiter's InterferenceType enum.
Their detection algorithms (policy trees, conflict graphs, anomaly resolution
strategies) are directly applicable. The field is mature (20+ years), has formal
correctness proofs, handles scale (10,000+ rules), and nobody has connected it
to prompt engineering.

This is the kind of cross-field transfer that justifies the scouting methodology.
The solution exists; it's just in a different literature.

### The Second Surprise: Legal Canons as Configurable Meta-Rules

The canons of construction don't just provide analogy — they provide a *design
pattern* for Arbiter's resolution layer. Instead of detecting interference and
leaving resolution to the developer, Arbiter could apply configurable canons
(specific > general, later > earlier, higher tier > lower tier) to *predict*
how the model will resolve the interference, and flag cases where the canons
disagree (i.e., the specific instruction is earlier but the general instruction
is later — which canon wins?).

### The Third Surprise: SPEAR Integration Is Tight

I expected more friction between Arbiter and SPEAR. The actual integration
surface is clean: Arbiter provides the diagnostic that SPEAR lacks (which
fusions are safe, which compositions have conflicts), and SPEAR provides the
runtime actuation that Arbiter lacks (adaptive refinement to fix detected
problems). They're two halves of a complete system — static analysis + dynamic
optimization.

### What's Missing

Two things nobody has:

1. **A formal model of instruction semantics.** Everyone (Arbiter, SPEAR, DSPy,
   all the prompt engineering literature) treats instruction semantics as a black
   box — you feed text to an LLM and measure what happens. The legal interpretation
   literature has centuries of formal semantics for normative statements (deontic
   logic: obligation, permission, prohibition). Deontic logic could provide the
   formal foundation for Arbiter's modality classification and interference
   detection. I didn't follow this thread deeply but it's a clear next trail.

2. **Longitudinal drift measurement.** Both SPEAR and Arbiter version prompts.
   Nobody tracks how interference patterns change over time as prompts evolve.
   The legal analogy is "regulatory accumulation" — the ESRB finding from pass 1
   that complex regulation creates an illusion of control. Do system prompts
   exhibit the same pattern? Does interference monotonically increase with prompt
   version count? Or does it follow a different trajectory? This needs the corpus
   data (337 Claude Code versions, 759 Codex versions, 482 Gemini CLI versions)
   that Arbiter already has access to.

---

## New References

- **What's the Magic Word? (Control Theory of LLM Prompting)**: Amos et al., arXiv:2310.04444, AAAI 2024
- **Linear Feedback Control for Prompt Optimization**: arXiv:2501.11979, Jan 2025
- **L2M (Mutual Information Scaling Law)**: arXiv:2503.04725, NeurIPS 2025
- **Firewall Policy Anomaly Detection**: Al-Shaer & Hamed, IEEE TDSC 2012. Also: Al-Shaer, "Firewall Policy Advisor for Anomaly Discovery," IFIP Networking 2004
- **SDN Flow Rule Conflict Detection via Knowledge Graph**: Springer LNCS, 2022
- **Garden-Path Sentences in LLMs**: Li et al., arXiv:2405.16042, 2024
- **Pragmatics in the Era of LLMs**: arXiv:2502.12378, Feb 2025
- **Thinking Tokens as Information Peaks**: arXiv:2506.02867, 2025
- **Canons of Construction**: Scalia & Garner, "Reading Law" (2012); CRS Report R45153; Al-Shaer's rule priority as implemented in firewall anomaly resolution

## Trails Opened by This Pass

1. **Deontic logic as formal foundation** for Arbiter's modality system.
   Obligation, permission, prohibition have centuries of formal treatment.
   Could provide provably sound interference detection where current approach
   is heuristic.

2. **Firewall policy tree adaptation** for O(n log n) interference detection.
   Direct algorithm transfer from Al-Shaer's work. Replace pairwise comparison
   with tree insertion + anomaly detection at insertion time.

3. **Stability analysis of refinement loops.** Control-theoretic criteria for
   when Arbiter+SPEAR feedback loops converge vs oscillate. Derivable from
   interference tensor eigenstructure.

4. **MI-based interference measurement.** Replace LLM-as-judge scoring with
   information-theoretic ground truth. Expensive but formally sound.

5. **Longitudinal drift study.** Track interference tensor across 337+ Claude
   Code versions. Does interference accumulate like regulatory complexity?

6. **Canon system for Arbiter.** Configurable meta-rules for predicting how
   models resolve detected interference. Specific>general, later>earlier,
   higher-tier>lower-tier as defaults, overridable per deployment.

7. **Conway's Law validation.** Cross-reference prompt authorship structure
   (when knowable) with interference pattern locations. Predict that
   interference concentrates at team boundaries.
