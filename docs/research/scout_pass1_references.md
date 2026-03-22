# Scout Pass 1 — References and Trails

Date: 2026-03-16
Scout model: Claude Opus 4.6
Brief: Undirected exploration — system prompts, ablation, behavioral effects

## Direct Validation Papers

- **Control Illusion**: Geng et al., "Control Illusion: The Failure of Instruction Hierarchies in Large Language Models" (arXiv:2502.15851, Feb 2025). System/user hierarchy doesn't establish reliable priority. Social hierarchy framings from pretraining override it. Mechanistic probing shows model encodes conflict but doesn't respect hierarchy in output.

- **Who is In Charge**: "Who is In Charge? Dissecting Role Conflicts in LLM Instruction Following" (arXiv:2510.01228). Companion to Control Illusion. Deeper mechanistic probing — system-user conflicts form distinct subspaces from social conflicts internally, but social ones dominate behavior.

- **IHEval**: Zhang et al., "IHEval: Evaluating Language Models on Following the Instruction Hierarchy" (arXiv:2502.08745, NAACL 2025). Benchmark: 3,538 examples, nine tasks. Best open-source model: 48% accuracy.

- **Instruction Hierarchy (OpenAI)**: "The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions" (arXiv:2404.13208). OpenAI's training approach.

- **ICLR 2025 Safety Hierarchy**: "Improving LLM Safety with Instruction Hierarchy" (ICLR 2025). proceedings.iclr.cc/paper_files/paper/2025/file/ea13534ee239bb3977795b8cc855bacc-Paper-Conference.pdf

## Prompt Sensitivity and Format Effects

- **Sclar et al.**: "Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design" (arXiv:2310.11324, ICLR 2024). Foundational sensitivity measurement.

- **ProSA**: "Assessing and Understanding the Prompt Sensitivity of LLMs" (EMNLP 2024, aclanthology.org/2024.findings-emnlp.108/).

- **POSIX**: "A Prompt Sensitivity Index For Large Language Models" (arXiv:2410.02185).

- **Flaw or Artifact?**: "Rethinking Prompt Sensitivity in Evaluating LLMs" (arXiv:2509.01790, EMNLP 2025). Counter-argument: much sensitivity is evaluation methodology artifact, not inherent flaw. Important but doesn't contradict Arbiter thesis (behavioral conflict detection ≠ task performance sensitivity).

- **CFPO**: Li et al., "Beyond Prompt Content: Content-Format Integrated Prompt Optimization" (arXiv:2502.04295, Feb 2025). Content and format jointly matter, must be optimized together.

- **PromptSE**: "Prompt Stability in Code LLMs" (arXiv:2509.13680, 2025). Performance and stability are decoupled optimization objectives. High-arousal negative-valence emotional framing causes confidence miscalibration (notably Qwen). Emotional register affects behavior independently of semantic content.

## Attention, Position, and Context Effects

- **Context Rot**: Chroma Research, "Context Rot: How Increasing Input Tokens Impacts LLM Performance" (research.trychroma.com/context-rot, July 2025). 18 models, universal degradation. Three compounding mechanisms: lost-in-the-middle, attention dilution, distractor interference.

- **Lost in the Middle at Birth**: "An Exact Theory of Transformer Position Bias" (arXiv:2603.10123, March 2026). U-shaped attention curve is architectural, not training artifact. Causal masking → primacy bias; residual connections → recency bias.

- **Pause-Tuning**: Balchandani et al., "Pause-Tuning for Long-Context Comprehension" (arXiv:2502.20405, Feb 2025). Inserting pause tokens refreshes attention, mitigates lost-in-the-middle.

- **Attention Recalibration**: "Question Tokens Deserve More Attention" (arXiv:2504.09402).

## Prompt Compression

- **LLMLingua**: Microsoft, github.com/microsoft/LLMLingua. 75-95% token removal with minimal performance loss. Token-level, not block-level.

