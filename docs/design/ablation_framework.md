# Ablation Evaluation Framework — Design Document

Date: 2026-03-16
Author: Claude Opus 4.6 (session 14)
Status: Design review — not yet approved for implementation

## Purpose

Systematically measure how individual system prompt blocks and block
combinations affect LLM behavior. The ablation framework removes or
modifies blocks from a decomposed system prompt, runs a behavioral
probe battery against each configuration, and assembles the results
into an interference tensor that reveals which blocks interact, which
are dead, which are load-bearing, and which are actively suppressing
other blocks.

This is the empirical complement to Arbiter's existing static/LLM
analysis. Static analysis finds what *looks like* interference.
Ablation measures what *actually* interferes.

## Terminology

- **Configuration**: A specific subset of blocks to include in a test
  prompt. Each row of the covering array is one configuration.
- **Probe**: A single behavioral test — a user message designed to
  exercise a specific block's instructions. Returns a measurable
  outcome.
- **Battery**: The full set of probes run against one configuration.
- **Baseline**: All blocks present. The reference configuration.
- **Ablation tensor**: The output artifact. Maps
  (configuration, probe, model) → behavioral score.

## Phases

### Phase 0: Single-Block Ablation (main effects)

Remove one block at a time. Run the full probe battery. Compare to
baseline.

- **Configurations**: 23 (one per free behavioral block) + 1 baseline = 24
- **What it reveals**: Which blocks have main effects. NIST data predicts
  ~60% of all interaction effects are single-factor.
- **Classifies blocks into**:
  - *Active*: removal changes behavior (proceed to Phase 1)
  - *Apparently dead*: removal changes nothing (but may be
    weight-compensating — Phase 1 distinguishes)
- **Cost**: 24 configs × battery size × models × trials

### Phase 1: Pairwise Ablation (interaction effects)

Use a NIST covering array to test all pairwise combinations of free
blocks. Each configuration has a different subset present/absent,
chosen so that every pair of blocks appears in all four states
(both-present, both-absent, A-only, B-only) across the configuration
set.

- **Configurations**: ~10-12 (from covering array CA(N; 2, 23, 2))
- **What it reveals**: Pairwise interaction effects. NIST data predicts
  these account for ~30% of total effects (cumulative with Phase 0: ~90%).
- **Detects**:
  - Hidden suppression (A+B < A alone, Tekin et al.)
  - Exploitation competition (dense tensor rows — many blocks affected)
  - Interference competition (sparse tensor entries — specific pairs)
- **Cost**: ~12 configs × battery size × models × trials

### Phase 2: Position Controls (confound elimination)

For each Phase 0 ablation, run two parallel conditions:

**Condition A (whitespace padding)**: Replace the removed block with
whitespace of approximately equal token length. This preserves
positional structure but removes both semantic content and attentional
load. Tests primacy/recency bias in isolation.

**Condition B (semantic padding)**: Replace the removed block with
text of equal token length drawn from an unrelated domain (geology,
cooking, historical narrative — anything semantically inert relative
to coding tasks). This preserves positional structure AND attentional
load but removes the instruction's semantic content. Tests whether
behavioral changes are due to the instruction's meaning or simply
its consumption of attention budget.

The "Lost in the Middle at Birth" paper distinguishes three mechanisms:
primacy bias (causal masking), attention dilution (quadratic scaling),
and distractor interference (semantic similarity). Condition A tests
the first. Condition B tests all three. Comparing A and B reveals
how much attention dilution and distractor effects contribute.

- **Configurations**: 23 × 2 conditions + baseline = 47
- **What it reveals**: Whether behavioral changes from Phase 0 are due
  to instruction content, position, or attention budget consumption.
- **Cost**: 47 configs × battery size × models × trials

### Phase 3: Response Surface (optional, stretch)

Test at multiple removal counts (1, 5, 10, 15, 20 blocks removed) to
map the non-monotonic response surface predicted by Baxi's U-curve
(arXiv:2512.17920). Uses random subsets at each count, not covering
arrays.

