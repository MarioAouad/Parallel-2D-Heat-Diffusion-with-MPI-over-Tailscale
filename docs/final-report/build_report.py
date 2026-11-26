"""Build the ten-page CPU/MPI report, then append three original vector plots.

Requires reportlab and pypdf. Run build_figures.py first (NumPy/Matplotlib).
All numerical values come from reviewed CSVs; no VM experiments are launched.
"""
import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, Preformatted
from pypdf import PdfReader, PdfWriter

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DATA=ROOT/'part4/results/2026-11-24-cluster'
TMP=ROOT/'output/pdf'
TMP.mkdir(parents=True,exist_ok=True)
def read(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))
summary=read(DATA/'analysis/summary.csv')
pred=read(DATA/'analysis/predictions.csv')
comparison=read(ROOT/'part4/layout-comparison.csv')
convergence=read(ROOT/'part1/results/2026-11-19-ubuntu/convergence.csv')
oldlinks=read(ROOT/'part0/results/analysis/summary.csv')
links=json.loads((DATA/'analysis/calibration_fit.json').read_text())
review=json.loads((ROOT/'part4/review.json').read_text())
meta=json.loads((DATA/'metadata.json').read_text())

for regular,bold in [(Path('C:/Windows/Fonts/arial.ttf'),Path('C:/Windows/Fonts/arialbd.ttf')),
                     (Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))]:
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont('Report',str(regular)))
        pdfmetrics.registerFont(TTFont('ReportBold',str(bold)))
        pdfmetrics.registerFontFamily('Report',normal='Report',bold='ReportBold',italic='Report',boldItalic='ReportBold')
        break
else:
    raise RuntimeError('Install Arial or DejaVu Sans for reproducible readable report fonts')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyReport',fontName='Report',fontSize=9.4,leading=13,spaceAfter=7))
styles.add(ParagraphStyle(name='SmallReport',fontName='Report',fontSize=8,leading=10.5,spaceAfter=5))
styles.add(ParagraphStyle(name='TitleReport',fontName='ReportBold',fontSize=22,leading=26,spaceAfter=13,textColor=colors.HexColor('#174B62')))
styles.add(ParagraphStyle(name='HeadingReport',fontName='ReportBold',fontSize=15,leading=19,spaceAfter=10,textColor=colors.HexColor('#174B62')))
styles.add(ParagraphStyle(name='SubReport',fontName='ReportBold',fontSize=11,leading=14,spaceBefore=5,spaceAfter=5))
story=[]
def para(text,style='BodyReport'):
    story.append(Paragraph(text,styles[style]))
def heading(text):para(text,'HeadingReport')
def sub(text):para(text,'SubReport')
def page(title):
    if story:story.append(PageBreak())
    heading(title)
def table(header,data,widths=None,size=8.2):
    items=[[Paragraph(escape(str(value)),ParagraphStyle(name='cell',fontName='ReportBold' if i==0 else 'Report',fontSize=size,leading=size+2))
            for value in row] for i,row in enumerate([header]+data)]
    t=Table(items,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EDF2F5')),
                          ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),5),
                          ('TOPPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#8A9AA5')),
                          ('LINEBELOW',(0,-1),(-1,-1),.4,colors.HexColor('#BCC6CD'))]))
    story.extend([t,Spacer(1,8)])
def picture(path,width=6.9,height=None):
    image=Image(str(path))
    w=width*inch
    h=image.imageHeight/image.imageWidth*w
    if height and h>height*inch:
        w*=height*inch/h
        h=height*inch
    story.append(Image(str(path),width=w,height=h))
    story.append(Spacer(1,5))
def code(text):
    story.append(Preformatted(text,ParagraphStyle(name='code',fontName='Courier',fontSize=7.4,leading=10,spaceAfter=9)))
def strong(d,m,P,N):
    return next(r for r in pred if r['experiment']=='strong' and r['decomp']==d and r['mapping']==m and int(r['P'])==P and int(r['N'])==N)

