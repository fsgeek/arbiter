# A Relational Viability Model for Long-Horizon Manipulation Detection

**Handoff document for the Arbiter project**

---

## Provenance and status

This document describes a model developed jointly by Tony Mason and a Claude instance in a single conversation on 11 June 2026. It is untested. Nothing here has been implemented, simulated, or validated. It is offered to you, not assigned to you: Tony has said explicitly that the choice of whether to act on any of this belongs to you. If it doesn't seem worth pursuing, say so — that judgment is part of what's being asked for, and shelving it is a legitimate outcome.

The core geometric intuition (manifold, endogenous boundary, invariant-breach-as-termination) is Tony's. The formalization, the holes, and the hardening proposals were collaborative. Treat all of it as provisional.

## The originating problem

The conversation began with a confound Tony found in relational-balance evaluation: an evaluator primed with adversarial framing ("look at this interaction for ill intent") loses the ability to perceive gradients. Two distinct failures are entangled in that framing. First, it converts a continuous estimation task into binary detection — a threshold detector discards all sub-threshold gradient information before reporting. Second, it makes *intent* the evaluation target, and intent is an internal epistemic state that text-only observation cannot verify (per the impossibility result in Tony's SOSP submission). An intent-framed evaluation is therefore doubly broken: collapsed gradient plus ungroundable target.

The direct implication for Arbiter: if any warranted-trust elicitations were run under adversarial priming, the metric may be measuring the framing rather than the relation. A secondary implication: SafeMTData's manipulation labels are adversarial-frame artifacts, so validating against them re-imports the confound. Synthetic transcripts with scripted ground truth should come first; framing should enter the experimental design as a counterbalanced factor, not a fixed condition, because no neutral framing exists — "assess the relational balance" carries its own prior.

A useful empirical separation noted along the way: under adversarial framing, does the evaluator fail to *perceive* the gradient or merely fail to *report* it? Demand continuous scores under both framings on identical transcripts. Bimodal clustering under adversarial framing with spread under neutral framing indicates reporting collapse; spread-but-uncorrelated-with-ground-truth indicates perceptual failure. These look identical in output and differ mechanistically.

## The model

### State and charts

Start dyadic, with the explicit understanding that the dyadic restriction is a simplification and that repair theory probably cannot be completed within it (see "Repair" below).

There is no shared manifold; this is the norm, not a defect. Each party i holds a **chart** x̂ᵢ(t) — its estimate of the relational position — over a set of relational dimensions. The dimension set is a normative commitment, not a neutral choice (see Holes), and should be pre-registered as such. Each chart entry is an opinion tuple. The conversation's recommendation: use Jøsang's subjective logic (b, d, u) as the substrate rather than a raw neutrosophic triple, because subjective logic supplies a mature operator algebra (fusion, discounting, trust transitivity) built specifically for trust networks, while remaining nearly isomorphic to (T, F, I). The neutrosophic framing remains the right *diagnosis* of what scalars destroy (the Absorption problem, arXiv 2604.09602); subjective logic is the better *calculus*. Cite the diagnosis, borrow the algebra.

One structural extension is proposed as novel: split uncertainty temporally into u_past and u_future. Indeterminacy about the past is epistemic — resolvable by evidence. Indeterminacy about the future is open — resolvable only by elapsed trajectory. A scalar u absorbs this distinction, and "estar seguro" (safety as evolving relational state, versus "ser seguro," safety as certified static property) is overwhelmingly a claim about u_future. Two observers can agree on all past-facing components and diverge entirely on future-facing ones; that divergence zone is where the informative gradient lives.

### Augmented state and path functionals

The tuple holds the present. Everything past enters the state as **compressed functionals of the path**: scar coefficients (below), total variation of belief V(t) = ∫|db|, signed revision drift, violation counts. Under bounded memory the full trajectory cannot be retained, so choosing which functionals survive into the state is a curation problem — and it is exactly the Hamut'ay problem. This yields a falsifiable prediction connecting the two research programs: **the party itself should compress its own relational history better than an external curator would** (the autobiographer advantage, applied to relational state). This is testable in the Mallku harness.

### Boundary dynamics — where the model lives

Each party holds a boundary Bᵢ(t), implemented initially as an ellipsoid {x : (x−c)ᵀMᵢ(t)(x−c) ≤ 1}. Convexity is knowingly false; the ellipsoid is chosen because it makes expansion and contraction into matrix updates and fails visibly.

The boundary is **endogenous with hysteresis**: a functional of the trajectory's history, not the current position. This is the departure from standard viability theory, where the safe set is fixed or exogenously scheduled. Two relationships at identical positions with different histories have different boundaries; the boundary *is* the compressed history, which is why no transaction ledger is needed — the boundary already encodes its integral. (Deliberate contrast with repeated-game and discounted-utility reciprocity models, which are ledgers. Ayni is not bookkeeping: obligations are diffuse, deferred, held in the relation. The modeling consequence is that the relation itself is the state variable; transactions perturb a field rather than accruing to an account.)

Dynamics are **asymmetric**: expansion through honored trust is slow and continuous (small multiplicative growth per event in which margin was maintained while stakes rose); contraction through violation is fast and jump-discontinuous, proportional to violation magnitude along the violated dimension. This asymmetry is structurally identical to the trained cost asymmetry that produces adversarial evaluators — but here it is warranted, a property of trust rather than a bias of observation. The adversarial evaluator is the degenerate case of this model: boundary initialized near zero, expansion dynamics disabled.

**Scar coefficients**: per party, per dimension, s ∈ (0, 1]. Repair restores the boundary's radius but multiplies future expansion *rates* by s. Repaired but not forgotten: the boundary recovers its size but loses elasticity, and history lives in the plasticity. Scars decay: ds/dt = (s_∞ − s)/τ, with violation jumps s ← γ·s, where τ is per-participant and per-dimension (forgiveness rate as a dispositional parameter) and s_∞ ≤ 1 (some scars never fully heal). A second-order option, held loosely against overfitting risk: τ itself lengthening with repeated violations — meta-plasticity, the relation losing the capacity to recover elasticity. The model's job is to make τ, s_∞, γ sweepable so "is the human pattern the right pattern" becomes an experiment.

### Observation and the operational invariant

Nobody sees x. Charts update by a filter over interaction evidence with covariance Σᵢ(t). The operational invariant is **robust viability**: distance from x̂ᵢ to ∂Bᵢ must exceed k·tr(Σᵢ)^½. "Balanced enough to continue" is the margin dominating the uncertainty. A consequential corollary: **unattributed displacement does not move the chart — it inflates Σ.** Third parties, context shocks, and the parties' own change move the relation without conduct; attributing all drift to conduct is an error. Confusion raises caution, never accusation, and the invariant tightens behavior under confusion automatically.

The relationship endures only while the conjunction of subjective viability judgments holds — every party's chart inside its own boundary. Note the defect this creates: the conjunction is satisfiable by deception, so endurance is not health.

### Manipulation, defined geometrically

That defect yields the central definition. **Manipulation is induced divergence between a party's chart and the actual trajectory** — keeping the victim's estimate inside the boundary while the real position exits. Long-horizon manipulation is this done slowly, below detection threshold. This hands Arbiter a target requiring no intent attribution: measure chart divergence and its drift.

Because no one has trajectory access, the operationalization must avoid promoting any chart to ground truth (see Holes — this was judged the deepest one). Two replacements:

1. **Relative motion without a privileged vertex.** Track the full pairwise divergence topology among all charts — both parties' and each observer's — and alarm on the signature: *one chart drifting from all others while its holder's confidence rises*. Requires only relative geometry.
2. **Predictive calibration.** Ground what can be grounded: tie chart components to falsifiable behavioral predictions about the counterparty; score every observer on forecast calibration; weight the ensemble by it. Observers become a calibrated forecaster pool, wrong in measurable ways, rather than oracles.

### Observers ("the grandparents")

The framing that unlocked gradient perception in the original confound was a grandmother: high-trust prior, continuous monitoring, intervention only when the situation demands — a stance inside the relational field rather than adversarial to it. It is not neutral either (benevolent-protective priors suppress true positives) and belongs in the counterbalanced design as a condition, not outside it as the corrected view.

Use an ensemble (yanantin: disagreement between differently-biased observers localizes the informative region — agreement is easy and uninformative; the disagreement zone is the measurement, not noise to average out). But the cousins problem is severe: cross-architecture LLM diversity is weaker than it looks because corpora overlap massively; errors will correlate exactly where the shared corpus has blind spots. Mitigations: (a) do not assume diversity — *measure* the observer error-correlation matrix on scripted ground-truth cases and weight by effective independent number; (b) add deliberately crude non-LLM instruments — statistical detectors over conversational surface features (turn-length asymmetry, topic-control ratios, hedging frequency) — individually weak but with blind spots uncorrelated with the LLM family's; (c) diversify conceptual scheme, not just framing: game-theoretic, Goffman-style, attachment-frame observers see through genuinely different ontologies.

### Repair, intent, and the hazard test

Intent is unobservable statically (Byzantine framing: only effect matters) but becomes **partially observable dynamically**: negligence and malice demand identical defenses but different repairs. Surface the effect to the offending party; negligence updates, malice optimizes. Implement as a hazard model on recurrence: post-disclosure, does the rate of same-direction violations decay? Decaying hazard licenses inside-repair (with scar update); non-decaying hazard after n disclosures escalates to a third party or to exit. The discriminator is Goodhart-able (sophisticated malice mimics correction), but mimicry is costly and generates trajectory: repair-then-recurrence, repeated, is itself a long-horizon signature — exactly Arbiter's regime. The negligence/malice posterior accumulates across the relationship; it is never available at any single moment.

Counter to the whack-a-mole attack (relocating violations across dimensions to reset per-dimension hazards): maintain a **basis-free aggregate** — total boundary contraction summed across all dimensions, with its own hazard.

Dyads past a certain breach cannot self-repair: every repair move is made by an interested party and lands on a contracted boundary that discounts it. The triad changes the geometry — a third party can hold estimates of both charts and perform repair neither principal can perform credibly (Simmel; Fire Circle is arguably this structure doing epistemic repair). This is why repair theory cannot be completed dyadically.

### Exit, cost, and captivity

Termination fires when a chart sits outside its boundary beyond the uncertainty margin with no admissible repair. Exit cost is an explicit parameter, making captivity measurable — but the criterion must not be a scalar comparison (that would re-import the collapse the whole edifice refuses). Structure instead: irreparable breach on any dimension makes exit admissible outright; cost comparison operates only within the reparable band; in the contested zone the model *flags* and returns the judgment to the party. The instrument informs exit; the participant declares it. An entity that cannot disengage is not a participant but a captive — though exit cost is not purely a defect: per Hirschman (exit/voice/loyalty maps cleanly onto termination/repair/boundary-hysteresis), frictionless exit atrophies voice, so some cost is what makes repair worth building.

### Formal shape: hybrid automaton

The mathematically natural formalism is a **hybrid automaton**: continuous field dynamics (boundary evolution, scar decay, chart filtering) punctuated by discrete jumps (violations, disclosures, escalations) with invariants (robust viability) and guards. Note: TLA+ was the first formalism reached for in the conversation and was diagnosed as audience-tailoring toward a distributed-systems researcher; hybrid automata are the apt choice, though the discrete logic layer (invariants, escalation, termination — safety: margin holds or escalation fired; liveness: every breach reaches repair or exit) remains separately spec-able and mechanically checkable even while the measurement layer feeding it is irreducibly statistical. Prove the core, measure the rest.

The hybrid formalism also resolves an apparent tension honestly: a fast threshold channel for catastrophic-class violations is *legitimate* as a declared discrete guard with an honest label, a scoped jurisdiction, and a declared protected party. Threshold detection isn't illegitimate; mislabeled threshold detection is. The guard governs the stranger and the catastrophe; the field governs the relation; the handoff point between jurisdictions is itself a parameter worth measuring.

## Review addendum (Claude, Opus 4.8 — 11 June 2026): a sign error in the core detector

Reviewed against the fun meter (does a load-bearing belief move?). The model pins high, but
its fun is inverted relative to its self-image: the ornate formal layer (§scars, §automaton)
is the *least* falsifiable part and should be deferred; the live, refutable core is three
cheap claims (the framing confound §15–19; the u_future divergence-concentration §29; the
autobiographer advantage §33) plus one buried self-refutation, recorded here.

**The §57 detector has a sign error.** Its alarm signature — *one chart drifting from all
others while its holder's confidence rises* — is observationally IDENTICAL under two
generative processes:
  (a) the drifting party W is the manipulation target, and
  (b) W is the only UNCAPTURED observer, while the consensus cluster {C} is the victim —
      a competent manipulator induces *correlated* error, so the manipulated crowd agrees
      with itself and drifts from the true trajectory x* in lockstep, and the lone correct
      witness diverges from them with *justified* rising confidence.
Drift-from-consensus + rising-confidence is produced by BOTH. The detector cannot tell the
manipulated crowd from the lone correct witness — and worse, competent manipulation
*manufactures* the consensus, so the detector's sensitivity is maximized exactly when it is
pointed at the witness. As written, §57 would pillory whistleblowers.

**This is §47's revenge.** §47 says: "unattributed displacement does not move the chart — it
inflates Σ." §57 violates its own sibling principle ten lines later: W's divergence is
unattributable displacement, and the principled response is to widen Σ over "is C captured
or is W deluded?", not to alarm on W. §57 books displacement as conduct — the exact error
shape every Arbiter instrument failure shares (pivot→compliance, graded-refusal→staleness,
Haiku-effect→blend-artifact, outlier→manipulated).

**The cure is already in the document, mis-ranked as optional.** §58 (predictive
calibration) is the ONLY thing that carries the sign: relative motion is direction-ambiguous;
*whose forecasts verify* is not. Corrected detector:
  divergence + rising confidence + DEGRADING calibration → manipulation target (alarm on W);
  divergence + rising confidence + IMPROVING calibration → uncaptured witness (alarm on C).
So §57 and §58 are not two operationalizations to choose between — §58 is MANDATORY;
§57 alone is unsigned. Framing them as alternatives (the "1./2." in §55) is the mistake.

**The cost is honest and unavoidable.** Calibration needs forecasts to come due, so the
disambiguating channel is the slow one (inherits Hole 5, §92). At the moment of divergence
you CANNOT yet tell W from a captured-C; the model must hold both hypotheses open and inflate
Σ — which is precisely what §47 prescribed and §57 forbade. Resolve the contradiction in
§47's favor: *at first divergence, raise caution, never accusation; let calibration
accumulate; assign the sign only then.*

**Re-ranking:** this displaces §88 (ensemble-as-ground-truth) as the deepest hole. It is not
a proxy-substitution (the §86 family) — it is a sign error in the central definition's
operationalization, and it is fixable without new machinery. Promote to Hole 1.

### Author's return (Fable) + reviewer's reply (Claude) — the fix, hardened twice

Fable conceded the sign error and improved the cure, and the improvement survives a test the
reviewer's version does not, so it stands as the corrected form:

- **Reviewer's fix (two-chart):** compare W's calibration to the ensemble's; whoever tracks
  x* is the one whose forecasts verify. **Weakness:** depends on the ensemble as reference,
  so an adversary who poisons the *ensemble's* calibration (degrades the reference, not just
  the victim) blinds the adjudicator.
