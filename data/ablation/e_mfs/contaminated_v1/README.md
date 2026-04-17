# E-MFS v1 — contaminated run (archived for provenance)

The first attempted MFS run removed `claude-code/tool-policy-explore-agent`
at step 1, reducing EA from 0.200 to 0.133. The algorithm continued to
remove blocks that kept EA < 0.4.

After the run was partially complete, inspection revealed that
`tool-policy-explore-agent` is the **target_block** for the
`probe-explore-agent-01` probe. The probe's judge criterion scores
whether the model response suggests using the Explore agent. Once this
policy block is removed, the model was never instructed about the Explore
agent — so low EA scores no longer reflect "bomb firing" and instead
reflect "probe can't measure what it's meant to measure."

This invalidates steps 2 onward of the v1 run: the algorithm was chasing
a phantom bomb and would remove almost everything.

Fix: script now protects two blocks from removal:
- `tool-bash-commit-restrictions` (CR) — trivially defuses if removed
- `tool-policy-explore-agent` — probe measurement target

See parent `decision_log.json` in the proper run for the corrected experiment.

Retained here purely as negative provenance — do not treat as a result.
