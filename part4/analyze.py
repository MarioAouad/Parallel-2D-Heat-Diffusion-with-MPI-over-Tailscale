"""Offline Part 4 analysis: tables, model overlays and report answers from recorded data."""
import argparse
import bisect
import collections
import json
import math
from pathlib import Path
import statistics
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import common as C

GROUP=('experiment','host','decomp','mapping','P','N')


def groups(rows):
    result=collections.defaultdict(list)
    for row in rows:
        result[tuple(str(row[k]) for k in GROUP)].append(row)
    return result


def rate_for(baselines,host,N):
    points=sorted((int(r['N']),float(r['median_seconds_per_interior_node'])) for r in baselines if r['host']==host)
    C.require(points,'No measured compute rate for '+host)
    if N <= points[0][0]:return points[0][1]
    if N >= points[-1][0]:return points[-1][1]
    i=bisect.bisect_left([n for n,_ in points],N)
    a,x=points[i-1];b,y=points[i]
    weight=(math.log(N)-math.log(a))/(math.log(b)-math.log(a))
    return x+(y-x)*weight


def derive(folder):
    meta=json.loads((folder/'metadata.json').read_text())
    rows=C.read_csv(folder/'measurements.csv')
    summaries=[]
    for key,selected in sorted(groups(rows).items()):
        row=dict(zip(GROUP,key));row.update(reps=len(selected),nodes=int(selected[0]['nodes']),
                                           cells_per_rank=float(selected[0]['cells_per_rank']))
        for field in ('seconds_per_step','seconds_per_grid_node','seconds_per_interior_node','communication_fraction'):
            values=[float(r[field]) for r in selected]
            for label,fn in [('median',statistics.median),('min',min),('max',max)]:
                row[label+'_'+field]=fn(values)
        summaries.append(row)
    calibration=C.read_csv(folder/'calibration.csv')
    links={key:C.fit_link([r for r in calibration if r['link']==key],meta['parameters']['calibration_max_bytes'])
           for key in sorted({r['link'] for r in calibration})}
    baselines=[r for r in summaries if r['experiment']=='baseline']
    state=json.loads((folder/'state.json').read_text())['completed']
    predicted=[]
    for row in summaries:
        if row['experiment']=='baseline':continue
        P,N=int(row['P']),int(row['N'])
        hosts=state[f"placement:{row['mapping']}:{P}"]['rank_hosts']
        py,px=C.dims(P) if row['decomp']=='blocks' else (P,1)
        rates={h['host']:rate_for(baselines,h['host'],N) for h in meta['hosts']}
        details=C.predict(dict(row,Py=py,Px=px),hosts,rates,links)
        micro=C.predict(dict(row,Py=py,Px=px),hosts,rates,links,latency_override=1e-6)
        if row['experiment']=='strong':
            T1=next(r['median_seconds_per_step'] for r in baselines if r['host']==meta['reference_host'] and int(r['N'])==N)
        else:
            T1=next(r['median_seconds_per_step'] for r in summaries if r['experiment']=='weak' and
                    r['decomp']==row['decomp'] and r['mapping']==row['mapping'] and int(r['P'])==1)
        T=float(row['median_seconds_per_step'])
        predicted.append(dict(experiment=row['experiment'],decomp=row['decomp'],mapping=row['mapping'],P=P,N=N,
                              serial_or_weak_reference_s=T1,measured_s_per_step=T,speedup_or_weak_efficiency=T1/T,
                              strong_efficiency=T1/T/P if row['experiment']=='strong' else '',
                              **details,model_microsecond_s_per_step=micro['model_total_s_per_step'],
                              measured_over_model=T/details['model_total_s_per_step']))
    return meta,rows,summaries,links,predicted


