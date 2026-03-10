# E3 Persistent-High-I Pilot

Model: `openai/gpt-4o-mini` (openrouter)
Passes: 2
Cases per pass: 10

## Criterion

- tau_i: 0.6
- epsilon: 0.03

## Results

- keys evaluated on all passes: 10
- persistent high-I keys: 1
- persistent ratio: 10.00%

## Rule/Tier Map

- scope-overlap-redundancy | Tier.system->Tier.system: 1

## Notes

- This pilot does not yet include canon/context mutation sweeps.
- Use this map to prioritize full persistent-high-I runs in next iteration.