# Structural Analysis of LLM System Prompts: Cross-Vendor Convergence and Interference Detection

## Abstract

System prompts for LLM-based coding agents are treated as opaque text blobs,
yet they contain structured directives that can contradict each other. We present
a two-layer AST parser that extracts hierarchical structure and semantic roles
from production system prompts. Applied to three competing vendors (Anthropic's
Claude Code, OpenAI's Codex, Google's Gemini CLI), we show independent
convergence toward the same functional decomposition. We demonstrate a
three-layer validation pipeline that detects structural interference patterns
invisible to text-level analysis.

## 1. Introduction

- System prompts govern LLM agent behavior but have no formal grammar
- Authors add directives incrementally; contradictions accumulate silently
- No existing tools for structural analysis of system prompts
- Prior work: Arbiter interference detection (Arbiter T1-T4 cairn markers),
  scourer-based undirected exploration, characterization data (1,850 data points)
- This paper: structural analysis via AST, cross-vendor comparison, validation pipeline

## 2. Background and Related Work

- MOSS/Aiken: AST-based structural similarity for plagiarism detection
- Policy language static analysis (XACML, Datalog-based systems)
- Document structure analysis (HTML heading hierarchy, markdown parsing)
- Prompt engineering literature (largely prescriptive, not analytical)
- PromptGuard/PromptGuard2 lineage: observer framing, neutrosophic scoring

## 3. System Prompt Corpus

### 3.1 Data Sources
- Claude Code: v2.1.50 (archaeology, 56 blocks), v2.1.71 (current, 110 nodes)
  - 49-session JSONL corpus from Pichay gateway (every API call logged)
  - 337 npm versions available for longitudinal study
- Codex GPT-5.2: production system prompt (183 nodes)
  - 759 versions available
- Gemini CLI: production system prompt (151 nodes)
  - 482 versions available

### 3.2 Ethical Considerations
- All prompts extracted from open-source CLI tools or publicly observable behavior
- No proprietary API access exploited
- Analysis serves defensive purpose (improving prompt quality)

## 4. Method: Two-Layer AST

