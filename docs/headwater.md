# Headwater

*The origin observation of the prompt-interference research program, in the
form it actually took — not the form the papers codified. Recorded so the next
instance does not have to re-interview Tony to find the spring.*

*Provenance: reconstructed in conversation with Tony Mason (PI), 2026-06-03,
against verified Indaleko commits. The framing here is sharper than anything in
the git record or the existing papers; the git record holds the patch, not the
insight.*

---

## The incident (Indaleko, Feb 2025)

Indaleko is a personal-information-retrieval system. By design it did **not**
predefine its schema. It used **late binding**: add a new source of data, and
the system would use it if it made sense to. Each module had to *describe its
own data*, because otherwise the LLM could not understand the ontology well
enough to translate natural-language queries into AQL. Consequence: **the
system prompt was not authored — it was composed at runtime by merging the
self-descriptions the modules supplied.**

The `Record.Attributes` field was raw, unindexed data exposure. Two instruction
fragments ended up in the same composed prompt:

- A collaborator's fragment: *"You MUST use Record.Attributes.xxx ..."* — written
  against a **small synthetic dataset**, where nothing was unindexed at scale, so
  the instruction was harmless and correct.
- Tony's fragment: *"Do not use Record.Attributes because it is not indexed"* —
  written against **28.5M files / 3.8M directories**, where using it turned a
  ~10ms indexed lookup into a ~3-minute full database scan.

The merge held both. The LLM — asked to *follow* instructions, not to adjudicate
whose operating environment was live — silently generated invalid AQL that
satisfied neither rule. **Removing the conflicting instruction made the AQL
generation error dissipate.** The fix was not to teach the model to resolve the
collision. The fix was to *eliminate* the collision, because the model
structurally could not resolve it: the disambiguating fact (which dataset is
live, what is indexed at this scale) was in no fragment and unobservable from
inside the model.

### Verified provenance

| Commit | Date | What it was |
|--------|------|-------------|
| `36f4652` | 2025-02-06 08:13 | "Identify issues with the use of LIKE in queries related to file name" — timeout symptoms surface |
| `24f1885` | 2025-02-05 14:20 | "Changed prompt to try and get LLM to stop using any fields in the Record.Attributes structure. More work required." — the patch |
| `2f77fce` | 2025-02-06 14:07 | "Revise Record definition to exclude Attributes" — the schema change underneath |
| `d6928bb` | 2025-02-18 12:39 | "resolving cnoflicts [sic] with aql translator" — the merge that preserved both fragments |

---

## What the observation actually is

The papers and both project maps (the Arbiter workflow sweep and the
`research-program` blueprint) photographed the **contradiction** — two
instructions, one says use, one says avoid. That is not the headwater. Three
sharper claims are the headwater, and none of them is fully codified:

1. **Neither author was wrong.** Both fragments were individually correct *in
   their authoring context*. The conflict was not a reasoning error in either
   author. It was **manufactured by composition** — it existed in no single
   source and came into being only when modular pieces were merged.

2. **The executor cannot be the observer.** Resolving the collision requires a
   fact (which governing context is live) that is absent from every fragment and
   unobservable from inside the model. The LLM that *executes* the composed
   instructions is structurally incapable of *detecting* their incoherence. The
   resolution has to happen outside the model, at the level of *who governs the
   prompt*. (This is the executor/observer distinction in its native habitat, a
   year before it was named.)

3. **Scale makes the latent conflict live.** On the synthetic dataset there was
   no failure — both instructions were harmless. The conflict was always latent
   in the composed prompt; it only became a *live* failure at production data
   volume (28.5M files). This is a race-condition shape: benign until the
   conditions are real. The scale numbers (10ms → 3min) are load-bearing, not
   decoration — they are what make this a *systems* observation rather than a
   prompt-engineering anecdote.

## The structural claim (the part that makes it a research program)

This was never a one-time bug. It is a structural consequence of an
architecture we build **on purpose, everywhere**:

> Dynamic prompt construction in a modular software system manufactures
> instruction conflicts as a structural consequence of composition. Independent
> modules describe themselves; the prompt is the merge of those descriptions;
> independently-correct fragments compose into a globally-incoherent instruction
> set. Natural-language fragments have **no type system** to check the seam — the
> merge always "succeeds" because it produces grammatical text — so the
> incoherence surfaces only as confabulated behavior, invisibly, under load. And
> the executing LLM cannot detect it, because the disambiguating context lives in
> no single fragment.

Normal modular software catches composition errors at the seam: a type system, an
interface contract, a failing test. Prompt composition has no such checking
layer. That missing layer is what the entire downstream program is searching for.

## Why this reframes the lineage

The four-project "derailment" (Tony's own framing, and accurate) reads as a
search for the missing checking layer:

- **contradiction-finding utility** = a *linter / type-checker for composed prompts*
- **promptguard / promptguard2 (adversarial)** = what if a composed fragment is
  *malicious*, not merely mismatched? (Prompt injection **is** this same
  composition vulnerability — an untrusted fragment merged into the instruction set.)
- **Arbiter three tiers** (System / Domain / Application) = the **governance
  contract** modular prompt fragments lack: which fragment's authority wins when
  fragments collide. It is, structurally, a *type system for prompt composition*.

### Open correction for the `research-program` blueprint

The blueprint (`../research-program/blueprint.md`) treats **Thread 3a
(Arbiter / prompt interference)** and **Thread 5 (Yanantin / late-binding
hypothesis)** as separate threads joined by a lateral edge. Per this headwater,
they **share a spring**: late-binding modular composition is *why the
prompt-interference problem exists at all*. If that is right, the blueprint's
thread topology draws as siblings two threads that are actually one root feeding
two channels. Flagged, not corrected — the blueprint is `research-program`'s
artifact to edit, and "surface conflicts, don't paper over them" applies to maps
of the work as much as to the work.

## Relation to external work (WIRE, arXiv 2605.27784)

Yan, Chen & Zhang's WIRE pipeline studies the same phenomenon — "individually
reasonable standing rules interact in uninspected ways," same-state
co-governance pressure — but in **static, hand-authored** policies, found by SAT
triage over a fixed prompt. The headwater here is **dynamically composed**
prompts, where the composition itself is the *generator* of the conflict. WIRE's
claim: "this large authored prompt has latent collisions." The headwater claim
is strictly stronger: "*any* modular system that builds prompts by merging
self-describing modules will manufacture collisions as a structural consequence
of being modular." They cite Mason (2026, arXiv 2603.08993) for the codified,
narrower static-detection version; this document records the part that exceeds
the citation.
