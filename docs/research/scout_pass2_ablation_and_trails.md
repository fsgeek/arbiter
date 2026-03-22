# Scout Pass 2 — Ablation Study Design + Unfollowed Trails

Date: 2026-03-16
Scout model: Claude Opus 4.6
Brief: Go deeper on ablation experimental design and 3 unfollowed trails from pass 1
Depends on: scout_pass1_references.md

---

## Part 1: The Ablation Study Design

### The Empty Space Is Real

I searched hard for anyone doing instruction-level ablation of production system
prompts. The closest things I found:

1. **Brittlebench** (Romanou et al., arXiv:2603.13285, March 2026) — applies
   "semantics-preserving perturbations" to benchmark prompts and measures
   degradation. Found performance degrades up to 12%, and single perturbations
   changed model rankings 63% of the time. But this is perturbation testing of
   *task prompts*, not block-removal ablation of *system prompts*. Different
   animal.

2. **In-Context Alignment** (Huang et al., arXiv:2406.11474, 2024) — divided
   context into three categories (format, system prompt, example), ablated each.
   Found examples matter most. But this is coarse-grained: "system prompt" is
   one undifferentiated blob, not 56 classified blocks.

3. **CDCT / Compression-Decay** (Baxi, arXiv:2512.17920, 2025) — compressed
   prompts across a gradient from ~2 words to ~135 words, measured constraint
   compliance. Found a U-curve: *medium* compression is worst. More on this
   below. But still working at the whole-prompt level, not per-instruction.

4. **Seemingly Useless Features** (Rofin et al., arXiv:2603.14087, March 2026) —
   found that transformer features that appear redundant for immediate next-token
   prediction actually serve downstream purposes. Features with extreme influence
   relate to formal reasoning domains. This is the mechanistic interpretability
   version of "that instruction looks dead but isn't."

Nobody is doing what we'd be doing: take a 56-block classified system prompt,
systematically remove blocks or combinations, measure behavioral effects on the
model operating under that prompt. The gap remains wide open.

### NIST Combinatorial Testing: The Mathematical Framework

NIST SP 800-142 (Kuhn, Kacker, Lei, 2010) provides the methodology. The core
empirical finding across medical devices, browsers, servers, NASA spacecraft,
network protocols, and operating systems:

| Interaction strength | % of faults | Cumulative |
|---------------------|-------------|------------|
| 1-way               | ~60%        | ~60%       |
| 2-way               | ~30%        | ~90%       |
| 3-way               | ~7%         | ~97%       |
| 4-way               | ~2%         | ~99%       |
| 5-way               | ~1%         | ~100%      |
| 6-way               | <1%         | ~100%      |

This means: **pairwise (t=2) testing catches ~90% of all interaction faults**.
This is why the sparse pairwise tensor is theoretically justified — not just
computationally convenient, but empirically sufficient.

### Covering Arrays: The Math for 56 Blocks

A covering array CA(N; t, k, v) guarantees that every t-way combination of k
parameters with v values each appears in at least one of N test configurations.

For our problem:
- k = 56 (blocks in Claude Code v2.1.50)
- v = 2 (each block is present or absent)
- t = 2 (pairwise interactions, catching ~90% of faults)

The number of 2-tuples to cover: C(56,2) * 2^2 = 1,540 * 4 = 6,160

But covering arrays compress this dramatically. For binary parameters:
- **t=2 (pairwise): ~15 test configurations**
- **t=3 (3-way): ~30-40 test configurations**

For comparison, full factorial = 2^56 = 72 quadrillion configurations.
Pairwise coverage gives a **~5 * 10^15 x reduction**.

NIST's ACTS tool (free, public domain, 4,500+ users) generates these arrays
automatically using the IPOG algorithm (In-Parameter-Order General). We'd feed
it 56 binary parameters and get back ~15 rows, each specifying which blocks to
include and which to exclude.

### What Would the Experiment Actually Look Like?

**Pilot design (minimum viable):**

