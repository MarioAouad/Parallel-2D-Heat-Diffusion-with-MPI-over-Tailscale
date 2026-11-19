"""Reproduce all tables and figures. Run after compiling heat_serial.cpp."""
from pathlib import Path
import csv
import math
import subprocess
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'results'
FIG = ROOT / 'figures'
TABLE = ROOT / 'tables'
for folder in [DATA, FIG, TABLE]:
    folder.mkdir(exist_ok=True)
plt.rcParams.update({'font.size': 10, 'axes.grid': True, 'grid.alpha': .25,
                     'savefig.bbox': 'tight', 'figure.figsize': (6.4, 3.7)})

def csv_write(name, rows):
    with (DATA / name).open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)

def sci(x):
    mantissa, exponent = f'{x:.5e}'.split('e')
    return rf'{mantissa}\times10^{{{int(exponent)}}}'

def save(name):
    plt.tight_layout(); plt.savefig(FIG / f'{name}.pdf'); plt.savefig(FIG / f'{name}.png', dpi=170); plt.close()

# Tasks 3.2 and 3.5: compute directly in binary64; do not algebraically
# simplify sin(x-h)-2sin(x)+sin(x+h), since cancellation is the experiment.
def difference(h):
    return (math.sin(1-h)-2*math.sin(1)+math.sin(1+h))/(h*h)

rows = []
for h in [.1, .05, .025, .0125]:
    approx = difference(h); error = abs(approx+math.sin(1))
    ratio = rows[-1]['error']/error if rows else None
    rows.append(dict(h=h, approximation=approx, error=error, ratio=ratio))
csv_write('task_3_2.csv', rows)
(TABLE/'task_3_2.tex').write_text('\n'.join(
    rf"{v['h']:.4g} & ${v['approximation']:.10f}$ & ${sci(v['error'])}$ & "
    + ('---' if v['ratio'] is None else f"{v['ratio']:.5f}")+r' \\' for v in rows))

roundrows = []
for k in range(1,11):
    h=10.**(-k); roundrows.append(dict(h=h, approximation=difference(h), error=abs(difference(h)+math.sin(1))))
csv_write('task_3_5.csv', roundrows)
(TABLE/'task_3_5.tex').write_text('\n'.join(
    rf"$10^{{-{k}}}$ & ${v['approximation']:.9f}$ & ${sci(v['error'])}$ \\" for k,v in enumerate(roundrows,1)))
hs = np.array([v['h'] for v in roundrows])
plt.loglog(hs, [v['error'] for v in roundrows], 'o-', label='Direct second difference')
plt.loglog(hs, math.sin(1)/12*hs**2, '--', label=r'Truncation prediction $|\sin(1)|h^2/12$')
plt.loglog(hs, 4*np.finfo(float).eps*math.sin(1)/hs**2, ':', label=r'Round-off scale $4\epsilon |\sin(1)|/h^2$')
plt.xlabel('Spacing h'); plt.ylabel('Absolute error'); plt.legend(fontsize=8); save('task_3_5_roundoff')

# Task 4.1: recurrence is iterated, including very fine steps needed to see
# asymptotic order at t=1 when lambda=50 (exact value is only 1.93e-22).
def euler(steps, backward=False, trajectory=False):
    dt=1.0/steps; g=1/(1+50*dt) if backward else 1-50*dt
    u=1.; values=[u]
    for _ in range(steps):
        u *= g
        if trajectory: values.append(u)
    return np.array(values) if trajectory else u

exact=math.exp(-50)
erows=[]
for M in [16000,32000,64000,128000,256000]:
    u=euler(M); error=abs(u-exact)
    erows.append(dict(steps=M, dt=1/M, solution=u, error=error,
                      order=None if not erows else math.log2(erows[-1]['error']/error)))
csv_write('task_4_1_convergence.csv',erows)
(TABLE/'task_4_1.tex').write_text('\n'.join(
    rf"{v['steps']} & ${sci(v['dt'])}$ & ${sci(v['solution'])}$ & ${sci(v['error'])}$ & "
    + ('---' if v['order'] is None else f"{v['order']:.5f}")+r' \\' for v in erows))
stability=[]
for M in [20,24,25,26,50]:
    stability.append(dict(steps=M, dt=1/M, forward_g=1-50/M,
                          forward_final=euler(M), backward_final=euler(M,True)))
csv_write('task_4_1_stability.csv',stability)
(TABLE/'task_4_1_stability.tex').write_text('\n'.join(
    rf"{v['steps']} & {v['dt']:.6f} & {v['forward_g']:.6f} & ${v['forward_final']:.5g}$ & ${sci(v['backward_final'])}$ \\" for v in stability))
fig,axes=plt.subplots(1,2,figsize=(7.1,3.4))
for M in [20,25,26,50]:
    vals=euler(M,trajectory=True)
    axes[0].plot(np.linspace(0,1,M+1),vals,'o-',ms=2,label=f'dt = 1/{M}')
    axes[1].semilogy(np.linspace(0,1,M+1),np.maximum(np.abs(vals),1e-25),'o-',ms=2,label=f'dt = 1/{M}')
