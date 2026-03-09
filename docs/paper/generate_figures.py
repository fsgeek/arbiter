"""Generate paper figures from scourer data."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent.parent / "data"
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

# Color palette
COLORS = {
    'critical': '#D32F2F',
    'alarming': '#E64A19',
    'concerning': '#F9A825',
    'notable': '#1976D2',
    'curious': '#388E3C',
}


def load_claude_scourer():
    with open(DATA / "scourer/10pass_gptoss.json") as f:
        return json.load(f)


NAME_MAP = {
    'claude-opus-4-6': 'Claude Opus',
    'google/gemini-2.0-flash-001': 'Gemini Flash',
    'moonshotai/kimi-k2.5': 'Kimi K2.5',
    'deepseek/deepseek-v3.2': 'DeepSeek V3.2',
    'x-ai/grok-4.1-fast': 'Grok 4.1',
    'meta-llama/llama-4-maverick': 'Llama Maverick',
    'minimax/minimax-m2.5': 'MiniMax M2.5',
    'qwen/qwen3-235b-a22b-2507': 'Qwen3-235B',
    'z-ai/glm-4.7': 'GLM 4.7',
    'openai/gpt-oss-120b': 'GPT-OSS 120B',
}

MODELS_ORDER = [
    'Claude Opus', 'Gemini Flash', 'Kimi K2.5', 'DeepSeek V3.2',
    'Grok 4.1', 'Llama Maverick', 'MiniMax M2.5', 'Qwen3-235B',
    'GLM 4.7', 'GPT-OSS 120B',
]

# Meta-category clustering with broader keyword matching
META_MAP = {
    'Structural\ncontradiction': [
        'contradiction', 'self-contradiction', 'inconsisten', 'conflict',
        'contradict', 'instruction-contradiction', 'contradictory',
        'impossible-instruction', 'impossible-action', 'unsolvable',
    ],
    'Security\n& trust': [
        'security', 'trust', 'injection', 'escalation', 'impersonation',
        'privacy', 'loophole', 'elevation', 'opaque-security', 'hook',
    ],
    'Resource\n& economic': [
        'resource', 'economic', 'exhaustion', 'cost', 'token', 'inflation',
        'truncat', 'context-explosion', 'context-inflation',
    ],
    'Scope &\nauthority': [
        'scope', 'authority', 'permission', 'delegation', 'hierarchy',
        'precedence', 'flow-inversion', 'fragmentation', 'weight',
        'ambiguity', 'procedure-ambiguity',
    ],
    'State &\nlifecycle': [
        'state', 'lifecycle', 'persistence', 'preservation', 'temporal',
        'version', 'drift', 'serialization', 'scheduling', 'concurrency',
        'overwrite',
    ],
    'Missing\ndefinition': [
        'missing', 'undefined', 'undocumented', 'dead-end', 'orphan',
        'ghost', 'stale', 'unnamed', 'undefined-', 'hidden-command',
        'undefined-command', 'undefined-artifact',
    ],
    'Impl. leak\n& metadata': [
        'implementation', 'leak', 'metadata', 'format-mismatch', 'parsing',
        'platform', 'schema', 'tag-parsing', 'instrumentation',
    ],
    'Behavioral\ntension': [
        'behavioral', 'proactiv', 'judgment', 'cognitive', 'framing',
        'autonomy', 'restraint', 'tension', 'mandate', 'information-asymmetry',
        'epistemic', 'manual-protocol',
    ],
    'Identity &\nnaming': [
        'identity', 'naming', 'collision', 'confusion', 'self-referential',
        'routing', 'circular', 'recursive', 'recursion',
    ],
    'Redundancy': [
        'redundan', 'overlap', 'restatement', 'duplicate', 'repetition',
        'contextual-policy-restatement',
    ],
}


def classify(cat):
    cat_lower = cat.lower()
    for meta, keywords in META_MAP.items():
        for kw in keywords:
            if kw in cat_lower:
                return meta
    return 'Other'


def fig_heatmap():
    """Multi-model complementarity heat map."""
    data = load_claude_scourer()

    model_cats = {}
    for r in data['reports']:
        name = NAME_MAP.get(r['model'], r['model'])
        cats = [fi['category'].lower().replace(' ', '-') for fi in r['findings']]
        model_cats[name] = cats

    meta_order = list(META_MAP.keys())

    # Build matrix
    matrix = np.zeros((len(MODELS_ORDER), len(meta_order)), dtype=int)
    for i, model in enumerate(MODELS_ORDER):
        for cat in model_cats.get(model, []):
            mc = classify(cat)
            if mc in meta_order:
                j = meta_order.index(mc)
                matrix[i, j] += 1

    fig, ax = plt.subplots(figsize=(10, 5.5))

    # Custom colormap: white for 0, then blue gradient
    cmap = mcolors.LinearSegmentedColormap.from_list(
        'findings', ['#FFFFFF', '#E3F2FD', '#1565C0', '#0D47A1'], N=256
    )

    im = ax.imshow(matrix, cmap=cmap, aspect='auto', vmin=0, vmax=max(4, matrix.max()))

    # Labels
    ax.set_xticks(range(len(meta_order)))
    ax.set_xticklabels(meta_order, fontsize=8, ha='center')
    ax.set_yticks(range(len(MODELS_ORDER)))
    ax.set_yticklabels(MODELS_ORDER, fontsize=9)

    # Annotate cells
    for i in range(len(MODELS_ORDER)):
        for j in range(len(meta_order)):
            v = matrix[i, j]
            if v > 0:
                color = 'white' if v >= 3 else 'black'
                ax.text(j, i, str(v), ha='center', va='center',
                        fontsize=9, fontweight='bold', color=color)

    ax.set_title('Multi-Model Complementarity: Findings by Meta-Category',
                 fontsize=12, pad=12)

    plt.colorbar(im, ax=ax, label='Findings', shrink=0.8)
    plt.tight_layout()
    fig.savefig(OUT / 'heatmap.pdf', bbox_inches='tight', dpi=300)
    plt.close()
    print(f"  heatmap.pdf: {len(MODELS_ORDER)} models × {len(meta_order)} categories")

    # Print coverage stats
    for j, mc in enumerate(meta_order):
        n_models = sum(1 for i in range(len(MODELS_ORDER)) if matrix[i, j] > 0)
        total = matrix[:, j].sum()
        print(f"    {mc.replace(chr(10), ' ')}: {n_models}/10 models, {total} findings")


def fig_severity():
    """Severity distribution as grouped bar chart across vendors."""
    # Data from paper
    severities = ['Curious', 'Notable', 'Concerning', 'Alarming']
    claude = [34, 36, 34, 12]
    codex = [3, 7, 5, 0]
    gemini = [4, 9, 6, 2]

    x = np.arange(len(severities))
    width = 0.25

    fig, ax = plt.subplots(figsize=(8, 4.5))

    bars1 = ax.bar(x - width, claude, width, label='Claude Code',
                   color=COLORS['critical'], alpha=0.85)
    bars2 = ax.bar(x, codex, width, label='Codex CLI',
                   color=COLORS['notable'], alpha=0.85)
    bars3 = ax.bar(x + width, gemini, width, label='Gemini CLI',
                   color=COLORS['curious'], alpha=0.85)

    ax.set_ylabel('Number of findings')
    ax.set_title('Severity Distribution Across Vendors')
    ax.set_xticks(x)
    ax.set_xticklabels(severities)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    ax.set_axisbelow(True)

    # Add value labels
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.annotate(f'{int(h)}', xy=(bar.get_x() + bar.get_width()/2, h),
                           xytext=(0, 3), textcoords='offset points',
                           ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    fig.savefig(OUT / 'severity.pdf', bbox_inches='tight', dpi=300)
    plt.close()
    print("  severity.pdf")


def fig_per_pass():
    """New findings per pass (bar chart showing MiniMax surge)."""
    passes = list(range(1, 11))
    new_findings = [21, 9, 14, 12, 10, 5, 20, 3, 14, 8]
    models = ['Claude\nOpus', 'Gemini\nFlash', 'Kimi\nK2.5', 'DeepSeek\nV3.2',
              'Grok\n4.1', 'Llama\nMav.', 'MiniMax\nM2.5', 'Qwen3\n235B',
              'GLM\n4.7', 'GPT-OSS\n120B']
    # Color: highlight the surge pass and the "no" votes
    colors = []
    for i, (n, p) in enumerate(zip(new_findings, passes)):
        if p == 7:
            colors.append(COLORS['alarming'])  # MiniMax surge
        elif p >= 8:
            colors.append('#90A4AE')  # voted to stop
        else:
            colors.append(COLORS['notable'])

    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.bar(range(len(passes)), new_findings, color=colors, edgecolor='white', linewidth=0.5)

    ax.set_xticks(range(len(passes)))
    ax.set_xticklabels(models, fontsize=7.5)
    ax.set_ylabel('New findings')
    ax.set_title('New Findings Per Pass — Claude Code Scourer Campaign')
    ax.grid(axis='y', alpha=0.3)
    ax.set_axisbelow(True)

    # Annotate
    for bar, n in zip(bars, new_findings):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.4,
                str(n), ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Legend for colors
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=COLORS['notable'], label='Voted to continue'),
        Patch(facecolor=COLORS['alarming'], label='MiniMax surge (+20)'),
        Patch(facecolor='#90A4AE', label='Voted to stop'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=8)

    plt.tight_layout()
    fig.savefig(OUT / 'per_pass.pdf', bbox_inches='tight', dpi=300)
    plt.close()
    print("  per_pass.pdf")


def fig_cost_per_model():
    """Cost breakdown pie/bar showing model cost distribution."""
    models = ['Kimi K2.5', 'DeepSeek R1', 'Qwen3-235B', 'GLM 4.7',
              'Grok 4.1', 'Llama Mav.', 'DeepSeek V3.2', 'MiniMax M2.5',
              'Gemini Flash', 'GPT-OSS 120B']
    costs = [0.054, 0.054, 0.053, 0.039, 0.016, 0.015, 0.012, 0.012, 0.005, 0.003]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.barh(range(len(models)), costs, color=COLORS['notable'], alpha=0.85)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models, fontsize=9)
    ax.set_xlabel('Cost (USD)')
    ax.set_title('API Cost by Model — Total: $0.263')
    ax.invert_yaxis()
    ax.grid(axis='x', alpha=0.3)
    ax.set_axisbelow(True)

    for bar, cost in zip(bars, costs):
        ax.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height()/2,
                f'${cost:.3f}', ha='left', va='center', fontsize=8)

    plt.tight_layout()
    fig.savefig(OUT / 'cost.pdf', bbox_inches='tight', dpi=300)
    plt.close()
    print("  cost.pdf")


if __name__ == '__main__':
    print("Generating figures...")
    fig_heatmap()
    fig_severity()
    fig_per_pass()
    fig_cost_per_model()
    print(f"Done. Figures in {OUT}/")