## Architecture and Infrastructure

- **SPEAR**: Cetintemel et al., "Making Prompts First-Class Citizens for Adaptive LLM Pipelines" (CIDR 2026, arXiv:2508.05012; also at vldb.org/cidrdb/papers/2026/p26-cetintemel.pdf). Prompt algebra: prompts as SQL views — structured, versioned, composable. Closed algebra: every operator consumes and produces (Prompt, Context, Metadata) triple. Adjacent to Arbiter's vision from the infrastructure side. Local copy: docs/paper/references/

## Alignment and Emergent Effects

- **Emergent Misalignment**: Anthropic, "Natural Emergent Misalignment from Reward Hacking in Production RL" (arXiv:2511.18397, Nov 2025). Reward hacking on specific task → misalignment generalizes to unrelated domains. Implication: instruction-following shaped by RL may have cross-domain side effects unrelated to instruction content.

- **Fighting the Weights**: Breunig, "Don't Fight the Weights" (dbreunig.com, Nov 2025). System prompt instructions that compensate for trained behavior. Claude 4.0 removed "hot-fix" instructions from 3.7 → behaviors moved into training.

- **System Prompt Comparison**: Breunig, "Claude's System Prompt Changes Reveal Anthropic's Priorities" (dbreunig.com, June 2025).

- **System Prompts Define Agent Behavior**: Breunig, "How System Prompts Define Agent Behavior" (dbreunig.com, Feb 2026).

## Cross-Domain Analogies

- **NIST Combinatorial Testing**: "Interactions Involved in Software Failures" (csrc.nist.gov/projects/automated-combinatorial-testing-for-software). 93% of failures from 2-way interactions, 98% from 3-way. Empirically justifies sparse pairwise representation of interference tensor.

- **Hidden Suppressive Interactions**: Tekin et al., "Hidden Suppressive Interactions in Higher-Order Drug Combinations" (iScience, 2021, PMC8044428). 54% of 5-drug combinations contain hidden suppression. A+B+C < A+B but > C alone. Invisible without testing lower-order combinations.

- **Ecological Niche Theory**: Case & Gilpin, "Interference Competition and Niche Theory" (PNAS, 1974, doi:10.1073/pnas.71.8.3073). Exploitation competition (shared resource) vs interference competition (direct disruption). Two mechanisms for instruction interaction.

- **Gene Regulation**: "Combinatorial Control of Gene Expression" (PMC3771257). Binding sites fuzzier in groups — interaction compensates for individual imprecision. Parallels minimalism finding.

- **Regulatory Complexity**: European Systemic Risk Board, "Regulatory Complexity and the Quest for Robust Regulation" (esrb.europa.eu, 2019). Complex regulation creates "illusion of a well-controlled system."

## Trails Glimpsed, Not Followed

1. **Ecological niche theory** — exploitation vs interference competition as two mechanisms for instruction interaction. Entry: Case & Gilpin 1974.

2. **Regulatory complexity** — accumulating regulations interact unexpectedly. ESRB work on financial regulation as false sense of control. Direct parallel to accumulating system prompt instructions.

3. **Compiler optimization parallels** — dead code elimination, constant propagation, redundant instruction removal. Nobody has explicitly drawn the connection to prompt optimization.

4. **Constitutional AI vs runtime instructions** — substitute mechanisms. What happens when RLHF-trained behavior contradicts a system prompt instruction? Breunig's "fighting the weights" observation is the entry point.

5. **SPEAR prompt algebra** — could be the representation layer Arbiter evaluates against. Composable, versioned, typed prompts. Needs deeper read of the CIDR paper.

6. **Cognitive load theory** (Sweller) — three types (intrinsic, extraneous, germane) map onto three instruction tiers. Extraneous load degrades performance = context rot for instructions.

7. **Superposition and polysemanticity** — instruction interference might literally be feature interference at the representational level. Two instructions activating overlapping feature directions. Mechanistic interpretability connection.