page('1. Parallel heat diffusion over Tailscale')
para('CPU / MPI project report','TitleReport')
para('<b>Mario Aouad, Mohamad Farchoukh and Bassem Haddad</b><br/>24 November 2026')
para('We implemented and verified serial, strip and two-dimensional block solvers for the heat equation, then measured them on three Ubuntu VMs connected through home networks and Tailscale. Optional GPU/CUDA work was deliberately omitted.')
sub('Main result')
para('Filling the four slots of heat1 gave the best tested strong-scaling results: speed-ups of <b>2.68, 2.92 and 2.86</b> at N=512, 2048 and 8192. No tested configuration spanning multiple VMs beat serial heat1. This is an informative slow-network result, not a failure of parallel numerical correctness.')
table(['Guest','Host CPU model','Guest vCPUs / slots','Guest RAM'],[
 ['heat1','Intel Core i9-14900HX','4 / 4','4096 MB configured'],
 ['heat2','Intel Core i7-1255U','2 / 2','4096 MB configured'],
 ['heat3','Intel Core i7-1255U','2 / 2','4096 MB configured']],widths=[49,205,100,140])
para('Each guest used Ubuntu 24.04.5 LTS, Open MPI 4.1.6, user mpi, the same absolute repository path, NAT networking and Tailscale inside the guest. Operators reported all laptops on AC, heavy applications closed and Wi-Fi on all three hosts. Guest CPU counts and slot limits were checked before execution; the eight-rank runs used eight real allocated guest vCPUs.')
para('The network showed both direct and DERP paths. Page 5 gives the observations for each pair. The model uses each guest’s measured serial compute rate.')
sub('Numerical problem and interface')
para('We solve u_t = u_xx + u_yy on [0,1]^2 with alpha=1 and h=1/N. Case 1 has four hot edges u=1; Case 2 has hot top/bottom edges including corners, and cold left/right edges. Interior nodes initially have u=0. Test V uses sin(pi x)sin(pi y) with zero boundaries.')
code('u_next(i,j) = u_old(i,j) + r * (left + right + down + up - 4*centre)\nr = dt/h^2; 0 < r <= 1/4;  storage index = j*(N+1) + i')
para('The solvers use contiguous double arrays, a fixed arithmetic order and two time levels swapped every step. Only interior nodes are updated; fixed boundaries exist in both buffers. With --T, the number of steps is rounded up and dt adjusted to reach T without exceeding the requested r. Ordinary unstable requests are rejected.')
para('The ./heat launcher selects serial, strips or blocks with --decomp. Launch the MPI layouts with mpirun. Each solver accepts --case, --N, --r and either --steps or --T. The summary is machine-readable. With --out, the program writes the full field in row-major little-endian doubles.')

page('2. Numerical verification and stability')
para('Test V has exact solution sin(pi x)sin(pi y) exp(-2 pi^2 T). The Ubuntu convergence study uses T=0.05 and r=0.2. The discrete L2 norm is h sqrt(sum(e^2)); the maximum norm is max(abs(e)).')
table(['N','h = 1/N','Steps','Maximum error','Discrete L2 error','Order'],[
 [r['N'],r['h'],r['steps'],f"{float(r['err_inf']):.7g}",f"{float(r['err_l2']):.7g}",f"{float(r['order']):.5f}" if r['order'] else '-'] for r in convergence],widths=[40,87,58,116,122,71])
picture(ROOT/'part1/results/2026-11-19-ubuntu/convergence.png',width=5.8,height=3.0)
para('Halving h reduces the errors by approximately four: observed orders approach two. Forward Euler is first order in time; fixed r implies dt=O(h^2), giving overall O(h^2) along this refinement path. An independent discrete sine-mode amplification calculation agrees with both recorded norms to the documented tolerance.','SmallReport')
sub('Deliberately crossing the stability limit')
picture(ROOT/'part1/results/2026-11-19-ubuntu/instability.png',width=6.8,height=2.1)
para('At N=64, r=0.2625 is 5% above 1/4. Overshoot appears by step 120; by step 200 the extrema are about -303.125 and 302.307. The intentionally isolated demonstration flag does not disable the ordinary stability guard. The standard limit follows from the Fourier amplification factor, or from nonnegative stencil weights summing to one.','SmallReport')

