"""Mesure : total de buts par ligue (constante) vs total déduit du marché over/under 2,5 (Pinnacle clôture).
Source : CSV 2025/26 de football-data.co.uk (colonnes PSCH/PSCD/PSCA et PC>2.5 / PC<2.5, sinon P>2.5 / P<2.5)."""
import csv, io, math, sys, requests
from collections import Counter, defaultdict
sys.argv = sys.argv[:1]
exec(open("scripts/mesure_scores.py", encoding="utf-8").read().split("c = sqlite3.connect")[0])
exec(open("scripts/mesure_scores_v2.py", encoding="utf-8").read().split("sign = lambda")[0].split("def fit_sum")[1].join(["def fit_sum", ""]) if False else "")

def fit_sum(p_h, p_a, total):
    lo, hi = 0.05, total-0.05; target = p_h - p_a
    for _ in range(50):
        mid = (lo+hi)/2
        h, _, a = outcome_probs(matrix(mid, total-mid))
        if h - a < target: lo = mid
        else: hi = mid
    return (lo+hi)/2, total-(lo+hi)/2

def total_from_over(p_over, line=2.5):
    """λ tel que P(Poisson(λ) > line) = p_over (bissection)."""
    k = math.floor(line)
    lo, hi = 0.2, 8.0
    for _ in range(60):
        mid = (lo+hi)/2
        p = 1 - sum(pois(mid, i) for i in range(k+1))
        if p < p_over: lo = mid
        else: hi = mid
    return (lo+hi)/2

rows = []
for div in ["E0","F1","SP1","D1","I1"]:
    r = requests.get(f"https://www.football-data.co.uk/mmz4281/2526/{div}.csv", timeout=60)
    text = r.content.decode("utf-8-sig", errors="replace")
    for row in csv.DictReader(io.StringIO(text)):
        try:
            h,d,a = float(row.get("PSCH") or row["PSH"]), float(row.get("PSCD") or row["PSD"]), float(row.get("PSCA") or row["PSA"])
            o = float(row.get("PC>2.5") or row.get("P>2.5") or row.get("AvgC>2.5") or row["Avg>2.5"])
            u = float(row.get("PC<2.5") or row.get("P<2.5") or row.get("AvgC<2.5") or row["Avg<2.5"])
            if o <= 1 or u <= 1: continue
            hs,as_ = int(row["FTHG"]), int(row["FTAG"])
        except (KeyError, ValueError, TypeError):
            continue
        rows.append((div,hs,as_,h,d,a,o,u))
print("matchs avec 1N2 + O/U 2,5 Pinnacle :", len(rows))
league = defaultdict(list)
for div,hs,as_,*_ in rows: league[div].append(hs+as_)
mean_goals = {k: sum(v)/len(v) for k,v in league.items()}

sign = lambda x,y: (x>y)-(x<y)
def run(name, total_fn):
    n=exact=winner=0; bins=defaultdict(lambda:[0,0]); ll=0; tot_err=0; tops=Counter()
    for div,hs,as_,h,d,a,o,u in rows:
        p_h,p_d,p_a = implied(h,d,a)
        total = total_fn(div,o,u)
        lh,la = fit_sum(p_h,p_a,total); m = matrix(lh,la)
        fav = max((p_h,1),(p_d,0),(p_a,-1))[1]
        cells = [(i,j) for i in range(MAXG+1) for j in range(MAXG+1) if sign(i,j)==fav]
        i,j = max(cells, key=lambda t: m[t[0]][t[1]])
        hit = (i,j)==(hs,as_); n+=1; exact+=hit; winner += sign(i,j)==sign(hs,as_)
        b=round(m[i][j]*100); bins[b][0]+=1; bins[b][1]+=hit; tops[f"{i}-{j}"]+=1
        ll += -math.log(max(m[min(hs,MAXG)][min(as_,MAXG)],1e-9)); tot_err += (total-(hs+as_))**2
    ann = sum(k*v[0] for k,v in bins.items())/n
    print(f"\n== {name} == n={n} exact {exact/n:.1%} (annoncé {ann:.1f} %) vainqueur {winner/n:.1%} logloss score {ll/n:.3f} RMSE total {math.sqrt(tot_err/n):.3f}")
    print("  scores :", tops.most_common(5))
    print("  calibration :", "  ".join(f"{k}%→{v[1]/v[0]:.0%}(n{v[0]})" for k,v in sorted(bins.items()) if v[0]>=60))

run("D  moyenne de la ligue", lambda div,o,u: mean_goals[div])
run("E  total marché O/U 2,5 Pinnacle", lambda div,o,u: total_from_over((1/o)/((1/o)+(1/u))))
run("F  moyenne des deux", lambda div,o,u: 0.5*mean_goals[div] + 0.5*total_from_over((1/o)/((1/o)+(1/u))))
