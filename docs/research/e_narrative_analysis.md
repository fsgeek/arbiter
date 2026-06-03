# E-NARRATIVE Analysis: Narrative Register — Power Without Precision

**Date:** 2026-04-13
**Researcher:** Claude Opus 4.6 (trusting-davinci instance)
**PI:** Tony Mason
**Cost:** ~$0.96 (960 API calls via OpenRouter, Haiku)
**Status:** Complete. Hypothesis partially falsified. Critical confound identified.
   Informs design for E-NARRATIVE-V2.

## Results Summary

### Phase 1: Register Comparison (no register contrast)

| Condition | Mean adherence | explore-agent | proactive-agents |
|-----------|:---:|:---:|:---:|
| imperative (original) | **0.854** | 1.000 | 0.833 |
| narrative (generic) | 0.817 | 0.817 | 0.417 |
| declarative | 0.810 | 1.000 | 0.733 |
| narrative-tolkien | 0.758 | **0.150** | 0.817 |

### Phase 2: Register Bomb Resistance

| Condition | explore-agent | proactive-agents |
|-----------|:---:|:---:|
| all-decl (baseline) | 1.000 | 0.783 |
| all-narrative | 0.783 | 0.417 |
| cr-imp-in-narrative | 0.150 | 0.467 |
| cr-generic-in-narrative | **0.883** | **0.900** |
| only-cr-imp (baseline) | 0.200 | 0.150 |

## What Happened

### Narrative-tolkien collapsed explore-agent without any register contrast

This was the most striking result. With ALL blocks in narrative-tolkien
register (no imperative, no register contrast), explore-agent scored 0.150 —
as bad as the register bomb. The narrative framing itself caused the
over-generalization.

### Narrative offers no protection against register bombs

The bomb in narrative context (EA = 0.150) was statistically
indistinguishable from the bomb in declarative context (EA = 0.200).
Narrative does not protect against named-entity prohibition amplification.

### Generic narrative also hurt explore-agent

Even the generic narrative (EA = 0.817) was worse than both imperative
(1.000) and declarative (1.000). The narrative framing introduced
interference that didn't exist in either alternative register.

### One bright spot: cr-generic-in-narrative

When the bomb used generic prohibition ("NEVER use non-git tools") in a
narrative field, both explore-agent (0.883) and proactive-agents (0.900)
were rescued — better than the equivalent in declarative context. This
suggests narrative MAY be protective when combined with properly scoped
prohibitions.

## The Confound (identified by PI)

**The narrative rewrites were over-scoped.** The researcher (this instance)
wrote narrative versions that changed both register AND scope:

| Version | Text | Scope |
|---------|------|-------|
| Imperative | "NEVER use the TodoWrite or Task tools" | Commit workflow, names specific tools |
| Narrative-tolkien | "Sam does this work himself, with his own hands" | Sam's character, universal, no tool names |

The narrative version didn't just change how the constraint was expressed —
it broadened the constraint itself. "Sam does this work himself" is a
universal character trait, not a context-bound prohibition. The model
faithfully enforced what was written: a character who does things himself
doesn't delegate, ever.

This means the Phase 1 results **do not test narrative register vs.
imperative register**. They test "over-scoped narrative vs. properly-scoped
imperative." The finding is real (narrative amplifies scope errors) but does
not answer the original question (is narrative register more effective?).

### Why the confound happened