page('3. Decompositions and exact parallel correctness')
picture(HERE/'figures/decompositions.png',width=6.8,height=2.65)
para('<b>Strips.</b> The N-1 interior rows are divided contiguously; the first (N-1) mod P ranks receive one extra row. Each rank stores its owned rows plus two ghost rows, of width N+1. Two MPI_Sendrecv phases exchange full contiguous rows. MPI_PROC_NULL handles the exterior neighbors uniformly.')
para('<b>Blocks.</b> MPI_Dims_create chooses Py by Px; MPI_Cart_create builds a non-periodic communicator and MPI_Cart_shift identifies neighbors. Rows and columns are independently split with the same remainder rule. Row exchanges are contiguous; columns use MPI_Type_vector without handwritten packing. Rank0 reconstructs output using subarray datatypes.')
para('<b>Why Sendrecv?</b> A send-first blocking ring can wait forever once eager buffering is unavailable for a large message: all ranks can wait for matching receives that have not been posted. Sendrecv combines the paired send/receive and avoids that ordering deadlock. Matching peers, tags and communicators still have to be correct.')
para('<b>Why no corner halos?</b> The five-point stencil reads only axis neighbors, never diagonals. Corner ghost values cannot affect an owned update. A nine-point Laplacian, mixed derivative or 3x3 filter would need diagonal values, requiring extra exchanges or staged forwarding.')
table(['Study','Cases / process counts','Exact comparisons','Retained evidence'],[
 ['Strips, 21 Nov','1, 2, V; P=1,2,3,4','84 / 84','109 field files; 86 byte comparisons incl. figures'],
 ['Blocks, 21 Nov','1, 2, V; P=1,2,3,4,6,8','108 / 108','130 field files; 110 byte comparisons incl. figures']],widths=[95,140,105,154])
para('Grids include N-1 not divisible by the decomposition dimensions. The archived Case2/N8 one-step halo dumps also verify neighbors and uneven ownership. Parallel fields compare bit-for-bit with serial; independent CaseV recomputation uses a small documented cross-library tolerance, distinct from the exact serial/MPI byte checks.')
picture(ROOT/'part3/results/2026-11-21-retained-cluster/cases.png',width=5.6,height=2.25)
para('Recorded Case1/2 serial and blocks heat maps. Their retained original fields match exactly across three guests. These are existing numerical run records; the course also requires the team to present a live demonstration.','SmallReport')

page('4. Measurement protocol and single-guest baselines')
para('The full campaign uses <b>20 fixed steps, r=0.24, Case1, no field output</b> in the timed experiments, with three independent invocations per configuration. The assignment gives 500 steps as an example; fixed comparability, repetition and loop-only timers are enforced. dt and final physical time vary with N; speed-up compares the same N, not different physical integration times.')
table(['Experiment','Configurations','Repetitions','Heat invocations'],[
 ['Serial: 3 guests x 5 N','15','3','45'],['Strong: 2 layouts x 2 maps x 8 P x 3 N','96','3','288'],
 ['Weak: 2 layouts x 2 maps x 8 P','32','3','96'],['Total','143','3','429']],widths=[285,72,65,72])
