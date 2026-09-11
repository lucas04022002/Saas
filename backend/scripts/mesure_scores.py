"""Mesure : score le plus probable déduit des cotes 1N2 (Poisson) vs résultat réel.

Usage : python scripts/mesure_scores.py [chemin sqlite]  (défaut dev.db)
Ne touche pas au produit : c'est la mesure préalable (tribunal) avant d'afficher quoi que ce soit.
"""
import math, sqlite3, sys
from collections import Counter, defaultdict

DB = sys.argv[1] if len(sys.argv) > 1 else "dev.db"
MAXG = 8

def implied(h, d, a):
    inv = [1/h, 1/d, 1/a]; s = sum(inv)
    return [x/s for x in inv]

def pois(l, k):
    return math.exp(-l) * l**k / math.factorial(k)

def matrix(lh, la):
    ph = [pois(lh, k) for k in range(MAXG+1)]
    pa = [pois(la, k) for k in range(MAXG+1)]
    return [[ph[i]*pa[j] for j in range(MAXG+1)] for i in range(MAXG+1)]

def outcome_probs(m):
    h = sum(m[i][j] for i in range(MAXG+1) for j in range(MAXG+1) if i > j)
    d = sum(m[i][i] for i in range(MAXG+1))
    a = sum(m[i][j] for i in range(MAXG+1) for j in range(MAXG+1) if i < j)
    return h, d, a

def fit(p_h, p_a, iters=60):
    """Trouve (λh, λa) tels que P(H)=p_h et P(A)=p_a. Descente simple sur 2 paramètres."""
    lh, la = 1.4, 1.1
    step = 0.5
    def err(lh, la):
        h, _, a = outcome_probs(matrix(lh, la))
        return (h-p_h)**2 + (a-p_a)**2
    e = err(lh, la)
    for _ in range(iters):
        improved = False
        for dh, da in ((step,0),(-step,0),(0,step),(0,-step)):
            nh, na = max(0.05, lh+dh), max(0.05, la+da)
            ne = err(nh, na)
            if ne < e:
                lh, la, e, improved = nh, na, ne, True
        if not improved:
            step /= 2
            if step < 1e-4: break
    return lh, la

c = sqlite3.connect(DB)
rows = c.execute("""
  select m.id, m.competition, m.home_score, m.away_score, s.bookmaker, s.home, s.draw, s.away
  from matches m join odds_snapshots s on s.match_id = m.id
  where m.status='FINISHED' and m.home_score is not null
  order by m.id, s.taken_at desc""").fetchall()
# une ligne par match : pinnacle si dispo, sinon moyenne ; dernière prise
best = {}
for mid, comp, hs, as_, book, h, d, a in rows:
    if not (h and d and a): continue
    cur = best.get(mid)
    rank = 0 if book == "fd_uk_pinnacle" else 1
    if cur is None or rank < cur[0]:
        best[mid] = (rank, comp, hs, as_, h, d, a)

n = 0; exact = 0; winner = 0; fav_winner = 0
bins = defaultdict(lambda: [0, 0])   # proba annoncée du score en tête -> [n, touchés]
top_scores = Counter(); by_comp = defaultdict(lambda: [0, 0, 0])
for mid, (rank, comp, hs, as_, h, d, a) in best.items():
    p_h, p_d, p_a = implied(h, d, a)
    lh, la = fit(p_h, p_a)
    m = matrix(lh, la)
    i, j = max(((i, j) for i in range(MAXG+1) for j in range(MAXG+1)), key=lambda t: m[t[0]][t[1]])
    p_top = m[i][j]
    n += 1
    hit = (i, j) == (hs, as_)
    exact += hit
    sign = lambda x, y: (x > y) - (x < y)
    winner += sign(i, j) == sign(hs, as_)
    fav = max((p_h, 1), (p_d, 0), (p_a, -1))[1]
    fav_winner += fav == sign(hs, as_)
    b = round(p_top * 100)
    bins[b][0] += 1; bins[b][1] += hit
    top_scores[f"{i}-{j}"] += 1
    by_comp[comp][0] += 1; by_comp[comp][1] += hit; by_comp[comp][2] += (sign(i, j) == sign(hs, as_))

print(f"matchs mesurés : {n}")
print(f"score exact touché : {exact/n:.1%}   (proba moyenne annoncée : {sum(k*v[0] for k,v in bins.items())/n:.1f} %)")
print(f"bon vainqueur (via score affiché) : {winner/n:.1%}   vs favori 1N2 direct : {fav_winner/n:.1%}")
print("scores affichés les plus fréquents :", top_scores.most_common(6))
print("\ncalibration (proba annoncée du score en tête -> taux réel) :")
for k in sorted(bins):
    tot, ok = bins[k]
    if tot >= 30: print(f"  annoncé {k:2d} % : réel {ok/tot:5.1%}  (n={tot})")
print("\npar compétition (n, exact, vainqueur) :")
for comp, (t, e, w) in sorted(by_comp.items()):
    print(f"  {comp}: n={t} exact={e/t:.1%} vainqueur={w/t:.1%}")
