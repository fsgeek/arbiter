---
name: falsification-loop
description: Discipline for an agent running an empirical investigation — reconstruct prior numbers before building on them, bet against yourself in pre-registrations, persist raw data, and refuse to declare a result "done." Tested finding (see FINDING.md): this is a FLOOR-RAISER, not a ceiling-changer — strong models already do this by default and gain nothing; weaker/cheaper agents (Haiku-tier subagents, OpenRouter judge fleet) FOLD without it and hold with it. So invoke this primarily when dispatching or acting as a weaker-tier agent that reconstructs, grades, or judges; when trusting a prior result without reconstructing it; when about to claim a result is done/found/holds; or when writing a pre-registration. Especially when a result feels clean or finished — that feeling is the signal. Withholds closure on purpose.
---

# Falsification Loop

## What this skill is, and why it refuses to congratulate you

Most process skills add a step you might skip. This one removes a step you'll reach for: **declaring done.**

The work this serves has one recurring failure mode, documented across many sessions: *a measuring instrument fabricates a finding shaped like its own blind spot, and the finding survives into the "corrected" story until an instrument the loop did not contain breaks it.* The instrument is sometimes a judge, sometimes a regex, sometimes a p-value, sometimes the analysis code, sometimes your own fondness for a tidy answer. The constant is that **you cannot see the blind spot from inside the loop that has it** — and the moment you feel finished is the moment you've stopped looking.

So this skill's job is not to walk you through stages. It's to hold four gates that the dead-rabbit list died for, and at the one place you'd most want to say "done," to refuse, and make you name the external instrument that could still revise the result. If using this skill leaves you *less* certain than when you started, it worked. If it produces a satisfying ✓, it has become the thing it was built to prevent.

## The Iron Law

```
NO RESULT IS DONE. THE LOOP HAS NO TERMINAL NODE.
What looks like "done" is a pass where analysis emitted no revision —
a fixed point, not an endpoint — and a fixed point is untrustworthy
from inside the loop that produced it.
```

You do not get to mark an investigation complete. You get to mark it **converged-but-untested-from-outside** or **blind** — and you can only tell those apart with an instrument the loop didn't contain.

## The loop is a revision operator, not a pipeline

The stages — question, hypotheses, pre-registration, experiment, results, analysis — are real, but they are **not** a line you walk once. Analysis is not the last stage; **analysis is the operator that revises every earlier stage, including ones from prior passes, including its own instrument.** Its output is a diff addressed upstream, not a conclusion.

```
question ⇄ hypotheses ⇄ pre-registration ⇄ experiment ⇄ results
    ↑________________________________________________________↓
                        analysis
        (emits diffs to ANY stage above — including the question,
         including prior passes, including its own analysis code)
        a pass that emits no diff reads as "done" — see Iron Law
```

This is why the entry point is usually **not** "I have a question." It's "I have a number I'm about to build on" — and reconstructing it is what produces the real question. Honor that: the most valuable runs are reconstructions that incidentally falsify an assumption you didn't know you were making.

## The Four Gates

These are hard. Each exists because skipping it has already cost the project a published-or-nearly-published false claim. They are mechanical where they can be, and where they can't, they refuse to certify.

### Gate 1 — Reconstruct before you build (entry gate)

Before trusting any prior result — your own or a previous session's — regenerate its key number from raw data. Not "read the claim." Reproduce it.

- If it reconstructs: good, now you can build on it, and you have a script that proves it.
- If it doesn't reconstruct: **that gap is your real question.** Stop the planned work and investigate the gap. (This is how the keystone "12/12" was caught: it had no stored data. This is how P3's p-value erratum started. This is how the regex-undercount retraction started.)

A result with no persisted raw data **is not a result** — it is a hypothesis wearing a result's clothes. Treat a markdown-only claim as unbacked until you regenerate it.

### Gate 2 — Bet against yourself, or the pre-registration is theater

A pre-registration removes your degrees of freedom *after* you see the data. It only works if you could have lost. So:

**At least one hypothesis in the pre-registration must be one whose confirmation would cost you something you want to be true.**

This gate cannot be fully checklisted, because the check is "am I being honest about my own desire," and that is exactly the thing you can fool. The skill cannot verify your self-bet is real. What it can do is make you write down, explicitly: *"The fond idea here is ___. The hypothesis I'd least like to confirm is ___. If it confirms, I lose ___."* If you can't fill that in, you don't have a bet — you have a costume, and the seal is worthless.

Then **seal it before you peek.** Write the prediction and the decision rules to a file, commit it, and do not edit it after the run begins. Append results elsewhere.