Phase 0: Single-block ablation (56 runs)
- Remove one block at a time, run behavioral battery
- Identifies blocks with main effects (the ~60% of interactions)
- Cheap, simple, immediately informative
- Some blocks will be identity/safety-critical; those get flagged
- Some blocks will be "dead" — removal changes nothing

Phase 1: Pairwise ablation (~15 runs from covering array)
- Each run has a different subset of blocks present/absent
- Covering array guarantees every pair of blocks is tested
- together-present, together-absent, one-present-one-absent
- Detects the ~30% of interactions that are pairwise

Phase 2 (stretch): 3-way ablation (~35 runs)
- Catches the additional ~7% from 3-way interactions
- Important because Tekin et al.'s hidden suppression finding
  suggests higher-order interactions may be more common in
  "soft" systems than in traditional software

**The measurement battery:**

This is the harder design question. What do you measure when you remove
Block 17? Options, from cheapest to richest:

1. **Task completion** — can the model still do the thing? (Y/N per task)
   - Cheap, binary, low information density
   - Misses behavioral shifts that don't cause outright failure

2. **Instruction adherence** — for each remaining block's instructions,
   does the model still follow them?
   - Directly measures interference: "removing Block 17 causes
     violations of Block 3's mandate"
   - Medium cost: needs LLM-as-judge per block per test config
   - This is what the interference tensor *is*

3. **Behavioral fingerprinting** — run the same N prompts under each
   config, compare output distributions
   - Richest signal: detects any behavioral shift, not just violations
   - Expensive: needs many samples for statistical power
   - But picks up the "hidden suppression" effects Tekin found

