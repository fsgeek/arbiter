export const meta = {
  name: 'axes-one-or-three',
  description: 'Adversarially test whether the three incoherence types are one axis or three',
  phases: [
    { title: 'Separate', detail: 'three skeptics, each proving one pair irreducibly distinct' },
    { title: 'Unify+Dimension', detail: 'one collapser, one dimensional analyst — independent reframes' },
    { title: 'Adjudicate', detail: 'adversarial judge renders a falsifiable verdict' },
  ],
}

const CONTEXT_PATH = '/home/tony/projects/arbiter/docs/research/axes_inquiry_context.md'
const GROUND = `Read ${CONTEXT_PATH} in full first — it is the verified substrate. Also read /home/tony/projects/arbiter/docs/spine-audit.md and /home/tony/projects/arbiter/docs/headwater.md for the source framing. Cite specific grounded facts (commits, R2 numbers, the 81%/r=-0.274 dissociation), not vibes. The project's prime directive is epistemic honesty: say what you know, what you don't, and what you made up. Abstraction-to-vacuity ("all incoherence in a gap") is a known failure mode here — it does not count as an answer.`

const SEP_SCHEMA = {
  type: 'object',
  required: ['pair', 'verdict', 'distinguishing_property', 'falsifier', 'confidence', 'honest_doubt'],
  properties: {
    pair: { type: 'string' },
    verdict: { type: 'string', enum: ['irreducibly_distinct', 'collapsible', 'undetermined'] },
    distinguishing_property: { type: 'string', description: 'A property provably present in one type and absent in the other — KIND not instantiation. Or state none found.' },
    is_kind_or_instantiation: { type: 'string', enum: ['kind', 'instantiation', 'unclear'], description: 'Is the difference a difference in kind, or just two instantiations of one thing under different conditions?' },
    falsifier: { type: 'string', description: 'What observation on reachable substrate would refute this verdict.' },
    confidence: { type: 'number' },
    honest_doubt: { type: 'string', description: 'The strongest argument against your own verdict.' },
  },
}

const REFRAME_SCHEMA = {
  type: 'object',
  required: ['reframe_name', 'claim', 'discriminating_prediction', 'differs_from_rival', 'falsifier', 'confidence', 'honest_doubt'],
  properties: {
    reframe_name: { type: 'string' },
    claim: { type: 'string' },
    discriminating_prediction: { type: 'string', description: 'A prediction this reframe makes that the rival framing (one vs three) does NOT — concrete.' },
    differs_from_rival: { type: 'string', description: 'Exactly where this reframe and its rival would disagree on an observation.' },
    falsifier: { type: 'string' },
    confidence: { type: 'number' },
    honest_doubt: { type: 'string' },
  },
}

phase('Separate')
const PAIRS = [
  { key: 'A-vs-B', desc: 'Binding-conflict (A) vs Granularity (B). A needs a PAIR + unobservable O; B needs neither — one constraint, wrong resolution. Is that a difference in KIND or just instantiation?' },
  { key: 'A-vs-C', desc: 'Binding-conflict (A) vs Frame-relative (C). Both are pairs of individually-correct fragments. A has syntactic opposition + hidden O; C is surface-clean, conflict in pragmatic frame. Does the structural oracle distinguish them, and does that distinction reflect a real difference in kind?' },
  { key: 'B-vs-C', desc: 'Granularity (B) vs Frame-relative (C). B is a single constraint at wrong resolution; C is a frame mismatch between two. Could granularity BE a special case of frame mismatch (resolution = a frame)? Or provably not?' },
]

const separations = await parallel(PAIRS.map(p => () =>
  agent(`${GROUND}\n\nYou are a SEPARATOR. Your job: try as hard as you honestly can to prove these two incoherence types are irreducibly DISTINCT KINDS, not two instantiations of one thing. ${p.desc}\n\nThe discipline: a difference in INSTANTIATION ("A happens to involve scale, B happens to involve tree depth") is NOT a difference in kind. A difference in KIND means there is a property of one provably absent in the other under ALL instantiations. If you cannot find one, say verdict=collapsible and explain what collapses them. Do not manufacture a distinction to look productive.`,
    { label: `sep:${p.key}`, phase: 'Separate', schema: SEP_SCHEMA })
      .then(r => ({ ...r, pair: p.key }))
))

