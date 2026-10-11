"""Export research figures from saved audited data; requires matplotlib."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'docs/assets/figures'
OUT.mkdir(parents=True, exist_ok=True)
data = json.loads((ROOT / 'docs/assets/data.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'svg.fonttype': 'none'})
names = {'gpt-5.4': 'GPT', 'qwen3.8-max': 'Qwen', 'deepseek-v4-pro': 'DeepSeek', 'kimi-k2.5': 'Kimi'}

def save(fig, name):
    fig.savefig(OUT / (name + '.png'), dpi=220, bbox_inches='tight')
    fig.savefig(OUT / (name + '.svg'), bbox_inches='tight')
    plt.close(fig)

matrix = data['protocol']['matrix']
cells = [[next(r for r in matrix if r['producer'] == p and r['reviewer'] == v) for v in data['reviewers']] for p in data['producers']]
fig, ax = plt.subplots(figsize=(6.4, 4.2), layout='constrained')
im = ax.imshow([[r['false_endorsement'] for r in row] for row in cells], cmap='YlOrBr', vmin=0, vmax=1)
ax.set_xticks(range(3), [names[v] for v in data['reviewers']])
ax.set_yticks(range(4), [names[p] for p in data['producers']])
ax.set(xlabel='Reviewer interface', ylabel='Producer interface', title='False endorsement of incorrect answers')
for i, row in enumerate(cells):
    for j, r in enumerate(row):
        ax.text(j, i, f"{r['false_accepted']}/{r['bad']}\n{r['false_endorsement']:.1%}", ha='center', va='center')
fig.colorbar(im, ax=ax, format=PercentFormatter(1), label='Incorrect and accepted / incorrect')
save(fig, 'pair-false-endorsement')

routes = data['protocol']['routes']
points = [('global_calibration', 'Global reviewer', (8, 6)), ('producer_calibration', 'Producer-aware route', (8, -25)), ('blind_global_agreement', 'Blind solve agreement', (8, -16)), ('all_three_agree', 'Three reviewers agree', (8, -16)), ('fixed_qwen3.8-max', 'Fixed Qwen', (-40, 40))]
fig, ax = plt.subplots(figsize=(7.2, 4.4), layout='constrained')
for key, label, offset in points:
    row = routes[key]
    ax.scatter(row['coverage'], row['conditional_risk'], s=70, marker='s' if key == 'all_three_agree' else 'o', label=label)
    ax.annotate(label + f"\n{row['false_accepted']}/{row['accepted']} errors", (row['coverage'], row['conditional_risk']), xytext=offset, textcoords='offset points', fontsize=9)
ax.set(xlabel='Acceptance coverage (accepted / 720 test answers)', ylabel='Conditional error (incorrect / accepted)', xlim=(.1, .95), ylim=(0, .26), title='Quality and coverage on 90 held-out seeded scenarios')
ax.xaxis.set_major_formatter(PercentFormatter(1))
ax.yaxis.set_major_formatter(PercentFormatter(1))
ax.grid(alpha=.2)
fig.text(.13, -.045, 'Observed points. Three-reviewer agreement costs 3 reviews; other routes cost 1.\n51 parameter configurations overall; calibration/test parameters overlap. No deployment certificate.', fontsize=9)
save(fig, 'risk-coverage')

if data['rtl']['summary']['complete']:
    audit = data['rtl']['audit']
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.9), sharey=True, layout='constrained')
    methods = ['direct_patch', 'same_family_trace', 'cross_family_trace']
    for ax, (task, rows) in zip(axes, audit['tasks'].items()):
        values = [rows[m]['correct_adoption'] for m in methods]
        ax.bar(range(3), values, color=['#8798a4', '#067f77', '#587da0'])
        ax.set(title={'dma_write': 'DMA writer', 'udp_rx_guard': 'UDP receive guard', 'icache_ctrl': 'Instruction cache'}[task], ylim=(0, 26))
        ax.set_xticks(range(3), ['One call', 'Same family', 'Cross family'], rotation=25, ha='right')
        for i, value in enumerate(values):
            ax.text(i, value + .6, f'{value}/24', ha='center')
    axes[0].set_ylabel('Development accepted and independently correct')
    fig.suptitle('18 qualified injected wrapper faults, four producer interfaces')
    fig.text(.06, -.045, 'Same/cross routes share initial repairs and have a maximum of 3 model calls.\nThree fixed contracts; fault count is not independent project count. CPU simulation only.', fontsize=9)
    save(fig, 'rtl-correct-adoption')
print(json.dumps({'figures': [p.name for p in OUT.glob('*.png')]}))