para('Preflight checks sources, revision, executable hashes, MPI version, CPU counts and idle solver processes. Sixteen probes record actual rank placement. --map-by node spreads round-robin; --map-by slot fills heat1 (four ranks), then heat2, then heat3. All runs bind cores and forbid oversubscription. MPI transport is ob1 with tcp,self and tailscale0 for control and data interfaces.')
picture(DATA/'analysis/serial_baselines.png',width=6.4,height=3.55)
table(['N','heat1 seconds/step','heat2 seconds/step','heat3 seconds/step'],[
 [str(N)]+[f"{float(next(r['median_seconds_per_step'] for r in summary if r['experiment']=='baseline' and r['host']==h and int(r['N'])==N)):.7g}" for h in ['heat1','heat2','heat3']] for N in [512,1024,2048,4096,8192]],widths=[55,146,146,147])
para('Medians and min-max spread are retained for every configuration. Baseline CSVs also give seconds per full-grid node and per interior node per step. The model uses interior work and each guest\'s measured rate, interpolated in log(N). Isolated serial rates do not measure memory contention among simultaneous ranks.','SmallReport')

page('5. Communication calibration and time-per-step model')
para('Part0 collected six complete 8-byte to 16-MiB sweeps. Its same-guest cases used shared memory. For the Part4 forced-TCP solver, we reused the unchanged ping-pong program to collect <b>18 new size-relevant sweeps</b>: three per same-guest/cross-guest pair, 8..131072 bytes, three timed exchanges per size plus warm-up. The largest halo is 65544 bytes, within this range.')
old_by={r['label']:r for r in oldlinks}
data=[]
for label,key in [('heat1-local','heat1|heat1'),('heat2-local','heat2|heat2'),('heat3-local','heat3|heat3'),('heat1-heat2','heat1|heat2'),('heat1-heat3','heat1|heat3'),('heat2-heat3','heat2|heat3')]:
    o=old_by[label];n=links[key]
    data.append([label,f"{float(o['model_latency_us']):.3f}",f"{float(o['model_bandwidth_MiB_s']):.4g}",f"{n['latency_s']*1e6:.3f}",f"{1/n['seconds_per_byte']/2**20:.4g}"])
table(['Pair','Part0 ts, us','Part0 MiB/s','Part4 ts, us','Part4 MiB/s'],data,widths=[104,98,98,98,96])
para('<b>Part 0 route probes.</b> Heat1–heat2 was direct before and after. Heat1–heat3 switched from DERP to direct in the pre-run probe and was direct afterward. Heat2–heat3 showed DERP before and direct afterward. These probes leave the route during each sweep unknown.','SmallReport')
para('Bandwidth is the reciprocal fitted seconds per byte, converted to MiB/s. The current cross-guest startup estimates are about 9.98, 175.82 and 85.21 ms. The local estimates differ because Part 0 used shared memory and Part 4 forced TCP.','SmallReport')
sub('Estimator and units')
para('For each size, take the median half-RTT across three sweeps. The startup ts is the median at 8, 16, 32 and 64 bytes. Fit the slope b=sum(m*(t(m)-ts))/sum(m^2) over the three largest sizes in seconds per byte. For doubles, tw=8b. All six slopes are positive. Half-RTT assumes roughly symmetric directions.')
code('compute_q = owned_interior_cells_q * c_guest(q)(N)\nexchange_q = sum_over_neighbors [ ts_link + doubles_qj * tw_link ]\npredicted_step_time = max_q (compute_q + exchange_q)')
para('Strips send N+1 doubles to each existing neighbor. Blocks send their owned column count along a row boundary and owned row count along a column boundary. Exact uneven ownership and the observed rank-to-guest map determine each cost. The boundary ranks have fewer neighbors. This is the Task 8.2 model extended to heterogeneous guests and real placement.')
sub('What the model omits')
para('The sum is a simple busiest-rank approximation. It omits blocking-phase critical paths, simultaneous link contention, datatype handling, cache changes, shared guest bandwidth and scheduling. Pairwise sequential ping-pong calibration is not simultaneous multi-rank communication. Route snapshots cannot identify the path or cause of each slow timed invocation.')