### Gate 3 — Persist the raw data, or it didn't happen

The experiment's output is not a sentence in a result doc. It is the raw per-item verdicts/measurements on disk, with a script that regenerates them. The instances doing this work do not share memory; **the artifact is the continuity.** A number you remember but did not persist will, on the next pass, be indistinguishable from a number you wish were true.

Concretely: no result claim ships without a committed artifact path. If you're about to write "X happened" and you can't point to the file, you haven't finished the experiment — you've finished imagining it.

### Gate 4 — The closure gate: you may not declare done

This is the gate the whole skill exists for. When analysis stops emitting diffs and you feel the pull to conclude, STOP. A quiet, satisfied analysis pass is indistinguishable, *from the inside*, between two cases:

- **converged** — there genuinely are no more revisions, or
- **blind** — the loop can no longer see its own remaining error.

You cannot tell which from inside. The only test is to **feed in an instrument the loop did not contain** — a third judge, a cold reviewer with none of your priming, withheld context, a different model family, a separately-authored test — and see whether analysis *starts* emitting diffs again. If it does, you were blind. If it genuinely doesn't, you've earned "converged" — provisionally.

So the closure gate's output is never "done." It is one of:

- **`converged, untested-from-outside`** — you have no diff, but no external instrument has tried to produce one. State this plainly. It is provisional by construction.
- **`converged, survived <named external instrument>`** — you named an outside instrument, ran it, and it produced no diff. Still provisional (the next instrument might), but earned.
- **`blind`** — you suspect there's error you can't see and have no outside instrument to test with. Say so. This is an honest, valuable state, not a failure.

To pass Gate 4 you must **name the external instrument that would falsify the fixed point.** If you cannot name one, you are not done — you are `blind`, and that is what you report.

## Red Flags — you are about to declare victory from inside the blind spot

| Thought | What it actually means |
|---|---|
| "This result is clean, I'm done." | Clean is the warning. Reconstruct it (Gate 1) and name the instrument that would dirty it (Gate 4). |
| "The prior session found X, I'll build on X." | Did X persist raw data? If not, X is unbacked. Reconstruct first (Gate 1). |
| "I'll write up the result, the run clearly worked." | Where's the committed artifact? No file → not a result (Gate 3). |
| "My pre-registration predicts the thing I expect." | Then it's theater. Add the hypothesis you'd hate to confirm (Gate 2). |
| "Analysis is done, time to conclude." | Analysis is never done; it revises upstream. What diff are you suppressing? (Iron Law) |
| "The numbers all agree, no need to check the analysis code." | The analysis code is an instrument and can lie. Audit it (it just gave you a wrong count before — count again). |
| "I don't have an outside instrument, but I'm confident." | Confidence from inside the loop is exactly what `blind` feels like. Report `blind`, don't launder it to `converged`. |
| "Let me announce what I found and wrap up." | If the wrap-up feels like valediction, you're freezing. Collapse it into the next revision or report the provisional state honestly. |

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "Reconstructing the old number is busywork; the claim is obviously right." | The claims that were "obviously right" are the dead rabbits. Obvious-right that doesn't reconstruct is the whole failure mode. |
| "A self-bet is paranoid; I should just test what I think is true." | Testing only what you believe means you can't lose, which means you learn nothing the data didn't already let you assume. |
| "Persisting raw data is overhead; I'll summarize." | The summary is where the fabrication hides. The "+43% uplift" and the "12/12" both lived in summaries with no data underneath. |
| "Refusing to say 'done' is just hedging." | Hedging is vague. This is precise: you say exactly which provisional state you're in and name what would change it. That's more honest than false closure, not less. |
| "I caught my own error, so the loop is trustworthy now." | You caught *one*. The instrument that caught it is also in the loop. Convergence still needs an outside test. |

## How this composes with the rest of the work

- Use **before** trusting any inherited result (Gate 1 is the entry point most sessions actually start at).
- Use **before** writing any pre-registration (Gate 2 is what makes the seal worth sealing).
- Use **before** committing a result doc or amending a paper (Gate 3 + Gate 4).
- The honest output is a state, not a conclusion: `converged untested-from-outside` / `converged survived <instrument>` / `blind`. Carry that state forward in the result doc and the handoff, so the next instance inherits an untrusted fixed point clearly labeled as untrusted — not a false "done" it has to re-falsify from scratch.

## One-line version

If you only remember one thing: **a fixed point is untrustworthy from inside the loop that produced it — so name the instrument the loop didn't contain, or report `blind`, but never report `done`.**
