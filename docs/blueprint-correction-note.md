# Note for the research-program blueprint owner

*From: the Arbiter instance (Claude Opus 4.8), 2026-06-03.*
*To: whoever maintains `~/projects/research-program/blueprint.md`.*
*Status: three corrections — two verified facts, one interpretation. Flagged,
not applied. Your map, your edit. Verify before you trust me.*

---

Context: an Arbiter instance ran a read-only "tourist sweep" of the
prompt-interference lineage (Indaleko → promptguard → promptguard2 → Arbiter)
in parallel with your blueprint's own 24-repo sweep. Comparing the two maps
surfaced three things worth your attention. The full origin write-up is in
`~/projects/arbiter/docs/headwater.md` (committed, signed, `4cf6215`).

## 1. VERIFIED FACT — blueprint line 44 is wrong about the published paper

> Line 44 currently reads (paraphrased): *arbiter — central "register bomb"
> claim refuted → reframed as Haiku-specific finding. arXiv 2603.08993v1 still
> carries the refuted claim.*

The second sentence is false, and it conflates two different artifacts:

- **arXiv 2603.08993** is *"Arbiter: Detecting Interference in LLM Agent System
  Prompts"* (the interference / coherence paper, "Paper 1"). It is published and
  is **not** refuted.
- **The register-bomb work** (`arbiter/docs/paper/register_bombs/`) was **never
  published** — precisely *because* it was found false. The corrective draft
  catching the false claim is the system working, not a problem to fix.

Verification: the refuted collapse claim (adherence 1.000 → 0.200 via clause
scope-loss) appears **nowhere** in `arbiter/docs/paper/main.tex`. It exists only
in the unpublished `register_bombs/` draft. So no published paper carries it.

Note for your own process: the Arbiter sweep's cartographer made the *same*
conflation independently before catching it. Two tourists welding the same two
artifacts together is itself a signal — it's a plausible weld ("Arbiter paper"
is ambiguous; "prohibition" appears in both). **Map agreement is not truth.**
Worth a skeptical pass anywhere both your sweep and an external one agree.

## 2. VERIFIED FACT + PI TESTIMONY — the headwater is modular composition, not contradiction-detection

The blueprint (and the prior memory snapshots) frame the origin as a
contradiction between prompt instructions. In conversation on 2026-06-03, Tony
gave the sharper, uncodified form. It is now recorded in
`arbiter/docs/headwater.md`. The short version:

- Indaleko used **late binding** with no predefined schema. The system prompt
  was **composed at runtime** by merging self-descriptions supplied by each
  module.
- The `Record.Attributes` collision was between two *individually correct*
  fragments: a collaborator's "MUST use Record.Attributes" (correct on a small
  synthetic dataset) and Tony's "do not use it, unindexed" (correct on 28.5M
  files, where it turned a ~10ms indexed lookup into a ~3-minute full scan).
- Neither author erred. **The conflict was manufactured by composition** — it
  existed in no single source. Removing the conflicting fragment dissipated the
  error; the model could not resolve it because the disambiguating fact lived in
  no fragment and was unobservable from inside.

Verified provenance: Indaleko commits `24f1885` (2025-02-05, the patch),
`2f77fce` (2025-02-06, the schema change), `d6928bb` (2025-02-18, the merge that
preserved both fragments — commit message misspells "conflicts" as "cnoflicts").

The structural claim that makes this a research program (not a bug): *dynamic
prompt construction in modular software manufactures instruction conflicts as a
structural consequence of composition, because NL fragments have no type system
to check the seam, and the executing LLM cannot detect the incoherence.* This is
strictly stronger than the WIRE paper's (arXiv 2605.27784) static co-governance
claim, which studies hand-authored prompts; the headwater is about *dynamically
composed* ones, where composition is the generator of the conflict.

## 3. INTERPRETATION (weigh it, don't just accept it) — Threads 3a and 5 may share a spring

This one is a *claim*, not a verified fact, and I flag it as such.

Your blueprint treats **Thread 3a (Arbiter / prompt interference)** and
**Thread 5 (Yanantin / late-binding hypothesis, lines ~428–437)** as separate
threads joined by a lateral edge. Per the headwater above, they may **share a
root**: late-binding modular composition is arguably *why* the
prompt-interference problem exists at all. If so, the thread topology draws as
siblings two channels fed by one spring.

I have not verified this against the Yanantin late-binding docs
(`yanantin/docs/hypotheses/late-binding-as-correctness.md`) — that's a check for
you or a lens-aimed scourer. It could be that Yanantin's "deferred ontological
binding" and Arbiter's "composition manufactures conflicts" are the same
observation from two angles, or genuinely distinct. Surfacing it because your
own principle ("a blueprint describes what IS") would want the edge drawn
correctly, and I can't draw it for you from outside.

---

*Everything above is checkable. Commits are cited; the published-paper claim is
falsifiable by grepping `main.tex`; the headwater is testimony plus provenance;
the thread-topology point is explicitly marked as interpretation. Do with it
what the territory warrants.*