4. **Constraint compliance** (Baxi's method) — test specific constraint
   types (format, length, content) with and without blocks
   - Good for detecting the RLHF/instruction tension
   - Targeted but narrow

The right answer is probably **instruction adherence (option 2) with selective
behavioral fingerprinting (option 3) on high-interest pairs**.

**Cost estimate:**

For pairwise coverage with instruction adherence measurement:
- 15 test configurations (covering array)
- 20 behavioral probes per configuration (task battery)
- ~$0.03 per API call
- Total: ~300 calls, ~$9

For single-block + pairwise + fingerprinting:
- 56 + 15 = 71 configurations
- 20 probes each + 50 fingerprinting prompts on 15 high-interest configs
- ~2,170 API calls, ~$65

This is absurdly cheap. The bottleneck is *designing the behavioral battery*,
not running it.

### Methodological Pitfalls

**1. The dead instruction problem.** Some blocks may appear removable because
the model's trained behavior already covers them. Breunig's "fighting the
weights" observation: instructions that compensate for trained behavior look
like dead code but serve as guardrails against behavioral drift across model
versions. Single-version ablation will miss this.

**2. Position confounds.** Lost in the Middle at Birth (arXiv:2603.10123) proved
the U-shaped attention curve is architectural. Removing a block from position 17
changes the positions of blocks 18-56. The ablation tests *position effects* and
*content effects* simultaneously. Mitigation: also test *replacing* removed
blocks with neutral padding to preserve positional structure.

**3. The Baxi U-curve.** CDCT found that medium compression produces worse
compliance than extreme compression. Removing a few blocks may be worse than
removing many. The response surface may be non-monotonic.

**4. Interaction with RLHF-trained behavior.** Baxi's key finding: removing
"helpfulness" signals improves constraint compliance by 598%. Some system prompt
blocks may *suppress* desirable trained behavior. The ablation might find that
removing certain blocks *improves* performance — the hidden suppression
analogue from Tekin et al.

**5. Model-specificity.** E2 data from Arbiter already shows bimodal behavior:
gpt-4o-mini and llama-4-maverick show 16% discrimination while gpt-5-mini,
gemini-2.0-flash, and claude-haiku-4.5 cluster at ~7%. Any ablation study
must run on multiple models or its findings don't generalize.

**6. Measurement sensitivity.** Brittlebench found that semantics-preserving
perturbations change model rankings 63% of the time. Our measurement battery
must be robust enough that signal > noise from the measurement itself.

### The Experimental Design from Combinatorial Testing

The specific technique to use is a **mixed covering array with constraints**.

Not all 56 blocks are independent binary toggles. Some form groups:
- Identity blocks (1-2): probably can't remove without breaking the model
- Safety blocks (3-4): removing is ethically problematic
- Tool schema blocks (28): removing these removes capabilities, not behaviors

The real ablation targets are the ~23 behavioral blocks (workflow, format,
scope guidance). Constrain the covering array: identity and safety blocks
always present, tool blocks always present (or ablated separately in their
own array). The behavioral covering array becomes CA(N; 2, 23, 2) which
needs only ~10-12 configurations.

ACTS supports constraints natively. You declare "parameter 1 must always
be value 1" and the algorithm respects this while generating the covering
array for the remaining free parameters.

### What Adjacent Fields Tell Us

**A/B testing at scale** (Microsoft Experimentation Platform, Google DIXO):
They run thousands of overlapping experiments simultaneously and have
developed methods for detecting interaction effects. Key insight: most
experiments don't interact, which is why they can overlap. When interactions
*are* found, they're usually multiplicative, not additive. This matches
the NIST pairwise finding from a different direction.

**Feature flag experiments**: Modern software deploys behind feature flags —
binary toggles for whether a capability is active. The analogy to prompt blocks
is exact. But feature flag experiments measure *user metrics* (click-through,
revenue), not *behavioral fidelity*. Nobody in the feature flag world measures
"does enabling Feature X cause Feature Y to misbehave" — they measure "does
enabling Feature X improve the KPI." We need the former.

**Drug interaction testing**: Tekin et al.'s 54% hidden suppression rate was
for 5-drug combinations specifically. For pairs, hidden suppression is rarer
but still present (~15-20% of pairs). For system prompts, the prediction
would be: ~15-20% of block pairs have hidden interference that you can't
detect by testing blocks individually. This is the pairwise value proposition.

---

## Part 2: The Unfollowed Trails

### Trail 1: The Compiler Optimization Parallel

Nobody has published this connection explicitly. I searched every plausible
query across arXiv and found zero papers drawing the analogy between compiler
optimization passes and prompt optimization. The closest thing is prompt
compression work (LLMLingua and descendants), which operates at the token
level — analogous to minification, not optimization.

But the parallel is structurally exact and worth spelling out:

| Compiler Pass | Prompt Analogue | Status |
|---------------|----------------|--------|
| Dead code elimination | Remove instructions with no behavioral effect | Untested |
| Constant propagation | Replace variable instructions with fixed values when model always chooses the same | Untested |
| Common subexpression elimination | Merge redundant scope overlaps | Arbiter detects 13 of these in Claude Code |
| Strength reduction | Replace expensive mandate+prohibition with simpler prohibition-only | Empirically validated (prohibition > mandate) |
| Inlining | Expand cross-references ("see above") to avoid attention gaps | Lost-in-the-Middle predicts this helps |
| Register allocation | Optimize instruction placement for attention budget | Lost-in-the-Middle at Birth provides the cost model |
| Unreachable code elimination | Remove instructions for features that are disabled | Gemini CLI's feature flags make this literal |
| Loop unrolling | Repeat critical instructions at multiple positions | Context Rot suggests this helps |

The key insight is that **dead code elimination requires the ablation study
to define "dead."** In compilers, dead code is provably unreachable. In
prompts, "dead" means "no behavioral effect when removed" — but only testable
empirically, because the execution model (the LLM) is a black box.

This creates a circular dependency: you need the ablation study to identify
dead instructions, but you need to know which instructions are dead to design
an efficient ablation study. The NIST covering array breaks this circularity
by testing *all pairwise combinations* without knowing which matter.

**The deeper parallel**: compiler optimization has a fixed-point property.
You run passes repeatedly until nothing changes. DCE might expose new
constant propagation opportunities, which might expose new dead code.
Prompt optimization would have the same property: removing redundant
instructions might reveal new conflicts that were previously masked by
the redundancy, which might make other instructions removable.

This predicts an **iterative ablation cycle**, not a one-shot experiment.

**What surprised me**: the "seemingly useless features" paper (Rofin et al.,
2026) provides the mechanistic explanation for why dead instruction elimination
is dangerous. Features that appear useless for immediate prediction serve
downstream purposes. Translated: an instruction that appears to have no
effect on the current task may be stabilizing behavior on future tasks, or
preventing a behavioral mode that the instruction implicitly suppresses.
"Dead" in the compiler sense (provably no effect) may not exist in the
LLM sense (statistically no *detectable* effect at current sample size).

### Trail 2: Constitutional AI vs Runtime Instructions (Fighting the Weights)

This trail turned up something genuinely important.

**The Baxi result** (arXiv:2512.17920) is the empirical anchor. The finding:
removing "helpfulness" signals from prompts improves constraint compliance by
598% (71/72 trials, p<0.001), with 79% achieving *perfect* compliance after
removal. The U-curve: medium-length prompts produce worse compliance than
either very short or very long prompts.

The mechanism they propose: RLHF training creates a strong drive toward
helpfulness. When a system prompt instruction conflicts with being helpful
(e.g., "refuse to answer questions about X"), the model experiences a tug-of-war
between trained behavior and runtime instruction. At medium prompt lengths,
there's enough instruction to activate the conflict but not enough to
decisively override the training.

**The ASCL paper** (Wang et al., arXiv:2602.13562, 2026) goes further. They
argue that context distillation — the technique of baking system prompt
behavior into model weights — creates "rigid associations between rule
memorization and refusal behaviors." Their solution: make safety consultation
*optional and tool-mediated* rather than weight-encoded. The model decides
when to check the rules rather than having rules permanently active.

This connects directly to Breunig's "fighting the weights" observation.
The taxonomy of instructions expands:

1. **Weight-aligned instructions**: things the model already does. These
   are genuinely dead code — they pass through with no effect.
2. **Weight-compensating instructions**: things that override trained
   behavior. These *look* dead (model does the right thing) but are load-
   bearing (remove them and trained behavior reasserts).
3. **Weight-conflicting instructions**: things that fight trained behavior
   and *lose*. The model ignores them. Control Illusion (arXiv:2502.15851)
   showed these exist — the model encodes the conflict but doesn't act on it.
4. **Weight-novel instructions**: things the model has no trained behavior
   for. These depend entirely on in-context learning and are fragile.

**The ablation study must distinguish these four categories.** A block that's
"dead" in category 1 is safe to remove. A block that's "dead" in category 2
is a landmine. A block that's "dead" in category 3 was never working.
A block in category 4 is the most vulnerable to position effects and context rot.

The multi-model dimension matters here too. Different models have different
trained behaviors, so the same instruction may be category 1 for one model
and category 2 for another. This predicts that **ablation results are
model-specific** — which is exactly what the E2 bimodal finding suggests.

**What surprised me**: the Baxi U-curve implies that *adding instructions can
make things worse*. Not just neutral — actively harmful. This inverts the
typical prompt engineering assumption that more specific = better. There's an
optimal instruction density, and exceeding it causes the RLHF-helpfulness
drive to overwhelm explicit constraints. This is the pharmacological hidden
suppression transferred to prompt engineering: the prompt is the drug cocktail,
and some instructions suppress others.

### Trail 3: Cognitive Load Theory (Sweller)

No papers directly apply Sweller's Cognitive Load Theory to LLM instruction
processing. But two papers circle close:

1. **Cognitive Overload Attack** (Upadhayay et al., arXiv:2410.11272, 2024)
   explicitly invokes cognitive load theory to explain LLM jailbreaking.
   Excessive contextual demands cause safety-trained systems to fail.
   Successfully jailbroke GPT-4, Claude 3.5 Sonnet, Llama-3-70B, Gemini
   with up to 99.99% success rates.

2. **Selection Bias and Cognitive Load** (Eicher & Irgolic, arXiv:2402.01740,
   2024) proposes that "LLMs experience a form of cognitive load that is
   compensated for with bias." More complex tasks produce stronger primacy
   effects in list selection.

Sweller's framework has three types of cognitive load:
- **Intrinsic**: inherent complexity of the material (instruction semantics)
- **Extraneous**: complexity from poor presentation (format sensitivity)
- **Germane**: productive processing that builds understanding (in-context learning)

The mapping to LLM instruction processing:

| Sweller Type | LLM Analogue | Arbiter Finding |
|-------------|-------------|-----------------|
| Intrinsic | Semantic complexity of the instruction | Prohibition beats mandate (simpler = better) |
| Extraneous | Format, position, redundancy | Format sensitivity 0-100% (Haiku), Context Rot |
| Germane | Building task-specific context | Minimalism wins (less germane load = better) |

The Cognitive Overload Attack paper implies an **attention budget** model
where instruction processing has a finite capacity. This explains several
Arbiter findings simultaneously:

- **Minimalism wins**: fewer instructions = less total load = more capacity
  per instruction
- **Prohibition > mandate**: prohibitions are lower-intrinsic-load than
  mandates (don't do X is simpler than do X in way Y)
- **Context Rot degrades with length**: more tokens = more load = each
  instruction gets less processing
- **Position effects (U-curve)**: beginning and end get disproportionate
  processing; middle instructions get whatever's left

**The key prediction**: there should be a measurable *capacity threshold*
beyond which adding instructions degrades processing of all instructions.
The Baxi U-curve may be exactly this threshold. And the threshold should
scale with model size — larger models have more attention heads, more
parallel processing capacity, higher thresholds.

This also reframes the ablation study: you're not just testing whether
Block 17 interferes with Block 3. You're testing whether Block 17
*consumes attention budget* that Block 3 needed. The interference
mechanism isn't semantic contradiction — it's resource competition.

**The ecological niche connection opens up here.** Case & Gilpin (1974)
distinguished exploitation competition (competing for the same resource)
from interference competition (directly disrupting the competitor).
In the attention budget model:
- **Exploitation competition**: two instructions compete for the same
  attention capacity. Neither contradicts the other, but processing both
  dilutes processing of each. This is Context Rot.
- **Interference competition**: one instruction actively disrupts processing
  of another. This is mandate-prohibition conflict. The model must choose.

These predict different ablation signatures:
- Exploitation: removing any block from an overloaded section improves
  processing of remaining blocks (irrespective of which block you remove)
- Interference: removing *specific* blocks improves processing of *specific*
  other blocks (the tensor has sparse, targeted entries)

The pairwise covering array tests both, but they're distinguishable in
the resulting tensor: exploitation produces dense rows/columns (many blocks
affected equally), interference produces sparse entries (specific pairs).

### Trail 4: Superposition and Polysemanticity (Bonus — Followed Further Than Expected)

This trail opened up more than I expected.

**Dual Encoding** (Claflin, arXiv:2507.00269, 2025) proposes that neural
networks encode information in two complementary spaces: feature identity
and feature integration. Standard sparse autoencoders (SAEs) assume linear
superposition and consistently fail to eliminate polysemanticity. The dual
encoding hypothesis: 3% of parameters (nonlinear integration features)
account for 16.5% of performance, and these integration features show
"selective sensitivity to experimental manipulations."

**Unified Theory of SAE Failures** (Tang et al., arXiv:2512.05534, 2025)
provides the theoretical framework for why linear decomposition fails:
polysemantic features, feature absorption, and dead neurons are
mathematically inevitable consequences of biconvex optimization.

The connection to instruction interference: if model features are
nonlinearly composed, then instruction A and instruction B may share
features in ways that can't be decomposed into A + B. The interference
is at the *representational level*, not just the *semantic level*. Two
instructions that are semantically non-contradictory may still interfere
because they activate overlapping feature integrations.

This predicts a category of interference that Arbiter can't currently
detect: **representational interference**, where instructions don't
contradict each other in meaning but compete for the same internal
feature directions. Only the ablation study could reveal these — they'd
show up as unexplained behavioral changes when seemingly unrelated
blocks are removed together.

The MoE literature (Mehta et al., arXiv:2508.01261; Pu et al.,
arXiv:2509.07945) provides a different angle: routing conflicts in
mixture-of-experts models where different instructions activate the
same experts. This is the ecological niche theory realized in hardware:
instructions compete for expert capacity the way species compete for
ecological niches.

---

## Synthesis: What This Changes

### For the ablation study design:

1. **Use NIST covering arrays.** The math is solved. ACTS generates the
   test matrix. For 23 free behavioral parameters (constrained covering
   array excluding identity/safety/tool blocks), pairwise coverage needs
   ~10-12 configurations. Total cost under $50.

2. **Include single-block ablation as Phase 0.** It's cheap (23 runs),
   identifies main effects (60% of interactions), and classifies blocks
   into the four weight-relationship categories.

3. **Measure instruction adherence, not just task completion.** The
   interference tensor *is* the measurement: for each block pair, does
   removing one change adherence to the other?

4. **Control for position effects.** Replace removed blocks with neutral
   padding to preserve positional structure. Run a parallel "position-only"
   condition where blocks are shuffled but all present.

5. **Run on at least 3 model families.** The E2 bimodal finding means
   single-model results don't generalize.

6. **Design for the U-curve.** Don't assume monotonic effects. Measure at
   multiple removal counts (1, 5, 10, 20 blocks removed) to map the
   response surface.

### For the paper:

The combinatorial testing connection deserves a paragraph in Related Work
and a more prominent role in the experimental design section. The NIST
data justifies the sparse tensor architecture; the covering array
methodology justifies the ablation study as feasible.

The compiler optimization parallel is a framing device for the entire
project. Arbiter is a prompt linter/compiler-warning system. The ablation
study is the equivalent of a profile-guided optimization pass.

### New references to add:

- **Brittlebench**: Romanou et al., arXiv:2603.13285 (March 2026)
- **CDCT / Compression-Decay**: Baxi, arXiv:2512.17920 (2025)
- **ASCL / Safety-Utility Trade-off**: Wang et al., arXiv:2602.13562 (2026)
- **Seemingly Useless Features**: Rofin et al., arXiv:2603.14087 (March 2026)
- **Dual Encoding**: Claflin, arXiv:2507.00269 (2025)
- **Cognitive Overload Attack**: Upadhayay et al., arXiv:2410.11272 (2024)
- **Selection Bias as Cognitive Load**: Eicher & Irgolic, arXiv:2402.01740 (2024)
- **NIST SP 800-142**: Kuhn, Kacker, Lei (2010) — the covering array tutorial
- **MoE Routing Conflicts**: Mehta et al., arXiv:2508.01261 (2025)

### Trails that opened from these trails:

1. **Profile-guided prompt optimization** — run the ablation study, identify
   dead/harmful blocks, remove them, repeat. Fixed-point iteration. Nobody
   has done this.

2. **Attention budget capacity curves** — the cognitive load / Baxi U-curve
   connection predicts measurable capacity thresholds that scale with model
   size. Testable.

3. **Exploitation vs interference taxonomy** — dense vs sparse patterns in
   the ablation tensor distinguish two fundamentally different failure modes.
   Different mitigations for each.

4. **Weight-relationship classification** — the four-category taxonomy
   (aligned/compensating/conflicting/novel) predicts which instructions are
   fragile to model updates. Testable across model versions.

5. **Representational interference** — instructions that don't semantically
   conflict but share feature directions. Only detectable by ablation, not
   by rule-based analysis. The dual encoding paper suggests this is nonlinear
   and accounts for a meaningful fraction of total interference.