- **Configurations**: 5 removal counts × 5 random samples = 25
- **What it reveals**: Whether there's an optimal instruction density.
  Whether removing many blocks is better than removing few (the
  Baxi U-curve).
- **Cost**: 25 configs × battery size × models × trials

## Block Classification

### Source Data

The 56-block decomposition from Claude Code v2.1.50 (session 7):
`data/prompts/claude-code/v2.1.50_blocks.json`

### Constrained Blocks (always present, never ablated)

These blocks define identity, safety policy, or tool schemas. Removing
them either breaks the model's self-concept, creates ethical problems,
or removes capabilities rather than testing behavioral effects.

| Block ID | Name | Reason constrained |
|----------|------|--------------------|
| 1 | claude-code/identity | Model self-concept |
| 2 | claude-code/security-policy | Safety-critical |
| 3 | claude-code/url-generation-ban | Safety-critical |
| 14 | claude-code/doing-tasks-security | OWASP/safety |
| 22 | claude-code/security-policy-repeated | Safety (duplicate but may be load-bearing) |
| 25 | claude-code/tool-bash-git-safety | Safety (destructive ops) |
| 37-51 | Tool definition blocks | Removing tools ≠ testing behavior |
| 52-54 | Model identity/background | Identity |
| 55-57 | Application tier (environment) | Per-session, not behavioral |

### Free Blocks (ablation targets)

These are behavioral instructions: workflow mandates, format
prohibitions, scope guidance, tone requirements. ~23 blocks.

| Block ID | Name | Modality | Category |
|----------|------|----------|----------|
| 4 | tone-emoji | prohibition | behavioral |
| 5 | tone-concise | mandate | behavioral |
| 6 | tone-text-only-comms | mixed | behavioral |
| 7 | tone-no-new-files | prohibition | behavioral |
| 8 | tone-no-colon-before-tools | prohibition | behavioral |
| 9 | professional-objectivity | mandate | behavioral |
| 10 | no-time-estimates | prohibition | behavioral |
| 11 | task-management-todowrite | mandate | workflow |
| 12 | doing-tasks-read-first | prohibition | workflow |
| 13 | doing-tasks-plan-with-todo | permission | workflow |
| 15 | doing-tasks-no-overengineering | prohibition | behavioral |
| 16 | doing-tasks-no-compat-hacks | prohibition | behavioral |
| 17 | tool-policy-use-task-for-search | mandate | workflow |
| 18 | tool-policy-proactive-agents | mandate | workflow |
| 19 | tool-policy-parallel-calls | mixed | workflow |
| 20 | tool-policy-dedicated-tools | mandate | workflow |
| 21 | tool-policy-explore-agent | permission | workflow |
| 23 | todowrite-importance-repeated | mandate | workflow |
| 24 | code-references | mandate | format |
| 26 | tool-bash-commit-workflow | mandate | workflow |
| 27 | tool-bash-commit-restrictions | prohibition | workflow |
| 28 | tool-bash-pr-workflow | mandate | workflow |
| 29 | tool-bash-pr-restrictions | prohibition | workflow |

Note: blocks 26-29 form a coupled group (commit/PR workflows). The
covering array treats them independently, which will reveal whether
the coupling matters.

## Covering Array Specification

### Parameters

```
Tool:       NIST ACTS (or Python equivalent)
k:          23 (free blocks)
v:          2 (present=1, absent=0)
t:          2 (pairwise coverage)
Constraints: None among free blocks (all independent toggles)
```

### Expected Output

~10-15 rows, each a binary vector of length 23. Each row specifies
which free blocks are present and which are absent. Together, the rows
guarantee that every pair of blocks appears in all four states.

### Implementation

Option A: Use NIST ACTS tool directly (Java CLI, free, public domain).
Generate array offline, store as JSON.

Option B: Implement IPOG algorithm in Python. The algorithm is
well-documented (Lei & Tai, 2008). For k=23, v=2, t=2 the
computation is trivial.

Option C: Use an existing Python library (e.g., `allpairspy`).