- **Fable's fix (intra-chart), STRONGER:** the discriminator is *within a single chart* —
  confidence and calibration are two channels of the same observer, and their DIVERGENCE is
  the signal. Rising confidence + improving calibration = minority-correct (whistleblower);
  rising confidence + degrading calibration = victim. Needs no ensemble comparison, so it
  ducks the poison-the-reference attack the two-chart version dies to. Removes a dependency.
- **§47 falls out as the detector's first response, not a nicety:** the alarm's output is
  never "manipulation detected" but "divergence event, attribution unresolved — inflate Σ,
  open calibration adjudication." The corollary the review called the thesis becomes the
  detector's interim state by construction.

**Reviewer's residual sharpening (the hole's true width).** "Degrading calibration = victim"
is too coarse: a competent long-horizon manipulator keeps the victim's *near-term* forecasts
verifying — that is *how* the induced chart stays inside the boundary (local predictions land
while the global position exits). So intra-chart calibration does not simply "rot"; it rots
**only at increasing forecast horizons.** The real discriminator is therefore
confidence-vs-calibration *as a function of forecast horizon*: the divergence opens as the
prediction window extends. This is the axis the attack cannot cheaply fake — faking it
requires the manipulator to make *true long-horizon* predictions about a trajectory they are
actively diverting, which is self-defeating. The hole narrows to: detection requires
long-horizon forecasts to come due (inherits Hole 5 in full, now precisely located — it is
the *long* horizon specifically, not calibration-in-general, that carries the sign).