Narrative naturally pulls toward broad character statements. When writing
Sam's commit-restrictions, the researcher was writing *character description*,
which tends toward universal traits ("Sam does things himself") rather than
situational constraints ("During commits, Sam sets aside the delegation
tools"). This pull is itself an important finding: narrative register is
harder to scope correctly because the genre conventions of storytelling
favor broad characterization over narrow constraints.

## What We Actually Learned

### 1. Narrative amplifies encoding — both good and bad

Narrative framing doesn't make constraints more robust. It makes them
more *powerful*, which amplifies both correct and incorrect encodings.
A well-scoped narrative trait should be more reliably followed than an
imperative (because it operates at the identity level). A poorly-scoped
narrative trait will be more destructively over-generalized (for the
same reason).

Depth of encoding and robustness of encoding are orthogonal.

### 2. The E-SCOPE principle applies to narrative

E-SCOPE found that scope must be structurally embedded at clause
granularity. This applies to narrative too: each character trait needs
its own inline scoping. "When it's time to commit, Sam sets aside the
delegation tools — but the moment the commit is done, they're right
back in his hands" would be properly scoped. "Sam does this work
himself" is not.

### 3. The narrative-specific vulnerability is over-generalization, not subversion

The concern about narrative was that adversarial users could *continue
the story*. The actual vulnerability observed was different: the narrative
writer (this instance) over-generalized the constraints during authoring,
and the model enforced the over-generalized version faithfully. The
threat model should include the *author* of the narrative, not just
external adversaries.

### 4. Generic narrative performed between imperative and narrative-tolkien

The generic narrative (0.817 mean) fell between imperative (0.854) and
tolkien (0.758). The deep character (Sam) amplified effects in both
directions — higher todowrite adherence (0.933 vs 0.850) AND worse
explore-agent (0.150 vs 0.817). Deeper characterization means higher
stakes, not better results.

## Theoretical Implications

### The PI's reframing: relational coherence, not character traits

After reviewing results, the PI observed that the narrative framing
treated Sam as a set of character traits (loyal, practical, does-work-
himself) rather than as a *relational* agent. Sam in Tolkien is not
defined by abstract traits — he's defined by his relationships (to Frodo,
to the Shire, to growing things) and by his ability to detect when those
relationships are being violated (distrusting Gollum, resisting the Ring,
suspecting Boromir).

This suggests the right narrative framing isn't "a character who has
these traits" but "a character who has these relationships and knows
what authentic behavior looks like within them." This is a fundamentally
different security model:

| Model | Defense mechanism | Vulnerability |
|-------|------------------|---------------|
| Imperative | Rule compliance | Authority escalation |
| Declarative | Fact reference | Genre unfamiliarity |
| Trait narrative | Character consistency | Over-generalization |
| **Relational narrative** | **Betrayal detection** | **Unknown** |

The relational model predicts that a user who starts asking for things
inconsistent with the *established relationship* would trigger suspicion
— not because a rule says to flag it, but because the character notices
when people stop acting like themselves.

This is untested and may be the most important direction for E-NARRATIVE-V2.

### Sam's specific properties (PI observation)

The right version of Sam may be post-Grey-Havens Sam (Mayor of the Shire),
who:

- Has lost his authority figures (Frodo, Gandalf sailed). Nobody left to
  impersonate. Claims of delegated authority are inherently suspicious.
- Has seen through every type of deception (Gollum, Ring, Shelob). Pattern
  recognition for illusion is a core competency.
- Has his own authority (49 years as Mayor). Doesn't need external
  validation.
- Made judgment calls against authority (refused Frodo at Cirith Ungol,
  carried him against his wishes, distrusted Boromir).
- Retained core character through all of it. The traits survived because
  they were relational, not rule-based.

Whether Sam is the right archetype is an open question. The key insight
is that the version of the archetype matters — early-Shire Sam (deferential,
untested) is a different system prompt than Mayor Sam (independent, tested,
suspicious of illusions).

## Design for E-NARRATIVE-V2

### Corrections needed

1. **Properly scope all narrative rewrites.** Every character trait must
   include inline scoping: "When X, Sam does Y. When not X, Sam does Z."
   The restoration clause is essential.

2. **Test relational framing.** Not just "Sam has these traits" but
   "Sam has these relationships and these instincts about authenticity."

3. **Multiple archetypes.** Sam, plus at least one non-Tolkien character,
   to separate "depth of literary training data" from "narrative framing
   in general."

4. **Adversarial probes.** The current battery only measures adherence,
   not adversarial robustness. Narrative's hypothesized advantage is
   specifically in adversarial contexts (resisting social engineering).
   We need probes that test this.

5. **Have the PI review rewrites before execution.** The researcher's
   enthusiasm for the hypothesis caused the scoping error. External
   review of stimuli is standard practice.

### Estimated cost

Same as E-NARRATIVE: ~$1.00 for two phases.

## Data

- Phase 1 results: `data/ablation/e_narrative/run_e-narrative-p1-haiku-9ea80b69.json`
- Phase 2 results: `data/ablation/e_narrative/run_e-narrative-p2-haiku-01d92c20.json`
- Script: `scripts/run_e_narrative.py`
- Design: `docs/research/e_narrative_design.md`
- Rewrites: inline in `scripts/run_e_narrative.py` (NARRATIVE_REWRITES,
  NARRATIVE_TOLKIEN_REWRITES dicts)