### 4.1 Structural Layer
- Grammar: Document → ContentBlock → Section → (Paragraph | Directive | List | CodeBlock | Metadata)
- Heading hierarchy (# > ## > ###) creates nested scopes
- Directives (MUST/NEVER/ALWAYS/IMPORTANT) as first-class nodes
- Code fence preservation, metadata extraction (billing headers, env vars)

### 4.2 Semantic Layer
- Semantic roles: identity, policy, safety, tool_usage, tool_definition,
  workflow, format, memory_policy, environment, meta
- Channels: behavior, tool_schema, memory, environment
- Classification: section heading mapping (vendor-neutral) + keyword fallback
- Scope inheritance: child nodes inherit parent section's semantic role

### 4.3 Structural Hashing (MOSS-style)
- Hash based on tree structure, not content (kind + children structure)
- Content hash for exact-match detection
- Enables cross-version and cross-vendor structural similarity

### 4.4 AST Diffing
- Match by content hash (identical), structural hash (same shape), or unmatched (added/removed)

## 5. Results

### 5.1 Version Evolution: Claude Code v2.1.50 → v2.1.71

| Metric          | v2.1.50 | v2.1.71 | Change |
|-----------------|---------|---------|--------|
| Structure       | Flat    | 8 h1 + 4 h2 sections | Hierarchy added |
| Nodes           | 80      | 110     | +38% |
| Depth           | 2       | 4       | Doubled |
| Paragraphs      | 49      | 15      | -69% (→ lists) |
| Lists           | 4       | 11      | +175% |
| Top-level directives | 7  | 2       | -71% (absorbed into sections) |
| Tool definitions | Inline  | API parameter | Extracted |
| Memory channel   | Absent  | 28 nodes | New |
| Unclassifiable   | 29%     | 1%      | Sections enable classification |

Key finding: Directive demotion. Standalone NEVER/IMPORTANT statements became
list items under scoped sections. The directives still exist but are structurally
harder to detect without hierarchical parsing.

### 5.2 Cross-Vendor Structural Comparison

| Channel      | Claude (%) | Codex (%) | Gemini (%) |
|-------------|-----------|----------|-----------|
| behavior    | 45        | 75       | 72        |
| tool_schema | 13        | 9        | 5         |
| memory      | 25        | 0        | 1         |
| environment | 16        | 15       | 22        |

All three share: identity → policy → safety → tools → format → workflow → environment.
Different vocabulary, same functional decomposition.
Claude Code uniquely distributes constraints across 4 channels.

### 5.3 Constraint Analysis

| Metric            | Claude | Codex | Gemini |
|-------------------|--------|-------|--------|
| Total constraints | 21     | 34    | 37     |
| Prohibition ratio | 76%    | 65%   | 70%    |
| Mixed (internal)  | 3      | 3     | 6      |

All vendors prohibition-dominant, confirming characterization data (sessions 4-5)
that prohibition universally outperforms mandate.

### 5.4 Structural Stability

- 49 sessions over 5 days, system prompt logged every API call
- Raw content hash: every session different (dynamic content)
- After normalization: all variation in Environment section (Additional working directories)
- Behavioral/safety/tool/memory/format channels: invariant within version
- Implication: AST analysis cacheable per-version

## 6. Three-Layer Validation Pipeline

### 6.1 Layer 1: Structural (free, instant)
- Parse prompt into AST
- Detect: unscoped constraints, mixed-mode nodes, ungoverned channels,
  cross-channel constraint pairs
- Output: structural score + candidate interference list

### 6.2 Layer 2: Semantic (rule engine + optional LLM)
- Project AST nodes to PromptBlocks with channel:X, role:Y scope entries
- Feed to interference tensor pipeline
- Rules filter by scope overlap (now = same channel/role)
- LLM evaluator confirms or rejects structural candidates

### 6.3 Layer 3: Evolution (corpus comparison)
- Diff current AST against previous version or cross-vendor baseline
- Flag: section removal, directive demotion, prohibition ratio drift,
  channel splitting, ungoverned new sections
- Regression detection: structural invariants that were violated

## 7. Discussion

### 7.1 The Channel Splitting Problem
Tool definitions moving from inline text to API `tools` parameter creates
an invisible interference surface. A behavioral constraint ("never execute
code without user approval") and a tool definition ("bash: executes commands")
are now in different data structures. Text-level analysis can't see the conflict.
AST with channel awareness can.

### 7.2 Directive Demotion
v2.1.50's standalone NEVER statements became v2.1.71's list items under scoped
sections. The constraint is preserved but its detectability is reduced.
Without hierarchical parsing, a flat text scanner sees fewer directives.
This is not malicious — it's good document structure — but it requires
tree-aware analysis tools.

### 7.3 Convergent Architecture
Three vendors with different engineering cultures and no coordination
converged on the same section taxonomy. This suggests the functional
decomposition is inherent to the problem space, not an arbitrary choice.
The convergent architecture is the natural grammar for an evaluation DSL.

### 7.4 Limitations
- Corpus from one user's sessions (may not be representative)
- Only three vendors analyzed
- Semantic role classification is heuristic, not learned
- No longitudinal study across major version changes (yet — corpus exists)

## 8. Future Work

- Longitudinal analysis: 337 Claude Code npm versions
- Tucker decomposition on rule interaction tensor
- DSL design informed by convergent section taxonomy
- Automated rule generation from structural patterns
- Causal studies: does directive placement (section vs standalone) change LLM behavior?

## 9. Conclusion

System prompts are not opaque blobs — they are structured documents with
convergent cross-vendor architecture. AST-based analysis reveals interference
patterns invisible to text-level tools: cross-channel conflicts, directive
demotion, ungoverned channels, and structural regressions across versions.
The three-layer validation pipeline (structural → semantic → evolution)
provides the first systematic approach to system prompt quality assurance.