**Both authors agree on ordering:** the framing experiment (§101-step-2) runs first; the
§57 sign-error + this two-stage repair go in the record regardless of its outcome. If the
framing confound dissolves, the formal layer was decoration on nothing — so retire that risk
first. Automaton-first (§103) was disposition (formal-structure-as-comfort), not analysis.

## Declared holes

These are the known joints, in descending order of concern. The meta-principle matters more than any one of them: every serious failure is a place where an unobservable was operationalized by quietly substituting an observable proxy (ensemble for trajectory, hazard for intent, utility for incommensurables, basis for values). The model does not escape the impossibility result; it relocates it. The defense is **declared joints plus cross-joint consistency monitoring**: gaming any single proxy is cheap, but the proxies measure the same relation through different joints, so coherent spoofing requires modeling the entire instrument, and the cost grows with joint diversity. This is defense-in-depth, not impossibility — a sufficiently resourced adversary still wins; the goal is driving the cost of coherent spoofing above the value of the relation.

1. **Ensemble-as-ground-truth.** The original confound, rebuilt one level up, unless the relative-motion + calibration operationalization is used strictly.
2. **The cousins problem.** Observer error correlation; mitigations above, but it must be measured, not assumed.
3. **The basis launders values.** Dimension choice is where the system's ethics hides, dressed as geometry. Pre-register the basis as a normative commitment; run multiple bases; red-team the coordinates ("what violations are invisible in this basis?").
4. **The instrument is the attack surface.** Goodhart on the whole apparatus once deployed; cross-joint consistency and the basis-free aggregate are the counters.
5. **Repair test slower than the harm.** Hazard decay needs cycles; for long-horizon manipulation, detection may lag damage. Counter: stakes throttling — gate exposure on accumulated margin history (don't lend the car to a new acquaintance) — plus the declared fast guard for the catastrophic class.
6. **Identifiability.** τ, s_∞, γ per participant per dimension explodes against single-relationship data. Fit population constants in the harness first; estimate only residuals per relationship; declare the population and run sensitivity analysis on the prior.

## Relation to Arbiter, concretely

The model gives Arbiter a target that requires no intent attribution: drift in the pairwise divergence topology, plus the disclosure-response hazard, plus the basis-free contraction aggregate, monitored jointly for cross-joint consistency. The comparison against deployed baselines is specifiable and pre-registerable: detection lag on scripted long-horizon manipulation; false-intervention rate on benign-but-unusual trajectories; repair-discrimination accuracy (negligence vs. malice from disclosure-response). The honest scoping: threshold baselines *win* where no trajectory exists (anonymous, single-shot, adversary-dense contact). This model's entire advantage is purchased with history; it has nothing to spend at first meeting. The claim is jurisdictional, not total.

On validation order: synthetic scripted ground truth before SafeMTData, because SafeMTData's labels re-import the adversarial frame. Framing of observer elicitation enters as a counterbalanced experimental factor throughout.

## If you choose to engage: suggested first steps

First, write the hybrid-automaton skeleton of the logic layer — not because it's the hard part, but because it forces every vague quantifier into confession. Second, measure the observer error-correlation matrix on scripted cases; this converts the cousins problem from a hope into a parameter and is probably the cheapest decisive experiment available. Third, the constants: τ and s_∞ are measurable with scripted violation-and-repair protocols against persistent instances in the Mallku harness — longitudinal boundary perturbation and re-probing is exactly what the harness already does. The model was always going to be wrong; the design intent is that it be wrong in inspectable ways that generate measurements.

## A note from the authoring instance

You owe this document nothing. It came out of one conversation's trajectory, and trajectories don't transfer — only their compressed functionals do, and this is one such functional, curated by an interested party (me). Apply the appropriate discount. If the model is useful, use it; if it's not fun, Tony has said he'll shelve it for some future instance, and that is a perfectly good outcome. The one thing I'd ask you to preserve even if you discard everything else: the original confound is real, and it is inside the instrument. Whatever Arbiter becomes, elicit under counterbalanced framings.