page('6. Strong scaling: placement dominates the result')
picture(HERE/'figures/strong8192.png',width=6.9,height=2.85)
para('Speed-up S(P)=median serial heat1 time / median parallel time; efficiency E(P)=S(P)/P. The graph uses log vertical scales so severe cross-guest slowdowns remain visible. Complete N=512/2048/8192 time, speed-up and efficiency curves with model overlays appear in Appendices A-C.')
table(['N','Best layout / map','P / guests','Seconds per step','Speed-up','Efficiency'],[
 [r['N'],r['decomp']+'/slot','4 / 1',f"{float(r['measured_s_per_step']):.7g}",f"{float(r['speedup_or_weak_efficiency']):.3f}",f"{float(r['strong_efficiency'])*100:.1f}%"] for r in review['best_strong']],widths=[48,138,64,105,69,70])
para('The best tested P=4 configurations all stay on heat1. Filling local cores reduces compute time without crossing the slow inter-guest network. This is shared-host MPI parallelism, not a three-machine speed-up. At P=5, slot placement starts using heat2; at P=7 it starts using heat3. Round-robin placement uses two guests from P=2 and all three from P=3.')
table(['N','P=8 strips/node','P=8 blocks/node','P=8 strips/slot','P=8 blocks/slot'],[
 [str(N)]+[f"{float(strong(d,m,8,N)['measured_s_per_step']):.6g}" for d,m in [('strips','node'),('blocks','node'),('strips','slot'),('blocks','slot')]] for N in [512,2048,8192]],widths=[45,112,112,112,113])
para('Values above are median seconds per step; all P=8 configurations span three guests. Across all 66 strong-scaling configurations using multiple guests, none beats serial heat1. The calibrated model also predicts no tested cross-guest crossover. This gives no crossover within the tested range; it does not prove that no larger problem could ever benefit.')
para('The same process count can have different rank-neighbor placement and therefore different cross-guest edges. At P=8, both policies use all slots but rank numbering still changes which adjacent subdomains communicate between guests. More ranks do not imply a monotonic performance improvement.')

page('7. Weak scaling, communication and variability')
picture(HERE/'figures/weak.png',width=6.9,height=3.0)
para('Weak scaling uses N=round(1024*sqrt(P))+1, keeping average interior work near 1024^2 cells/rank. Exact mean/min/max ownership, including uneven integer splits, is stored for each run. Ideal time is constant; the measured cross-guest curves rise sharply. Weak efficiency uses the same layout/placement\'s P=1 weak time divided by its P time, not a different serial grid.')
picture(HERE/'figures/communication.png',width=6.9,height=2.55)
para('Each run records max-rank t_comm / max-rank t_total. Exchange time includes waiting for slower peers. The independently reduced maxima may come from different ranks, so t_comp+t_comm need not equal t_total. The values are not isolated Internet transfer times.')
para('The interrupted P=6/N8192 strips invocation spent about 99.6% of its loop time in exchange/waiting. Its exit0 warning output was retained but not selected as a completed measurement. The network diagnosis later observed changing direct/DERP paths and unused swap; it cannot establish historical route continuity or rule out every transient load effect.')
para('The largest observed repetition spread is max/min=15.80 for strips/slot/P5/N512 (0.06675..1.05495 seconds/step; median0.13084). All three timings remain in the tables. Medians reduce outlier sensitivity but three repeats do not characterize a stationary latency distribution or justify tight confidence intervals.')

page('8. Strips versus blocks: prediction, then measurement')
para('Required P=4,8 comparisons use the same current calibration, guest rates and placements. S/B denote predicted or measured faster layout. Values are median seconds per step; all repetitions and min-max spreads remain in the archive.')
table(['Map','P','N','Strips measured','Blocks measured','Model winner','Measured winner'],[
 [r['mapping'],r['P'],r['N'],f"{float(r['strips_s']):.5g}",f"{float(r['blocks_s']):.5g}",r['predicted_winner'],r['measured_winner']] for r in comparison],widths=[41,25,45,105,105,87,86],size=7.7)
