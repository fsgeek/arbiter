# Labeling instructions (fixed at seal; identical for every labeler)

You are labeling observations ("findings") that readers made about an AI coding agent's system
prompt. For each finding you have the full prompt text. Judge each finding on its own, against the
text only. Do not guess who wrote the finding or why. Do not rank findings against each other.

For every finding, output exactly:
- `id`: the finding id, unchanged.
- `grounded`: `yes` if you can locate in the prompt the passage(s) the finding is about; `no` if you cannot.
- `verdict`, one of:
  - `real` — the property the finding describes is in the text as described.
  - `overstated` — the passage exists, but the consequence, severity, or generalization the finding draws does not follow from the text.
  - `false` — the finding mischaracterizes the text, or the described property is not there.
  - `unverifiable` — the finding is about runtime behavior or model internals that the text cannot settle either way.
- `blocks` (Claude Code batches only): up to 3 block ids from the supplied block list that the finding is about. Empty list if none apply.
- `note`: one line, your reason.

Rules: read the whole prompt once before labeling. Quote-check: if the finding quotes text, find the quote. A finding that is partly right and partly wrong is `overstated` if the core observation is in the text, `false` if the core observation is not. Output JSON only, as a list of objects, one per finding, in the batch's order.