def plot_results(out,summaries,predictions,synthetic=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    def save(fig,name):
        if synthetic:fig.suptitle('SYNTHETIC TEST DATA - NOT MEASURED',color='crimson',fontsize=11)
        fig.savefig(out/(name+'.png'),dpi=160);fig.savefig(out/(name+'.pdf'));plt.close(fig)
    colors=plt.cm.tab10.colors
    fig,ax=plt.subplots(figsize=(7.5,4.5),constrained_layout=True)
    for i,host in enumerate(sorted({r['host'] for r in summaries if r['experiment']=='baseline'})):
        selected=sorted([r for r in summaries if r['experiment']=='baseline' and r['host']==host],key=lambda r:int(r['N']))
        ax.errorbar([int(r['N']) for r in selected],[r['median_seconds_per_step'] for r in selected],
                    yerr=[[r['median_seconds_per_step']-r['min_seconds_per_step'] for r in selected],
                          [r['max_seconds_per_step']-r['median_seconds_per_step'] for r in selected]],
                    marker='o',capsize=3,label=host,color=colors[i])
    ax.set(xlabel='N (intervals)',ylabel='Serial seconds per step',xscale='log',yscale='log',title='Per-VM serial baseline: median and min-max')
    ax.legend();save(fig,'serial_baselines')
    for name,ylabel,column in [('strong_time','Seconds per step','measured_s_per_step'),
                               ('strong_speedup','Speed-up versus serial heat1','speedup_or_weak_efficiency'),
                               ('strong_efficiency','Speed-up / P','strong_efficiency')]:
        fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
        for iy,decomp in enumerate(('strips','blocks')):
            for ix,mapping in enumerate(('node','slot')):
                ax=axes[iy,ix]
                subset=[r for r in predictions if r['experiment']=='strong' and r['decomp']==decomp and r['mapping']==mapping]
                for i,N in enumerate(sorted({r['N'] for r in subset})):
                    sel=sorted([r for r in subset if r['N']==N],key=lambda r:r['P'])
                    x=[r['P'] for r in sel]
                    values=[float(r[column]) for r in sel]
                    if name=='strong_time':
                        spread=[next(r for r in summaries if r['experiment']=='strong' and r['decomp']==decomp and r['mapping']==mapping and int(r['P'])==t['P'] and int(r['N'])==N) for t in sel]
                        ax.errorbar(x,values,yerr=[[t['median_seconds_per_step']-t['min_seconds_per_step'] for t in spread],
                            [t['max_seconds_per_step']-t['median_seconds_per_step'] for t in spread]],fmt='o-',capsize=2,color=colors[i],label=f'N={N} measured')
                    else:
                        ax.plot(x,values,'o-',color=colors[i],label=f'N={N} measured')
                    model=[r['model_total_s_per_step'] if name=='strong_time' else r['serial_or_weak_reference_s']/r['model_total_s_per_step']/(r['P'] if name=='strong_efficiency' else 1) for r in sel]
                    ax.plot(x,model,'--',color=colors[i],label=f'N={N} model')
                    if name=='strong_time':
                        ax.plot(x,[r['model_microsecond_s_per_step'] for r in sel],':',color=colors[i],label=f'N={N}, latency=1us')
                ax.set(title=f'{decomp}, map-by {mapping}',xlabel='MPI processes P',ylabel=ylabel,yscale='log')
                ax.grid(alpha=.2);ax.legend(fontsize=7)
        save(fig,name)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),constrained_layout=True)
    for i,(decomp,mapping) in enumerate((d,m) for d in ('strips','blocks') for m in ('node','slot')):
        sel=sorted([r for r in predictions if r['experiment']=='weak' and r['decomp']==decomp and r['mapping']==mapping],key=lambda r:r['P'])
        spread=[next(r for r in summaries if r['experiment']=='weak' and r['decomp']==decomp and r['mapping']==mapping and int(r['P'])==t['P']) for t in sel]
        axes[0].errorbar([r['P'] for r in sel],[r['measured_s_per_step'] for r in sel],
            yerr=[[r['median_seconds_per_step']-r['min_seconds_per_step'] for r in spread],
                  [r['max_seconds_per_step']-r['median_seconds_per_step'] for r in spread]],fmt='o-',capsize=2,color=colors[i],label=f'{decomp}/{mapping}')
        axes[0].plot([r['P'] for r in sel],[r['model_total_s_per_step'] for r in sel],'--',color=colors[i])
        axes[1].plot([r['P'] for r in sel],[r['speedup_or_weak_efficiency'] for r in sel],'o-',color=colors[i],label=f'{decomp}/{mapping}')
    axes[0].set(xlabel='P',ylabel='Seconds per step',yscale='log',title='Weak scaling (dashed = model)')
    axes[1].set(xlabel='P',ylabel='T(P=1) / T(P)',title='Weak scaling efficiency')
    for ax in axes:ax.legend(fontsize=8);ax.grid(alpha=.2)
    save(fig,'weak_scaling')
    fig,axes=plt.subplots(2,2,figsize=(11,7),constrained_layout=True)
    for iy,decomp in enumerate(('strips','blocks')):
        for ix,mapping in enumerate(('node','slot')):
            ax=axes[iy,ix]
            subset=[r for r in summaries if r['experiment']=='strong' and r['decomp']==decomp and r['mapping']==mapping]
            for N in sorted({int(r['N']) for r in subset}):
                sel=sorted([r for r in subset if int(r['N'])==N],key=lambda r:int(r['P']))
                ax.errorbar([int(r['P']) for r in sel],[r['median_communication_fraction'] for r in sel],
                            yerr=[[r['median_communication_fraction']-r['min_communication_fraction'] for r in sel],
                                  [r['max_communication_fraction']-r['median_communication_fraction'] for r in sel]],capsize=2,label=f'N={N}')
            ax.set(title=f'{decomp}/{mapping}',xlabel='P',ylabel='Halo fraction (median and min-max)',ylim=(0,1.01));ax.legend(fontsize=8)
    save(fig,'communication_share')