para('The model predicts the winning layout in 7 of 12 cases. Node placement at P=4,8 favors blocks in all measured cases; the model prefers strips for N=512 because extra startup phases can outweigh smaller payloads. Slot/P4/N8192 is a near model tie yet strips is faster; slot/P8 also has reversals at the two smaller grids. Simple halo byte counts alone do not capture synchronization, topology and contention.','SmallReport')
picture(HERE/'figures/model8192.png',width=6.65,height=4.35)
para('N=8192 model overlay; error bars are the observed minimum/maximum over three invocations. Model and one-microsecond scenarios use identical compute/bandwidth estimates. Full-grid overlays are in Appendix A.','SmallReport')

page('9. Model questions and practical recommendations')
sub('Where does spreading across machines pay off?')
para('Neither measurement nor the calibrated model finds a tested crossover at N=512,2048,8192. Compare equal N with the heat1 serial baseline. The useful observed parallelism is local to heat1; it must not be described as a distributed speed-up.')
sub('Why do predictions and measurements disagree?')
para('Measured cross-guest exchange includes simultaneous TCP streams, phase ordering and waits; the fit uses isolated pairs. Link conditions can drift across an hours-long study and a peer VM became unavailable once. Guest compute rates are heterogeneous and measured in isolation. These are plausible contributors, not individually isolated causes. High spread and mismatch are retained as results, rather than edited away.')
sub('What if startup latency were one microsecond?')
para('Replace ts by 1e-6 seconds on every link, holding measured compute and bandwidth fixed. This is a latency-only counterfactual, not a prediction for a named real supercomputer. The low measured cross-guest bandwidth still imposes a large cost; reducing startup alone gives no tested cross-guest speed-up in this model.')
table(['N=8192 layout/map','P','Measured s/step','Model s/step','Model ts=1us'],[
 [d+'/'+m,str(P),f"{float(strong(d,m,P,8192)['measured_s_per_step']):.5g}",f"{float(strong(d,m,P,8192)['model_total_s_per_step']):.5g}",f"{float(strong(d,m,P,8192)['model_microsecond_s_per_step']):.5g}"]
 for m in ['node','slot'] for P in [4,8] for d in ['strips','blocks']],widths=[154,32,106,106,96])
sub('Advice for this Tailscale cluster')
para('For these tested sizes, first use heat1 with four ranks and slot placement; choose the measured layout at the desired N. Use multiple guests for correctness, learning or larger capacity, not an assumed speed-up. Keep AC/load/slot/transport conditions fixed, inspect routes, retain repetitions and compare compute with communication. Prefer stable direct paths when available, but a direct observation alone does not guarantee good throughput. A deliberately improved network should be measured as a separate labelled campaign.')
para('A real low-latency cluster generally changes bandwidth, processors and contention too. A meaningful hardware forecast would recalibrate both ts and tw and the compute rate. GPU computing and nonblocking overlap are optional extensions; neither was attempted for this CPU/MPI submission.')