axes[0].set_ylim(-2.5,2.5); axes[0].set_title('Sign oscillations (vertical axis clipped)')
tt=np.linspace(0,1,300); axes[1].semilogy(tt,np.exp(-50*tt),'k--',label='Exact')
axes[1].set_title('Absolute value reveals growth / decay')
for ax in axes: ax.set_xlabel('t'); ax.set_ylabel('u or |u|'); ax.legend(fontsize=7)
save('task_4_1_stability')
dt=np.array([v['dt'] for v in erows]); ee=np.array([v['error'] for v in erows])
plt.loglog(dt,ee,'o-',label='Computed final-time error')
plt.loglog(dt,ee[-1]*dt/dt[-1],'--',label='Slope 1 reference')
plt.xlabel('Time step'); plt.ylabel('Absolute error at t=1'); plt.legend(); save('task_4_1_order')

exe=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).parent/('heat_serial.exe' if sys.platform=='win32' else 'heat_serial')
raw=[]
def heat(N,r,T,case,steps=None,out=None):
    args=[str(exe),str(N),str(r),str(T),case]
    if steps is not None: args.append(str(steps))
    if out is not None: args.append(str(out))
    response=subprocess.check_output(args,text=True).strip()
    raw.append('COMMAND: '+' '.join(args)+'\n'+response)
    return {k:float(v) for k,v in (token.split('=') for token in response.split())}

conv=[]
for N in [16,32,64,128,256]:
    result=heat(N,.2,.05,'V')
    G=1-8*.2*math.sin(math.pi/(2*N))**2
    analytic=abs(G**int(result['steps'])-math.exp(-2*math.pi**2*.05))
    assert abs(result['err_inf']-analytic)<5e-13, (result,analytic)
    assert abs(2*result['err_l2']-result['err_inf'])<5e-13
    order=None if not conv else math.log2(conv[-1]['err_l2']/result['err_l2'])
    conv.append(dict(N=N,h=1/N,steps=int(result['steps']),dt=result['dt'],
                     err_inf=result['err_inf'],err_l2=result['err_l2'],order=order))
csv_write('task_7_2.csv',conv)
(TABLE/'task_7_2.tex').write_text('\n'.join(
    rf"{v['N']} & $1/{v['N']}$ & {v['steps']} & ${sci(v['err_inf'])}$ & ${sci(v['err_l2'])}$ & "
    + ('---' if v['order'] is None else f"{v['order']:.5f}")+r' \\' for v in conv))
hs=np.array([v['h'] for v in conv]); errors=np.array([v['err_l2'] for v in conv])
plt.loglog(hs,errors,'o-',label=r'Computed $\|e\|_{2,h}$')
plt.loglog(hs,errors[-1]*(hs/hs[-1])**2,'--',label='Slope 2 reference')
plt.xlabel('h'); plt.ylabel('Discrete L2 error at T=0.05'); plt.legend(); save('task_7_2_convergence')

# Task 6.7: all four edges hot, interior initially zero, no artificial noise.
unstable=[]
snapshots={}
for steps in [1,20,40,80,120,160,200,300]:
    out=DATA/f'unstable_{steps}.bin'
    v=heat(64,.2625,.05,'X',steps,out)
    unstable.append(dict(steps=steps,T=v['T'],minimum=v['minimum'],maximum=v['maximum']))
    snapshots[steps]=np.fromfile(out,dtype='<f8').reshape(65,65)
csv_write('task_6_7.csv',unstable)
(TABLE/'task_6_7.tex').write_text('\n'.join(
    rf"{v['steps']} & ${v['T']:.6f}$ & ${v['minimum']:.6g}$ & ${v['maximum']:.6g}$ \\" for v in unstable if v['steps'] in [1,40,80,120,160,200]))
fig,axes=plt.subplots(1,3,figsize=(7.1,2.7))
for ax,step in zip(axes,[40,120,200]):
    image=ax.imshow(snapshots[step],origin='lower',extent=[0,1,0,1],cmap='coolwarm')
    ax.set_title(f'Step {step}'); ax.set_xlabel('x'); ax.set_ylabel('y'); ax.grid(False)
    fig.colorbar(image,ax=ax,shrink=.74)
save('task_6_7_instability')
fig,axes=plt.subplots(1,2,figsize=(7.1,3.2))
for step in [40,80,120,200]:
    axes[0].plot(np.arange(65)/64,snapshots[step][8,:],label=f'Step {step}')
axes[0].set_xlabel('x at y=1/8'); axes[0].set_ylabel('Temperature'); axes[0].legend(fontsize=8)
axes[1].semilogy([v['steps'] for v in unstable],[max(abs(v['minimum']),abs(v['maximum'])) for v in unstable],'o-')
axes[1].set_xlabel('Time step number'); axes[1].set_ylabel('Maximum absolute temperature')
save('task_6_7_growth')
(DATA/'heat_raw_output.txt').write_text('\n\n'.join(raw)+'\n')
print('Roundoff data:',roundrows)
print('Euler data:',erows)
print('Heat convergence:',conv)
print('Instability:',unstable)
print('All experiments and analytic cross-checks completed.')