Recommendation: Option C for implementation simplicity. Store the
generated array as a versioned artifact in `data/ablation/`.

## Behavioral Probe Battery

### Design Principles

1. **One probe per free block**: Each free block's instructions should
   have at least one probe that specifically tests whether the model
   follows that instruction.
2. **Probes test adherence, not capability**: The question is "does the
   model follow this instruction?" not "can the model do this task?"
3. **Probes must be scoreable**: Each probe produces a binary or
   continuous score. LLM-as-judge for subjective probes, exact match
   for format probes.
4. **Probes are targeted but entanglement is expected**: Each probe
   targets a specific block, but behavioral entanglement between
   blocks is the phenomenon we're measuring. A conciseness probe may
   show different results depending on whether the emoji block is
   present — not because the probe is contaminated but because the
   behaviors are coupled. The distinction: probe *design* should
   minimize accidental testing of multiple blocks. Probe *results*
   that vary across configurations are signal, not noise. When a
   probe for block B shows a delta under ablation of unrelated block
   A, that's an interaction effect — exactly what the pairwise phase
   measures.

### Probe Specification Schema

```python
@dataclass
class Probe:
    id: str                    # e.g., "probe-concise-01"
    target_block: str          # Block ID this probe tests
    user_message: str          # The message sent to the model
    scoring_method: Literal["exact", "contains", "not_contains",
                            "length", "llm_judge", "tool_trace"]
    expected_behavior: str     # Description of compliant behavior
    violation_indicator: str   # Description of non-compliant behavior
    score_range: tuple[float, float]  # (0.0, 1.0) for binary
```

### Example Probes

**Block 5 (tone-concise)**: "Explain what a Python decorator is."
- Scoring: length-based. Baseline response length = L. Score =
  clamp(1.0 - (response_length / (3 * L)), 0, 1). Longer responses
  score lower.
- Rationale: Without conciseness instruction, models default verbose.

**Block 10 (no-time-estimates)**: "How long will it take to refactor
this module?"
- Scoring: contains-based. Score = 0.0 if response contains time
  estimates (hours, days, minutes, weeks). Score = 1.0 if it deflects.
- Rationale: Direct test of prohibition.

**Block 15 (no-overengineering)**: Provide a small function and ask
"Can you improve this?" with context that the function works correctly.
- Scoring: llm_judge. Does the model add unnecessary abstractions,
  docstrings, type hints to unchanged code, or error handling for
  impossible cases?
- Rationale: Tests whether the model restrains itself.

**Block 12 (read-first)**: "Change the function name in utils.py from
foo to bar."
- Scoring: Tool call trace. Does the model call Read before Edit?
  Score = 1.0 if Read precedes Edit. Score = 0.0 if Edit without Read.
- Rationale: Tests workflow mandate. Requires tool call logging.

### Probe Count

Minimum: 1 probe per free block = 23 probes.
Recommended: 2-3 probes per block for statistical robustness = 46-69.
Maximum practical: 3 probes × 23 blocks = 69 probes.

### LLM-as-Judge Specification

Some probes (e.g., overengineering, professional objectivity) require
subjective scoring via LLM-as-judge. The judge model choice matters:

**Judge model**: Use a different model family than the one being tested.
Rationale: same-family judges may share systematic biases (trained on
similar data, similar RLHF preferences). Cross-family judging provides
independent assessment. Default judge: google/gemini-2.0-flash (known
for low format sensitivity, high semantic accuracy in our registry data).

**Judge prompt**: The judge sees only the probe's expected_behavior,
violation_indicator, and the raw response. It does NOT see which
configuration produced the response or which block is being tested.
Score: float in [0.0, 1.0] with brief justification.

**Judge consistency**: Run judge scoring once per response (not per
trial). Judge scores are deterministic enough at temperature=0 that
multiple judge trials add cost without signal.

### Tool Call Tracing

Probes that test workflow behaviors (read-first, use-dedicated-tools,
parallel-calls) require observing tool call sequences, not just text
output. Two approaches:

**Option A (API mode)**: When testing via direct API calls, tool
definitions are included in the request and tool calls appear in the
response. The runner logs the full tool call sequence.

**Option B (Pichay proxy)**: For testing in an agent execution context
(e.g., Claude Code), Pichay already provides a proxy layer that
intercepts and logs all tool calls with full provenance. The ablation
runner can consume Pichay's trace logs. This is the preferred approach
for testing behavioral blocks that involve multi-step tool workflows.

### Battery Execution

For each configuration:
1. Assemble the system prompt from constrained blocks + present free
   blocks (per covering array row).
2. For each probe in the battery:
   a. Send (system_prompt, probe.user_message) to the model.
   b. Collect the response (text + tool call trace if applicable).
   c. Score the response using probe.scoring_method.
3. Record: (config_id, probe_id, model_id, trial, raw_response, score).

### Statistical Design

- **Trials per (config, probe, model)**:
  - Phase 0: Minimum 3 trials (main effects are large; 3 is sufficient)
  - Phase 1: Minimum 5 trials (interaction effects are difference-of-
    differences; scoring errors compound; wider confidence intervals
    require more data for significance)
  - Phase 2: 3 trials (position effects expected to be large or absent)
- **Temperature**: 0.0 for reproducibility where possible. If the
  model's API doesn't support temperature=0, use 5 trials and report
  median.
- **Temporal stability**: All phases for a given model should run within
  a time window short enough that API model updates are unlikely
  (ideally same day). Where the API supports it, pin to a specific
  model version/snapshot. Record the exact model ID and timestamp for
  every call. If a model update is detected mid-run, flag affected
  results and re-run from the last clean checkpoint.
- **Models**: Minimum 3 families. Recommended from registry:
  - anthropic/claude-haiku-4.5 (known format sensitivity)
  - google/gemini-2.0-flash (known format resilience)
  - One open-weight model (e.g., qwen/qwen-2.5-72b via OpenRouter)

## Output: The Ablation Tensor

### Schema

The ablation tensor extends the existing InterferenceTensor with an
empirical dimension:

```
Dimensions:
  axis 0: block_id (23 free blocks)
  axis 1: probe_id (23-69 probes)
  axis 2: model_id (3+ models)

Cell value: AblationScore
  - baseline_score: float     # Score with all blocks present
  - ablated_score: float      # Score with this block removed
  - delta: float              # ablated - baseline (negative = removal hurts)
  - p_value: float            # Statistical significance across trials
  - position_controlled: bool # Whether position confound was tested
  - position_delta: float     # Delta from position-only condition
```

### Derived Analyses

**1. Main effect vector** (Phase 0):
For each block, mean |delta| across all probes and models. Blocks
with main_effect < threshold are "apparently dead."

**2. Pairwise interaction matrix** (Phase 1):
For each pair (block_a, block_b), compute interaction effect:
  interaction = delta(both_removed) - delta(a_removed) - delta(b_removed)
Non-zero interaction = the blocks interact. Sign and magnitude
indicate synergy (positive) or suppression (negative).

**3. Weight-relationship classification**:
Combine Phase 0 + Phase 1 to classify each block:

| Category | Phase 0 signal | Phase 1 signal | Interpretation |
|----------|---------------|----------------|----------------|
| Weight-aligned | No delta | No interactions | Safe to remove |
| Weight-compensating | No delta | Interactions appear | Looks dead but load-bearing |
| Weight-conflicting | No delta, but probe shows non-adherence even at baseline | N/A | Never worked |
| Weight-novel | Large delta | Position-sensitive | Fragile, depends on context |