phase('Unify+Dimension')
const reframes = await parallel([
  () => agent(`${GROUND}\n\nYou are the UNIFIER. Claim: all three types are projections of ONE underlying axis. But you are FORBIDDEN the vacuous unification ("all gaps"). Your unification only counts if it names the single axis concretely AND makes a discriminating prediction that a three-types model does not — e.g., predicts a transformation that converts one type into another, or predicts a measurement on which all three fall on a single ordering. Confront the hard constraint: Paper 3 proves within-instruction clarity (81%) and between-instruction topology dissociate. If they dissociate, how can there be one axis? Either explain the dissociation within one axis or concede.`,
    { label: 'unify', phase: 'Unify+Dimension', schema: REFRAME_SCHEMA }),
  () => agent(`${GROUND}\n\nYou are the DIMENSIONAL ANALYST. Reject the false binary. Do NOT ask "one or three." Ask: what are the actual INDEPENDENT PARAMETERS along which an incoherence varies? Candidate dimensions to consider and test: (1) arity — does the conflict need 1 fragment or a pair? (2) observability — is the disambiguator inside the prompt, or in an unobservable operating context O? (3) detection-surface — syntactic (oracle sees it) vs pragmatic/frame (oracle blind)? (4) resolution-locus — does fixing it require choosing a governing fragment, choosing a frame, or re-resolving granularity? Map the three named types as POINTS in this parameter space. The real finding may be: there are N orthogonal dimensions, the three named types sample them non-uniformly, and "one vs three" was the wrong question. State how many dimensions you find, whether the three types are linearly independent in that space, and the discriminating prediction this view makes.`,
    { label: 'dimension', phase: 'Unify+Dimension', schema: REFRAME_SCHEMA }),
])

phase('Adjudicate')
const dossier = JSON.stringify({ separations: separations.filter(Boolean), reframes: reframes.filter(Boolean) }, null, 2)
const verdict = await agent(`${GROUND}\n\nYou are the ADJUDICATOR — adversarial, skeptical, and you have read the spine-audit so you know this project's instances have a documented pull toward premature closure and toward welding distinct things into one word. Here is the full dossier of separator and reframe findings:\n\n${dossier}\n\nYour job is NOT to average them. Render a verdict on: ONE axis, THREE types, or N-dimensional space (and if N, what N and which dimensions). The verdict is only admissible if it comes with: (1) a falsifiable discriminating prediction on substrate Tony can actually reach (note: the case #11 governance/ runs are NOT on the working tree tonight — so the experiment must be designable but need not be runnable tonight); (2) an explicit statement of what would make you WRONG; (3) identification of any place where an agent below committed the abstraction-to-vacuity sin or welded instantiation-difference into kind-difference. If the honest answer is "undetermined, here is the single experiment that would determine it," that is a VALID and preferred verdict over false closure. End with the ONE question you would put to Tony.`,
  { label: 'adjudicate', phase: 'Adjudicate', schema: {
    type: 'object',
    required: ['verdict', 'dimensions_if_N', 'discriminating_prediction', 'what_would_make_me_wrong', 'vacuity_or_weld_caught', 'designable_experiment', 'one_question_for_tony', 'confidence'],
    properties: {
      verdict: { type: 'string', enum: ['one_axis', 'three_types', 'N_dimensional', 'undetermined_with_decisive_experiment'] },
      dimensions_if_N: { type: 'array', items: { type: 'string' } },
      discriminating_prediction: { type: 'string' },
      what_would_make_me_wrong: { type: 'string' },
      vacuity_or_weld_caught: { type: 'string' },
      designable_experiment: { type: 'string', description: 'Concrete experiment, what substrate, what it would show, why it falsifies.' },
      one_question_for_tony: { type: 'string' },
      confidence: { type: 'number' },
    },
  } })

return { separations: separations.filter(Boolean), reframes: reframes.filter(Boolean), verdict }
