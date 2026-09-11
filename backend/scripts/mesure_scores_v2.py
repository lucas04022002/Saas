import math, sqlite3, sys
from collections import Counter, defaultdict
sys.argv = sys.argv[:1]
exec(open("scripts/mesure_scores.py", encoding="utf-8").read().split("c = sqlite3.connect")[0])  # réutilise implied/pois/matrix/outcome_probs/fit

c = sqlite3.connect("dev.db")
rows = c.execute("""select m.id, m.competition, m.home_score, m.away_score, s.bookmaker, s.home, s.draw, s.away
  from matches m join odds_snapshots s on s.match_id = m.id
  where m.status='FINISHED' and m.home_score is not null order by m.id, s.taken_at desc""").fetchall()
best = {}
for mid, comp, hs, as_, book, h, d, a in rows:
    if not (h and d and a): continue
    rank = 0 if book == "fd_uk_pinnacle" else 1
    if mid not in best or rank < best[mid][0]: best[mid] = (rank, comp, hs, as_, h, d, a)

# total de buts moyen par ligue (sur la saison, sert de repli)
goals = defaultdict(list)
for _, (r, comp, hs, as_, *_x) in best.items(): goals[comp].append(hs+as_)
mean_goals = {k: sum(v)/len(v) for k, v in goals.items()}
print("buts moyens par ligue :", {k: round(v,2) for k,v in mean_goals.items()})

def fit_sum(p_h, p_a, total):
    """λh+λa = total fixé ; un seul paramètre (part domicile) pour coller à p_h - p_a."""
    lo, hi = 0.05, total-0.05
    target = p_h - p_a
    for _ in range(50):
        mid = (lo+hi)/2
        h, _, a = outcome_probs(matrix(mid, total-mid))
        if h - a < target: lo = mid
        else: hi = mid
    return (lo+hi)/2, total-(lo+hi)/2

sign = lambda x, y: (x > y) - (x < y)
def run(name, fitter, conditional):
    n=exact=winner=0; lam=0; bins=defaultdict(lambda:[0,0]); tops=Counter(); ll=0
    for mid,(r,comp,hs,as_,h,d,a) in best.items():
        p_h,p_d,p_a = implied(h,d,a)
        lh,la = fitter(p_h,p_a,comp)
        m = matrix(lh,la); lam += lh+la
        fav = max((p_h,1),(p_d,0),(p_a,-1))[1]
        cells = [(i,j) for i in range(MAXG+1) for j in range(MAXG+1) if (not conditional or sign(i,j)==fav)]
        i,j = max(cells, key=lambda t: m[t[0]][t[1]])
        p_top = m[i][j]; hit = (i,j)==(hs,as_)
        n+=1; exact+=hit; winner += sign(i,j)==sign(hs,as_)
        b=round(p_top*100); bins[b][0]+=1; bins[b][1]+=hit; tops[f"{i}-{j}"]+=1
        ll += -math.log(max(m[min(hs,MAXG)][min(as_,MAXG)],1e-9))
    ann = sum(k*v[0] for k,v in bins.items())/n
    print(f"\n== {name} ==  n={n}  exact {exact/n:.1%} (annoncé {ann:.1f} %)  vainqueur {winner/n:.1%}  λ moyen {lam/n:.2f}  logloss score {ll/n:.3f}")
    print("  scores affichés :", tops.most_common(5))
    print("  calibration :", "  ".join(f"{k}%→{v[1]/v[0]:.0%}(n{v[0]})" for k,v in sorted(bins.items()) if v[0]>=60))

run("A  2 contraintes (p_h,p_a), score libre", lambda ph,pa,c: fit(ph,pa), False)
run("B  2 contraintes, score cohérent avec favori", lambda ph,pa,c: fit(ph,pa), True)
run("C  total ligue fixé, score libre", lambda ph,pa,c: fit_sum(ph,pa,mean_goals[c]), False)
run("D  total ligue fixé, score cohérent avec favori", lambda ph,pa,c: fit_sum(ph,pa,mean_goals[c]), True)