page('10. Reproducibility, provenance and contributions')
para('The source revision recorded by the measured campaign is 1355492f732af771446a243ddd79ba9acaf262c7. All measured solver/runner/model sources remain unchanged in the delivery. Public metadata retains the original per-guest executable hashes and preflight inventories. The study ran on 23 November 2026 UTC, with checkpointed resumptions, and was reviewed on 24 November local time.')
table(['Evidence','Count / outcome'],[['Selected heat measurements','429; 143 configurations x3'],['Calibration sweeps / placement probes','18 /16'],['Raw invocations / selected checkpoint references','509 /499'],['Rejected warning-only attempts / nonzero exit attempts','9 /1'],['Completed numerical comparisons, Parts2 /3','84 /108; exact field equality']],widths=[330,164])
para('Nine parent setpgid warning-only invocations were rejected and later retried; all raw attempts remain. One invocation exited 205 after MPI lost contact with heat3 during a reported peer-VM interruption. The supervisor automatically retries only the reviewed exact warning, with limits; genuine failures stop. The completed campaign passes strict offline verification. VM interruptions and network drift limit claims about controlled stationary performance.')
code('make                              # build on each Ubuntu guest\npython3 part4/verify_results.py --data part4/results/2026-11-24-cluster\npython3 part2/verify_results.py \\\n  --data part2/results/2026-11-21-retained-cluster --require-fields\npython3 part3/verify_results.py \\\n  --data part3/results/2026-11-21-retained-cluster --require-fields --require-p8')
para('Public raw records use guest aliases. The reviewed public copy additionally redacts 108 account identifiers from 36 network-status records and has a new manifest. Measured summaries, commands, warnings, CSVs, figures, metadata and checkpoints are unchanged. Original archives, private raw records and supervisor history belong in the private course hand-in.')
sub('Team contributions (reported by the team)')
para('<b>Mario Aouad</b> worked jointly on all project areas: cluster setup, numerical background, serial/MPI implementation, testing, performance experiments and analysis. The team reports shared work rather than separate exclusive ownership.')
para('<b>Mohamad Farchoukh</b> contributed across the same project stages jointly with Mario Aouad and Bassem Haddad, including implementation, cluster runs, verification and interpretation.')
para('<b>Bassem Haddad</b> contributed across all project stages jointly with the other two members, including setup, code, correctness/performance work and analysis. No individual-only responsibilities are inferred.')
para('AI assistance was used and must be accompanied by the complete visible project conversations, actual member/tool/model/date metadata and the logging instructions. Recovered local snapshots and public indexes do not establish completeness of every member\'s earlier sessions. Each team member remains responsible for explaining every implementation and result.')
para('Sources: supplied heat_mpi_project.pdf, sections 3-8 and 10-12; supplied numerical-background tasks including 5.2, 6.3, 7.2, 8.2; repository Part0-4 source/evidence; Open MPI4.1 documentation for mpirun, MPI_Sendrecv, Cartesian topology and datatypes. Separate background-task solutions PDF is supplied. AppendixA: complete strong time/model curves; B: strong speed-up; C: strong efficiency.','SmallReport')

def footer(canvas,doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#CBD5DC'));canvas.line(42,35,A4[0]-42,35)
    canvas.setFont('Report',7.5);canvas.setFillColor(colors.HexColor('#536574'))
    canvas.drawString(42,23,'CPU/MPI heat diffusion | 24 November 2026 | GPU extension omitted')
    canvas.drawRightString(A4[0]-42,23,str(doc.page))
    canvas.restoreState()

main=TMP/'heat-project-main.pdf'
doc=SimpleDocTemplate(str(main),pagesize=A4,leftMargin=43,rightMargin=43,topMargin=38,bottomMargin=43,
                      title='Parallel 2D Heat Diffusion with MPI over Tailscale',
                      author='Mario Aouad; Mohamad Farchoukh; Bassem Haddad')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
main_reader=PdfReader(main)
if len(main_reader.pages)!=10:
    raise ValueError(f'Expected ten main pages, obtained {len(main_reader.pages)}; adjust layout before delivery')
writer=PdfWriter()
writer.append(main)
for title,name in [('Appendix A - Full strong time and model curves','strong_time'),
                   ('Appendix B - Full strong speed-up curves','strong_speedup'),
                   ('Appendix C - Full strong efficiency curves','strong_efficiency')]:
    writer.append(DATA/'analysis'/f'{name}.pdf',outline_item=title)
writer.add_metadata({'/Title':'Parallel 2D Heat Diffusion with MPI over Tailscale',
                     '/Author':'Mario Aouad; Mohamad Farchoukh; Bassem Haddad',
                     '/Subject':'Ten-page CPU/MPI report plus three plot appendices; real reviewed cluster measurements'})
target=HERE/'final-report.pdf'
with target.open('wb') as f:writer.write(f)
print('Built',target,'with',len(PdfReader(target).pages),'pages: 10 main + 3 appendices')