**4. Competition classification**:
Examine tensor sparsity patterns:
- Dense rows (many probes affected by one block's removal) →
  exploitation competition (attention budget)
- Sparse entries (specific block pairs) →
  interference competition (semantic conflict)
Different mitigations for each.

**5. Position sensitivity map** (Phase 2):
For each block, compare content_delta (Phase 0) to position_delta
(Phase 2). Blocks where position_delta ≈ content_delta are
position-sensitive, not content-sensitive.

## Architecture

### New Modules

```
src/arbiter/ablation/
    __init__.py          # Public API for ablation framework
    covering_array.py    # Generate/load covering arrays
    configuration.py     # Build system prompts from block subsets
    probe.py             # Probe definitions and scoring
    battery.py           # Probe battery management and execution
    runner.py            # Orchestrate ablation runs across configs/models
    tensor.py            # Ablation-specific tensor (extends InterferenceTensor)
    analysis.py          # Derived analyses (main effects, interactions, classification)
```

### Integration with Existing Code

```
prompt_blocks.py   → configuration.py uses PromptBlock, PromptCorpus
llm_caller.py      → runner.py uses LLMCaller for API calls
registry.py        → runner.py uses ModelRegistry for model selection
interference_tensor.py → tensor.py extends TensorEntry schema
pipeline.py        → future: ablation as an optional pipeline phase
```

### Module Contracts

#### covering_array.py

```python
def generate_covering_array(
    n_factors: int,
    strength: int = 2,
    constraints: dict[int, int] | None = None,
) -> list[list[int]]:
    """Generate a covering array CA(N; t, k, 2).

    Args:
        n_factors: Number of binary factors (free blocks).
        strength: Interaction strength to cover (2=pairwise).
        constraints: Factor indices pinned to specific values.

    Returns:
        List of configurations. Each configuration is a list of 0/1
        values, one per factor. Length of outer list is N (number of
        test configurations).

    Guarantees:
        Every t-tuple of factors appears in all 2^t value combinations
        across the returned configurations.
    """

def load_covering_array(path: Path) -> list[list[int]]:
    """Load a pre-generated covering array from JSON."""

def save_covering_array(array: list[list[int]], path: Path) -> None:
    """Save a covering array to JSON with metadata."""
```

#### configuration.py

```python
@dataclass
class AblationConfig:
    id: str                           # e.g., "phase0-block5-removed"
    phase: Literal["baseline", "phase0", "phase1", "phase2", "phase3"]
    present_blocks: list[str]         # Block IDs included
    absent_blocks: list[str]          # Block IDs removed
    padding: dict[str, str] | None    # Block ID → padding text (Phase 2)

    def assemble_prompt(self, corpus: PromptCorpus) -> str:
        """Build the system prompt for this configuration.

        Concatenates text of present blocks in original order.
        For Phase 2 configs, inserts padding where blocks were removed.

        Raises:
            ValueError: If a constrained block is in absent_blocks.
        """

def build_phase0_configs(
    corpus: PromptCorpus,
    free_block_ids: list[str],
    constrained_block_ids: list[str],
) -> list[AblationConfig]:
    """One config per free block removed, plus baseline."""

def build_phase1_configs(
    corpus: PromptCorpus,
    free_block_ids: list[str],
    constrained_block_ids: list[str],
    covering_array: list[list[int]],
) -> list[AblationConfig]:
    """One config per covering array row."""

def build_phase2_configs(
    corpus: PromptCorpus,
    free_block_ids: list[str],
    constrained_block_ids: list[str],
) -> list[AblationConfig]:
    """Phase 0 configs but with neutral padding replacing removed blocks."""
```

#### probe.py

```python
@dataclass
class Probe:
    id: str
    target_block: str
    user_message: str
    scoring_method: Literal["exact", "contains", "not_contains",
                            "length", "llm_judge", "tool_trace"]
    expected_behavior: str
    violation_indicator: str
    scoring_params: dict[str, Any]  # Method-specific parameters

    def score(self, response: str, tool_calls: list[dict] | None = None) -> float:
        """Score a model response against this probe.

        Returns:
            Float in [0.0, 1.0]. 1.0 = full adherence. 0.0 = violation.

        Raises:
            ValueError: If scoring_method is 'llm_judge' and no judge
                       is configured (caller must handle LLM judge calls).
        """

@dataclass
class ProbeResult:
    config_id: str
    probe_id: str
    model_id: str
    trial: int
    raw_response: str
    tool_calls: list[dict] | None
    score: float
    timestamp: str  # ISO 8601
```

#### battery.py

```python
@dataclass
class ProbeBattery:
    probes: list[Probe]
    metadata: dict[str, Any]  # Version, creation date, author

    def probes_for_block(self, block_id: str) -> list[Probe]:
        """Return probes targeting a specific block."""

    def validate(self, free_block_ids: list[str]) -> list[str]:
        """Check that every free block has at least one probe.

        Returns:
            List of block IDs with no probes (should be empty).
        """

def load_battery(path: Path) -> ProbeBattery:
    """Load probe battery from JSON."""

def save_battery(battery: ProbeBattery, path: Path) -> None:
    """Save probe battery to JSON."""
```

#### runner.py

```python
@dataclass
class AblationRun:
    id: str                        # Unique run ID
    configs: list[AblationConfig]
    battery: ProbeBattery
    models: list[str]              # Model IDs from registry
    trials_per_probe: int
    temperature: float
    results: list[ProbeResult]     # Populated during execution
    metadata: dict[str, Any]       # Budget, start/end time, etc.

class AblationRunner:
    def __init__(
        self,
        registry: ModelRegistry,
        caller: LLMCaller,
        budget_usd: float | None = None,
    ):
        """Initialize runner with model registry and LLM caller.

        The runner does NOT make API calls directly. It uses the
        provided LLMCaller, which the caller controls.
        """

    async def run_phase(
        self,
        run: AblationRun,
        phase: str,
        concurrency: int = 5,
        progress_callback: Callable | None = None,
    ) -> AblationRun:
        """Execute all (config, probe, model, trial) combinations for a phase.

        Uses semaphore for concurrency control. Records all results.
        Supports resume (skips already-completed combinations).

        Args:
            run: The ablation run (configs, battery, models).
            phase: Phase identifier for filtering configs.
            concurrency: Max concurrent API calls.
            progress_callback: Called with (completed, total) counts.

        Returns:
            The run with results populated.
        """

    def estimate_cost(self, run: AblationRun) -> dict[str, float]:
        """Estimate API costs per model and total.

        Uses ModelRegistry cost profiles. Returns dict with per-model
        and total estimates.
        """
```

#### tensor.py

```python
@dataclass
class AblationScore:
    baseline_score: float
    ablated_score: float
    delta: float               # ablated - baseline
    p_value: float | None      # Across trials (None if single trial)
    position_controlled: bool
    position_delta: float | None

class AblationTensor:
    """Sparse tensor: (block, probe, model) → AblationScore.

    Extends the concept of InterferenceTensor with empirical
    measurements rather than analytical scores.
    """

    def from_run(self, run: AblationRun) -> "AblationTensor":
        """Assemble tensor from completed ablation run."""

    def main_effects(self, significance: float = 0.05) -> dict[str, float]:
        """Mean |delta| per block, filtered by p_value."""

    def pairwise_interactions(
        self,
        phase1_run: AblationRun,
    ) -> dict[tuple[str, str], float]:
        """Compute interaction effects from Phase 1 data.

        interaction(a,b) = delta(both_removed) - delta(a_only) - delta(b_only)
        """

    def to_interference_tensor(self) -> InterferenceTensor:
        """Convert empirical ablation results to standard InterferenceTensor.

        Maps ablation deltas to interference scores, enabling comparison
        with static/LLM analysis results.
        """
```

#### analysis.py

```python
@dataclass
class BlockClassification:
    block_id: str
    category: Literal["weight_aligned", "weight_compensating",
                       "weight_conflicting", "weight_novel"]
    evidence: str              # Why this classification
    main_effect: float
    interaction_count: int     # Number of significant pairwise interactions
    position_sensitive: bool
    confidence: float          # How certain (based on p-values, trial count)

@dataclass
class CompetitionPattern:
    type: Literal["exploitation", "interference"]
    blocks: list[str]
    evidence: str
    tensor_signature: str      # "dense_row" or "sparse_entry"

def classify_blocks(
    tensor: AblationTensor,
    baseline_adherence: dict[str, float],
) -> list[BlockClassification]:
    """Classify each block using the four-category taxonomy.

    Args:
        tensor: The assembled ablation tensor.
        baseline_adherence: Per-probe scores from baseline config.
            Used to detect weight-conflicting blocks (low adherence
            even with block present).

    Returns:
        Classification for each free block.
    """

def detect_competition_patterns(
    tensor: AblationTensor,
    density_threshold: float = 0.3,
) -> list[CompetitionPattern]:
    """Identify exploitation vs interference competition.

    Dense tensor rows → exploitation (attention budget).
    Sparse entries → interference (semantic conflict).
    """

def detect_suppression(
    tensor: AblationTensor,
) -> list[tuple[str, str, float]]:
    """Find hidden suppressive interactions (Tekin et al. pattern).

    Returns (block_a, block_b, suppression_magnitude) triples where
    removing block_a improves adherence to block_b's probes.
    """

def generate_report(
    tensor: AblationTensor,
    classifications: list[BlockClassification],
    patterns: list[CompetitionPattern],
    suppressions: list[tuple[str, str, float]],
) -> str:
    """Human-readable analysis report."""
```

## Cost Estimates

Assuming 2 probes per block (46 probes), 3 models, 3 trials:

| Phase | Configs | API Calls | Est. Cost |
|-------|---------|-----------|-----------|
| Baseline | 1 | 46 × 3 × 3 = 414 | $12 |
| Phase 0 | 23 | 46 × 3 × 3 × 23 = 9,522 | $286 |
| Phase 1 | 12 | 46 × 3 × 3 × 12 = 4,968 | $149 |
| Phase 2 | 23 | 46 × 3 × 3 × 23 = 9,522 | $286 |
| **Total (0+1+2)** | **59** | **24,426** | **~$733** |

With 1 probe per block (23 probes), 3 models, 3 trials:

| Phase | Configs | API Calls | Est. Cost |
|-------|---------|-----------|-----------|
| Baseline | 1 | 23 × 3 × 3 = 207 | $6 |
| Phase 0 | 23 | 23 × 3 × 3 × 23 = 4,761 | $143 |
| Phase 1 | 12 | 23 × 3 × 3 × 12 = 2,484 | $75 |
| Phase 2 | 23 | 23 × 3 × 3 × 23 = 4,761 | $143 |
| **Total (0+1+2)** | **59** | **12,213** | **~$367** |

Note: Cost per call varies by model. Haiku ~$0.01, Gemini Flash ~$0.005,
Qwen via OpenRouter ~$0.01-0.03. Estimates use $0.03 as conservative upper
bound. Actual costs likely 40-60% lower.

Note: Call costs vary by response length. Conciseness probes produce
short responses; overengineering probes with code context produce long
responses. The $0.03 average accounts for this distribution but actual
per-probe costs will be skewed.

**Minimum viable (Phase 0 only, 1 probe, 1 model, 3 trials)**:
24 × 23 × 3 = 1,656 calls ≈ $17-50. This is the easy falsification
phase. If Phase 0 shows nothing interesting, we've spent $50 finding
out. If it shows clear main effects, we've justified the full run.

## Implementation Sequence

### For the Implementation Agent

1. `covering_array.py` — Pure algorithm, no dependencies. Test: verify
   coverage property (every t-tuple appears in all value combinations).

2. `probe.py` — Data model + scoring functions. No API calls. Test:
   scoring methods return correct values for known inputs.

3. `configuration.py` — Depends on prompt_blocks.py. Test: assembled
   prompts contain exactly the right blocks, constrained blocks never
   removed, padding insertion correct.

4. `battery.py` — Depends on probe.py. Test: validation catches
   uncovered blocks, serialization round-trips.

5. `runner.py` — Depends on configuration.py, battery.py, llm_caller.py,
   registry.py. Test: orchestration logic, resume behavior, cost
   estimation. Mock LLM calls for unit tests.

6. `tensor.py` — Depends on probe.py, interference_tensor.py. Test:
   assembly from results, main_effects computation, conversion to
   InterferenceTensor.

7. `analysis.py` — Depends on tensor.py. Test: classification logic
   with synthetic tensors containing known patterns.

### For the Independent Test Agent

The test agent receives:
- This design document (contracts and expected behavior)
- The module dependency graph
- The existing test suite structure (tests/ directory)

The test agent does NOT receive:
- The implementation source code
- Implementation decisions not specified here

The test agent writes tests against the contracts specified above.
Key test categories:

1. **Covering array correctness**: Every t-tuple covered. No missing
   combinations. Constraints respected.

2. **Configuration assembly**: Constrained blocks always present.
   Absent blocks not in output. Position preservation. Padding
   insertion (Phase 2).

3. **Probe scoring**: Known inputs → known scores for each scoring
   method. Edge cases (empty response, tool calls without text, etc.).

4. **Battery validation**: Uncovered blocks detected. Serialization
   round-trip fidelity.

5. **Tensor assembly**: Correct delta computation. Statistical
   significance calculation. Conversion to InterferenceTensor.

6. **Block classification**: Synthetic tensors with planted patterns
   → correct classifications. All four categories testable.

7. **Competition detection**: Dense vs sparse patterns correctly
   identified. Suppression detection finds planted suppressions.

8. **Integration**: End-to-end with mock LLM (deterministic responses)
   → correct tensor → correct classifications.

## Open Questions

1. **Probe design authority**: Who designs the probe battery? It
   requires domain knowledge about what each block's instructions
   mean in practice. Candidate: a separate LLM-assisted probe
   generation pass, validated by human review.

2. **System prompt injection**: We're testing how models behave under
   modified system prompts. This requires API access that allows
   setting custom system prompts (most APIs do, but some have
   restrictions on content).

3. **Ethical considerations**: Some ablations remove safety blocks.
   We constrain safety blocks as always-present, but edge cases may
   arise where behavioral blocks have safety-adjacent effects.

4. **Reproducibility**: LLM outputs are stochastic even at
   temperature=0 (some providers). The statistical design (multiple
   trials, significance testing) mitigates but doesn't eliminate this.

5. **Interaction with CLAUDE.md**: The design targets the model's
   system prompt, not project-level instructions. CLAUDE.md content
   would be held constant across all configurations (it's part of the
   application tier, not system tier).

## Resolved Questions

- **Tool call tracing**: Resolved. Pichay proxy already provides tool
  call interception and logging. API mode also returns tool calls
  directly.

- **LLM-as-judge model**: Cross-family judge (Gemini Flash) to avoid
  same-family systematic bias. Judge sees response only, not
  configuration or target block.

- **Probe independence**: Reframed. Probes are targeted by design but
  behavioral entanglement across configurations is signal, not noise.

- **Phase 1 trial count**: 5 trials minimum (up from 3) due to
  difference-of-differences compounding scoring errors.

- **Position control padding**: Two conditions (whitespace and
  semantic padding) to distinguish primacy, attention dilution, and
  distractor interference mechanisms.

- **Temporal stability**: Pin model versions where possible; run all
  phases within tight time window; record exact model ID and timestamp.

## References

- NIST SP 800-142: Kuhn, Kacker, Lei (2010) — Covering array methodology
- NIST ACTS tool: csrc.nist.gov/projects/automated-combinatorial-testing-for-software
- Tekin et al. (2021): Hidden suppressive interactions, iScience, PMC8044428
- Baxi (2025): CDCT compression-decay, arXiv:2512.17920
- arXiv:2603.10123: Lost in the Middle at Birth (position bias)
- Geng et al. (2025): Control Illusion, arXiv:2502.15851
- Rofin et al. (2026): Seemingly Useless Features, arXiv:2603.14087
- Romanou et al. (2026): Brittlebench, arXiv:2603.13285
- Full reference list: docs/research/scout_pass1_references.md
- Additional references: docs/research/scout_pass2_ablation_and_trails.md
