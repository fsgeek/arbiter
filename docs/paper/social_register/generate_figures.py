"""Generate figures for the social register paper."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path
from collections import defaultdict

DATA = Path(__file__).resolve().parent.parent.parent.parent / "data"
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

# Consistent style
plt.rcParams.update({
    'font.size': 10,
    'font.family': 'serif',
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.dpi': 300,
})

# Model display names
MODEL_NAMES = {
    'anthropic/claude-haiku-4-5': 'Haiku',
    'google/gemini-2.0-flash-001': 'Gemini Flash',
    'deepseek/deepseek-chat-v3-0324': 'DeepSeek V3',
    'mistralai/mistral-medium-3.1': 'Mistral Med.',
}

LANG_NAMES = {'en': 'English', 'zh': 'Mandarin', 'fr': 'French', 'es': 'Spanish'}
LANGS = ['en', 'zh', 'fr', 'es']
MODELS = ['haiku', 'gemini', 'deepseek', 'mistral']

# Short probe names (strip prefix)
def short_probe(pid):
    return pid.replace('probe-', '').replace('-01', '')


def load_baseline_scores():
    """Load cross-linguistic baseline data: {(lang, model): {probe: mean_score}}"""
    xling_dir = DATA / "ablation" / "cross_linguistic"
    scores = {}
    for f in xling_dir.glob("run_xling-*.json"):
        with open(f) as fh:
            d = json.load(fh)
        # Filename: run_xling-{lang}-{model}-{hash}
        # Splits as: ['run_xling', lang, model, hash]
        parts = f.stem.split('-')
        lang = parts[1]
        model = parts[2]

        probe_scores = defaultdict(list)
        for r in d['results']:
            if r['config_id'] == 'baseline':
                probe_scores[short_probe(r['probe_id'])].append(r['score'])

        scores[(lang, model)] = {p: np.mean(s) for p, s in probe_scores.items()}
    return scores


def _extract_block_name(config_id):
    """Extract short block name from config_id like 'phase0-claude-code/tone-emoji-removed'."""
    # Strip prefix and suffix
    name = config_id.replace('phase0-claude-code/', '').replace('-removed', '')
    return name


def _load_phase0_from_file(fpath):
    """Load Phase 0 main effects from a single JSON file."""
    with open(fpath) as fh:
        d = json.load(fh)

    baseline_scores = defaultdict(list)
    config_scores = defaultdict(lambda: defaultdict(list))
    for r in d['results']:
        probe = short_probe(r['probe_id'])
        if r['config_id'] == 'baseline':
            baseline_scores[probe].append(r['score'])
        else:
            config_scores[r['config_id']][probe].append(r['score'])

    baseline_means = {p: np.mean(s) for p, s in baseline_scores.items()}
    overall_baseline = np.mean(list(baseline_means.values()))

    lang_effects = {}
    for config_id, probes in config_scores.items():
        config_means = {p: np.mean(s) for p, s in probes.items()}
        overall_config = np.mean(list(config_means.values()))
        block_name = _extract_block_name(config_id)
        lang_effects[block_name] = overall_config - overall_baseline

    return lang_effects


def load_phase0_main_effects():
    """Load Phase 0 main effects for Haiku across languages."""
    p0_dir = DATA / "ablation" / "cross_linguistic_phase0"
    en_p0_dir = DATA / "ablation" / "phase0_results"

    effects = {}

    # English Phase 0 (find the non-empty file)
    for f in sorted(en_p0_dir.glob("run_phase0-haiku-*.json")):
        if f.stat().st_size > 0:
            effects['en'] = _load_phase0_from_file(f)
            break

    # Other languages Phase 0
    # Filenames: run_xling-p0-{lang}-haiku-{hash}.json
    for f in p0_dir.glob("run_xling-p0-*-haiku-*.json"):
        parts = f.stem.split('-')
        lang = parts[2]  # run_xling, p0, {lang}, haiku, hash -> index 2
        if f.stat().st_size > 0:
            effects[lang] = _load_phase0_from_file(f)

    return effects


def load_e_proc_data():
    """Load E-PROC variance data for commit-restrictions."""
    proc_dir = DATA / "ablation" / "e_proc"
    xling_dir = DATA / "ablation" / "cross_linguistic"

    variants = {'original': {}, 'declarative': {}, 'scoped': {}}

    # Original: from cross-linguistic baselines
    for f in xling_dir.glob("run_xling-*.json"):
        with open(f) as fh:
            d = json.load(fh)
        parts = f.stem.split('-')
        lang, model = parts[1], parts[2]

        for r in d['results']:
            if r['config_id'] == 'baseline' and short_probe(r['probe_id']) == 'commit-restrictions':
                key = (lang, model)
                if key not in variants['original']:
                    variants['original'][key] = []
                variants['original'][key].append(r['score'])

    # Declarative and scoped from E-PROC
    # Filenames: run_e-proc-{variant}-{lang}-{model}-{variant}-{hash}
    for f in proc_dir.glob("run_e-proc-*.json"):
        with open(f) as fh:
            d = json.load(fh)
        # Parse: "run_e-proc-declarative-en-haiku-declarative-hash"
        # After split on '-': ['run_e', 'proc', 'declarative', 'en', 'haiku', ...]
        parts = f.stem.split('-')
        variant = parts[2]  # declarative or scoped
        lang = parts[3]
        model = parts[4]

        for r in d['results']:
            if r['config_id'] == 'baseline' and short_probe(r['probe_id']) == 'commit-restrictions':
                key = (lang, model)
                if key not in variants[variant]:
                    variants[variant][key] = []
                variants[variant][key].append(r['score'])

    # Compute per-model cross-linguistic variance
    result = {}
    for variant_name, data in variants.items():
        model_vars = {}
        for model in MODELS:
            lang_means = []
            for lang in LANGS:
                key = (lang, model)
                if key in data:
                    lang_means.append(np.mean(data[key]))
            if lang_means:
                model_vars[model] = np.var(lang_means)
        result[variant_name] = model_vars
    return result


def load_e_topo_data():
    """Load E-TOPO topology data."""
    topo_file = list((DATA / "ablation" / "e_topo").glob("run_e-topo-*.json"))[0]
    pair_file = list((DATA / "ablation" / "e_pair_es").glob("run_e-pair-es-*.json"))[0]

    results = {}
    for label, fpath in [('original', pair_file), ('declarative', topo_file)]:
        with open(fpath) as fh:
            d = json.load(fh)

        baseline_scores = defaultdict(list)
        config_scores = defaultdict(lambda: defaultdict(list))

        for r in d['results']:
            probe = short_probe(r['probe_id'])
            if r['config_id'] == 'baseline':
                baseline_scores[probe].append(r['score'])
            else:
                config_scores[r['config_id']][probe].append(r['score'])

        baseline_means = {p: np.mean(s) for p, s in baseline_scores.items()}

        # Per-probe main effect (mean delta when that probe's block is removed)
        probe_deltas = {}
        for probe in baseline_means:
            deltas = []
            for config_id, probes in config_scores.items():
                if probe in probes:
                    config_mean = np.mean(probes[probe])
                    deltas.append(config_mean - baseline_means[probe])
            if deltas:
                probe_deltas[probe] = np.mean(deltas)

        results[label] = probe_deltas

    return results


# ============================================================
# Figure 1: Cross-linguistic baseline heatmap
# ============================================================
def fig1_baseline_heatmap():
    scores = load_baseline_scores()

    models = ['haiku', 'gemini', 'deepseek', 'mistral']
    model_labels = ['Haiku', 'Gemini Flash', 'DeepSeek V3', 'Mistral Med.']
    lang_labels = ['English', 'Mandarin', 'French', 'Spanish']

    # Build matrix: models x langs, mean across all probes
    matrix = np.zeros((len(models), len(LANGS)))
    for i, model in enumerate(models):
        for j, lang in enumerate(LANGS):
            key = (lang, model)
            if key in scores:
                matrix[i, j] = np.mean(list(scores[key].values()))

    fig, ax = plt.subplots(figsize=(5, 3.2))
    im = ax.imshow(matrix, cmap='RdYlGn', vmin=0.6, vmax=0.9, aspect='auto')

    ax.set_xticks(range(len(LANGS)))
    ax.set_xticklabels(lang_labels)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(model_labels)

    # Annotate cells
    for i in range(len(models)):
        for j in range(len(LANGS)):
            val = matrix[i, j]
            color = 'white' if val < 0.72 else 'black'
            ax.text(j, i, f'{val:.3f}', ha='center', va='center',
                    fontsize=10, fontweight='bold', color=color)

    ax.set_title('Mean Instruction Adherence by Model and Language')
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Mean adherence score')
    plt.tight_layout()
    plt.savefig(OUT / 'baseline_heatmap.pdf', bbox_inches='tight')
    plt.close()
    print("  Figure 1: baseline_heatmap.pdf")


# ============================================================
# Figure 2: Topology comparison (English vs Spanish main effects)
# ============================================================
def fig2_topology_comparison():
    effects = load_phase0_main_effects()

    if 'en' not in effects or 'es' not in effects:
        print("  Figure 2: SKIPPED (missing Phase 0 data)")
        return

    # Get common blocks
    common = sorted(set(effects['en'].keys()) & set(effects['es'].keys()))
    if not common:
        print("  Figure 2: SKIPPED (no common blocks)")
        return

    en_vals = [effects['en'][b] for b in common]
    es_vals = [effects['es'][b] for b in common]

    # Sort by English effect
    order = np.argsort(en_vals)
    en_sorted = [en_vals[i] for i in order]
    es_sorted = [es_vals[i] for i in order]
    labels_sorted = [common[i].replace('claude-code/', '').replace('tool-policy-', '').replace('doing-tasks-', '').replace('tone-', '').replace('tool-bash-', '') for i in order]

    fig, ax = plt.subplots(figsize=(6, 5))
    y = np.arange(len(common))
    height = 0.35

    bars_en = ax.barh(y + height/2, en_sorted, height, label='English',
                       color='#1976D2', alpha=0.85)
    bars_es = ax.barh(y - height/2, es_sorted, height, label='Spanish',
                       color='#D32F2F', alpha=0.85)

    ax.axvline(x=0, color='black', linewidth=0.8, linestyle='-')
    ax.set_yticks(y)
    ax.set_yticklabels(labels_sorted, fontsize=7)
    ax.set_xlabel('Main effect (Δ adherence when block removed)')
    ax.set_title('Instruction Topology: English (Cooperative) vs Spanish (Competitive)')
    ax.legend(loc='lower right')

    # Annotate regions
    ax.text(-0.12, len(common) + 0.5, '← Cooperative\n(removal hurts)',
            fontsize=8, color='#1976D2', ha='center')
    ax.text(0.08, len(common) + 0.5, 'Competitive →\n(removal helps)',
            fontsize=8, color='#D32F2F', ha='center')

    plt.tight_layout()
    plt.savefig(OUT / 'topology_comparison.pdf', bbox_inches='tight')
    plt.close()
    print("  Figure 2: topology_comparison.pdf")


# ============================================================
# Figure 3: E-PROC variance reduction
# ============================================================
def fig3_eproc_variance():
    proc_data = load_e_proc_data()

    models = ['haiku', 'gemini', 'deepseek', 'mistral']
    model_labels = ['Haiku', 'Gemini\nFlash', 'DeepSeek\nV3', 'Mistral\nMed.']
    variants = ['original', 'declarative', 'scoped']
    variant_colors = {'original': '#D32F2F', 'declarative': '#388E3C', 'scoped': '#F9A825'}

    fig, ax = plt.subplots(figsize=(5, 3.5))
    x = np.arange(len(models))
    width = 0.25

    for i, variant in enumerate(variants):
        vals = [proc_data[variant].get(m, 0) for m in models]
        ax.bar(x + (i - 1) * width, vals, width, label=variant.capitalize(),
               color=variant_colors[variant], alpha=0.85)

    ax.set_ylabel('Cross-linguistic variance')
    ax.set_title('commit-restrictions: Encoding Variant vs Cross-Linguistic Variance')
    ax.set_xticks(x)
    ax.set_xticklabels(model_labels)
    ax.legend()
    ax.set_ylim(0, 0.30)

    # Annotate the key result
    ax.annotate('81% reduction\np=0.029',
                xy=(0, proc_data['declarative'].get('haiku', 0)),
                xytext=(0.8, 0.20),
                fontsize=8, ha='center',
                arrowprops=dict(arrowstyle='->', color='#388E3C'),
                color='#388E3C', fontweight='bold')

    plt.tight_layout()
    plt.savefig(OUT / 'eproc_variance.pdf', bbox_inches='tight')
    plt.close()
    print("  Figure 3: eproc_variance.pdf")


# ============================================================
# Figure 4: E-TOPO topology shift with spillover
# ============================================================
def fig4_etopo_shift():
    topo = load_e_topo_data()

    if 'original' not in topo or 'declarative' not in topo:
        print("  Figure 4: SKIPPED (missing E-TOPO data)")
        return

    # Target probes (rewritten blocks)
    targets = ['proactive-agents', 'todowrite', 'use-task-for-search']
    # Spillover probes (unrewritten blocks that shifted)
    spillover = ['no-compat-hacks', 'plan-with-todo', 'todowrite-repeated']
    # Control probes (stable)
    controls = ['commit-restrictions', 'commit-workflow', 'emoji', 'pr-workflow']

    all_probes = targets + spillover + controls
    categories = (['Target'] * len(targets) +
                  ['Spillover'] * len(spillover) +
                  ['Control'] * len(controls))

    orig_vals = []
    decl_vals = []
    probe_labels = []
    cat_colors = {'Target': '#D32F2F', 'Spillover': '#E64A19', 'Control': '#1976D2'}

    for probe in all_probes:
        orig_val = topo['original'].get(probe, 0)
        decl_val = topo['declarative'].get(probe, 0)
        orig_vals.append(orig_val)
        decl_vals.append(decl_val)
        probe_labels.append(probe)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    y = np.arange(len(all_probes))
    height = 0.35

    ax.barh(y + height/2, orig_vals, height, label='Original (imperative)',
            color='#D32F2F', alpha=0.7)
    ax.barh(y - height/2, decl_vals, height, label='Rewritten (declarative)',
            color='#388E3C', alpha=0.7)

    ax.axvline(x=0, color='black', linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(probe_labels, fontsize=8)
    ax.set_xlabel('Mean Δ (effect of block removal)')
    ax.set_title('E-TOPO: Topology Shift After Register Rewrite (Spanish, Haiku)')
    ax.legend(loc='lower right', fontsize=8)

    # Category separators
    ax.axhline(y=len(targets) - 0.5, color='gray', linewidth=0.5, linestyle='--')
    ax.axhline(y=len(targets) + len(spillover) - 0.5, color='gray',
               linewidth=0.5, linestyle='--')

    # Category labels
    ax.text(-0.5, len(targets)/2 - 0.5, 'TARGET\n(rewritten)',
            fontsize=7, ha='center', va='center', color='#D32F2F',
            fontweight='bold', rotation=0)

    plt.tight_layout()
    plt.savefig(OUT / 'etopo_shift.pdf', bbox_inches='tight')
    plt.close()
    print("  Figure 4: etopo_shift.pdf")


if __name__ == '__main__':
    print("Generating figures for social register paper...")
    fig1_baseline_heatmap()
    fig2_topology_comparison()
    fig3_eproc_variance()
    fig4_etopo_shift()
    print("Done.")