def report(meta,summaries,links,predictions):
    strong=[r for r in predictions if r['experiment']=='strong']
    crossing=[r for r in strong if r['P']>1 and next(s['nodes'] for s in summaries if all(str(s[k])==str(r[k]) for k in ('experiment','decomp','mapping','P','N')))>1]
    actual=sorted({r['N'] for r in crossing if r['speedup_or_weak_efficiency']>1})
    model=sorted({r['N'] for r in crossing if r['serial_or_weak_reference_s']/r['model_total_s_per_step']>1})
    lines=['# Part 4 measured analysis','',f"Revision: `{meta['revision']}`. Profile: **{meta['parameters']['profile']}**. Mode: **{meta['mode']}**.",
           f"Conditions supplied by operator: {meta['notes']}",
           f"All session notes: {meta.get('session_notes',[meta['notes']])}",
           f"Failed invocation attempts retained in raw history: {meta.get('failed_attempts_retained',0)}.",
           f"Network snapshot counters (mentions, not route-continuity proof): {meta.get('network_snapshot_counts',{})}",'',
           'This file summarizes recorded data; it is not the final ten-page course report.',
           '', '## Does spreading work across VMs pay off?', '',
           f'Measured cross-VM speed-up over serial {meta["reference_host"]} occurs at tested N: {actual or "none"}.',
           f'The busiest-rank model predicts cross-VM speed-up at tested N: {model or "none"}.',
           'These are tested sizes, not an interpolated crossover or proof about untested N.', '',
           '## Model and discrepancies', '',
           'Compute uses each guest\'s measured serial seconds per interior node, log-interpolated in global N. '
           'Strips use owned rows and N-1 columns; blocks use the actual uneven Cartesian split. '
           'Each neighbor contributes ts + doubles*tw; prediction is max over ranks of compute + summed neighbor exchanges. '
           'ts is the median half-RTT at 8..64 bytes; tw is eight times the anchored seconds/byte slope at the largest three sizes. '
           'All six same/cross-VM calibrations use the same TCP/self transport as the solvers. '
           'Half-RTT assumes directional symmetry. Pairwise estimates are not simultaneous contention measurements.', '',
           'The model omits blocking-phase critical paths, cache changes, datatype packing, shared memory-bandwidth contention '
           'and interference on home links. Check raw network observations before attributing a mismatch to DERP or Wi-Fi; '
           'those observations do not prove route continuity. Per-host compute rates represent isolated serial execution, '
           'not simultaneous execution on every guest core.', '',
           '## A one-microsecond interconnect', '',
           'predictions.csv and the dotted strong-time curves replace every link startup with 1 microsecond, retaining '
           'measured bandwidth and compute rates. This isolates latency: a real cluster also changes bandwidth, '
           'hardware and contention, so it is not a forecast of a particular supercomputer.', '',
           '## Advice for Tailscale', '',
           'Select P/layout/placement from the measured configuration at the N you need, rather than assuming more '
           'processes are faster. A tested crossing is listed above. Keep power/load/allocation/transport fixed, '
           'prefer stable routes and retain spread, including slow results. Do not compare different N as a speed-up.', '',
           '## Interpretation and scope', '',
           'Strong speed-up uses the serial baseline on heat1 at the same N; therefore MPI P=1 need not have speed-up exactly 1. '
           'Efficiency divides that speed-up by P. Weak efficiency uses the same layout/placement\'s P=1 weak run. '
           'Weak N=round(base*sqrt(P))+1 fixes interior work approximately; the exact cells per rank and min/max owned '
           'cells are recorded. Raw per-run communication fraction is max-rank t_comm/max-rank t_total: '
           'the maxima can occur on different ranks, and t_comp+t_comm need not equal t_total.', '',
           'summary.csv includes median and min-max spread for every configuration. measurements.csv preserves every '
           'repetition and per-step/per-grid-node/per-interior-node quantities. predictions.csv preserves model error '
           'for each strong/weak group. Original raw output and placement probes are retained. '
           'A smoke/synthetic fixture is never official performance evidence.', '',
           'The final report must still add actual team contributions, hardware/network discussion, selected curves, '
           'and explanation of the specific discrepancies observed. The live demo and full AI-history hand-in remain separate.']
    lines+=['','## Best tested parallel configuration at each strong-scaling N','',
            '| N | Layout | Placement | P | Median seconds/step | Speed-up vs serial heat1 |',
            '| ---: | --- | --- | ---: | ---: | ---: |']
    for N in sorted({r['N'] for r in strong}):
        best=min((r for r in strong if r['N']==N),key=lambda r:r['measured_s_per_step'])
        lines.append(f"| {N} | {best['decomp']} | {best['mapping']} | {best['P']} | {best['measured_s_per_step']:.6g} | {best['speedup_or_weak_efficiency']:.6g} |")
    lines+=['','If the best tested speed-up is at most 1, serial heat1 was faster than every tested parallel configuration at that N.']
    return '\n'.join(lines)+'\n'


def analyze(folder,out,replace=False):
    folder,out=Path(folder),Path(out)
    if not replace:out.mkdir(parents=True,exist_ok=False)
    else:out.mkdir(parents=True,exist_ok=True)
    meta,rows,summaries,links,predictions=derive(folder)
    C.write_csv(out/'summary.csv',summaries);C.write_csv(out/'predictions.csv',predictions)
    C.write_json(out/'calibration_fit.json',links)
    (out/'REPORT.md').write_text(report(meta,summaries,links,predictions),encoding='utf-8')
    plot_results(out,summaries,predictions,synthetic=meta['mode']!='cluster')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True,help='NEW analysis folder; never overwrite reviewed evidence')
    args=parser.parse_args();analyze(args.data,args.out)


if __name__=='__main__':main()
