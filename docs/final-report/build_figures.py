"""Rebuild compact report figures from immutable reviewed measurements."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent/'figures'
DATA = ROOT/'part4/results/2026-11-24-cluster'
OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':9, 'axes.spines.top':False, 'axes.spines.right':False,
                     'savefig.dpi':180})
def read(name):
    with (DATA/name).open() as f:
        return list(csv.DictReader(f))
p = read('analysis/predictions.csv')
s = read('analysis/summary.csv')
colors = ['#176B8A','#B75C28','#467845','#7A4F8A']
styles = [(d,m) for d in ('strips','blocks') for m in ('node','slot')]
def save(fig,name):
    fig.savefig(OUT/(name+'.png'),bbox_inches='tight')
    fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight')
    plt.close(fig)

fig, axes = plt.subplots(1,2,figsize=(7,2.8),constrained_layout=True)
for i,(d,m) in enumerate(styles):
    z=sorted([r for r in p if r['experiment']=='strong' and r['N']=='8192' and r['decomp']==d and r['mapping']==m],key=lambda r:int(r['P']))
    for ax,column in zip(axes,['speedup_or_weak_efficiency','strong_efficiency']):
        ax.plot([int(r['P']) for r in z],[float(r[column]) for r in z],'o-',color=colors[i],label=d+'/'+m,ms=3)
for ax,title,y in zip(axes,['Strong speed-up, N=8192','Strong efficiency, N=8192'],['Serial heat1 time / MPI time','Speed-up / P']):
    ax.set(title=title,xlabel='MPI processes P',ylabel=y,yscale='log',xticks=range(1,9))
    ax.axhline(1,color='0.55',lw=.6);ax.grid(alpha=.2);ax.legend(fontsize=7)
save(fig,'strong8192')

fig, axes = plt.subplots(2,2,figsize=(7,4.7),constrained_layout=True)
for ax,(d,m) in zip(axes.flat,styles):
    z=sorted([r for r in p if r['experiment']=='strong' and r['N']=='8192' and r['decomp']==d and r['mapping']==m],key=lambda r:int(r['P']))
    x=[int(r['P']) for r in z]
    spread=[next(q for q in s if all(q[k]==r[k] for k in ('experiment','decomp','mapping','P','N'))) for r in z]
    med=[float(q['median_seconds_per_step']) for q in spread]
    ax.errorbar(x,med,yerr=[[v-float(q['min_seconds_per_step']) for v,q in zip(med,spread)],
                           [float(q['max_seconds_per_step'])-v for v,q in zip(med,spread)]],fmt='o-',label='Measured median; min-max',color=colors[0],ms=3,capsize=2)
    ax.plot(x,[float(r['model_total_s_per_step']) for r in z],'--',label='Calibrated model',color=colors[1])
    ax.plot(x,[float(r['model_microsecond_s_per_step']) for r in z],':',label='Model with startup = 1 us',color=colors[2])
    ax.set(title=d+'/'+m,xlabel='MPI processes P',ylabel='Seconds per step',yscale='log',xticks=range(1,9))
    ax.grid(alpha=.2);ax.legend(fontsize=6.7)
save(fig,'model8192')

fig, axes = plt.subplots(1,2,figsize=(7,3),constrained_layout=True)
for i,(d,m) in enumerate(styles):
    z=sorted([r for r in p if r['experiment']=='weak' and r['decomp']==d and r['mapping']==m],key=lambda r:int(r['P']))
    axes[0].plot([int(r['P']) for r in z],[float(r['measured_s_per_step']) for r in z],'o-',color=colors[i],label=d+'/'+m,ms=3)
    axes[1].plot([int(r['P']) for r in z],[float(r['speedup_or_weak_efficiency']) for r in z],'o-',color=colors[i],label=d+'/'+m,ms=3)
for ax,title,y in zip(axes,['Weak scaling: ~1024^2 cells/rank','Weak efficiency'],['Seconds per step','T(P=1) / T(P)']):
    ax.set(title=title,xlabel='MPI processes P',ylabel=y,yscale='log',xticks=range(1,9));ax.grid(alpha=.2);ax.legend(fontsize=7)
save(fig,'weak')

fig, ax = plt.subplots(figsize=(7,2.6),constrained_layout=True)
for i,(d,m) in enumerate(styles):
    z=sorted([r for r in s if r['experiment']=='strong' and r['N']=='8192' and r['decomp']==d and r['mapping']==m],key=lambda r:int(r['P']))
    ax.plot([int(r['P']) for r in z],[100*float(r['median_communication_fraction']) for r in z],'o-',color=colors[i],label=d+'/'+m,ms=3)
ax.set(title='Communication share, N=8192: median of three runs',xlabel='MPI processes P',ylabel='max(t_comm) / max(t_total), %',ylim=(0,102),xticks=range(1,9))
ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=2)
save(fig,'communication')

fig, axes=plt.subplots(1,2,figsize=(7,2.7),constrained_layout=True)
for ax,layout in zip(axes,['strips','blocks']):
    ax.set(xlim=(0,8),ylim=(0,8),aspect='equal',title='P=4: '+layout,xlabel='x grid index',ylabel='y grid index')
    for rank in range(4):
        x,y,w,h=(0,rank*2,8,2) if layout=='strips' else ((rank%2)*4,(rank//2)*4,4,4)
        ax.add_patch(Rectangle((x,y),w,h,facecolor=colors[rank],alpha=.2,edgecolor=colors[rank],lw=1.2))
        ax.text(x+w/2,y+h/2,f'rank {rank}',ha='center',va='center')
    ax.set_xticks([0,4,8]);ax.set_yticks([0,4,8])
fig.text(.5,-.02,'Schematic ownership only; ghost layers surround each local subdomain. No diagonal halo is needed.',ha='center',fontsize=8)
save(fig,'decompositions')
print('Built five report figure pairs in',OUT)
