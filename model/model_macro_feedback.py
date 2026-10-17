# -*- coding: utf-8 -*-
"""
Model de feedback macroeconomic al consolidării fiscale (2025–2030)
===================================================================
Extinde modelul DSA cu efectele măsurilor de consolidare (majorări de taxe,
înghețarea salariilor și pensiilor, tăieri de cheltuieli) asupra economiei
reale, consumului și comportamentului agenților economici.

Metoda oficială (Consiliul Fiscal, Opinia 2026, nota 33 — metodologia CE din
DSA):
    efect de runda a doua = impact inițial × multiplicator fiscal × semi-elasticitate bugetară
    multiplicator fiscal agregat = 0,75
    semi-elasticitate bugetară   = 0,32
Exemplu oficial: pachetul 2026 = +1,25 pp din PIB venituri (brut, estimare MF);
metoda standard dă un efect de runda a doua ≈ -0,3 pp din PIB (1,25 × 0,75 × 0,32).
Bugetul 2026 încorporează doar +0,8 pp din PIB; CF apreciază că diferența de
~0,45 pp „pare să integreze" efectele de runda a doua și este „apropiată" de
estimarea standard.

Modele folosite aici:
1) Impactul asupra PIB real:    dY_t  = -m × dPB_t         (în anul măsurii, pp din PIB)
2) Decalajul de producție:      Gap_t = m × Σ_s dPB_s × w(t−s), cu w = 1, 2/3, 1/3, 0:
                                efectul fiecărei măsuri se stinge în 3 ani (convenția
                                DSA a CE: decalajul se închide în T+3)
3) Limita superioară:           Ylvl_t = m × Σ_{s<=t} dPB_s (fără nicio recuperare)
4) Consumul:                    la fel, cu m_c = 0,6 × m (0,45 la m=0,75)
5) Feedback bugetar:            dB_t  = -ε × Gap_t         (componenta ciclică)
6) Testul „consolidare autodistructivă": fracția păstrată în anul măsurii = 1 − m·ε
unde dPB = îmbunătățirea soldului primar (pp din PIB, pozitiv = consolidare).

Calibrări alternative pentru sensibilitate: m ∈ {0,4 (moderate, măsuri pe
partea de ofertă), 0,75 (oficial CE/CF), 1,2 (recesiune + consumatori cu
constrângeri de lichiditate, vezi Grecia 2010-2015)}.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(__file__), "outputs")
FIG = os.path.join(os.path.dirname(__file__), "figuri")
os.makedirs(OUT, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

M_OFICIAL = 0.75      # multiplicator fiscal agregat (CE/CF, metodologia DSA)
EPS_OFICIAL = 0.32    # semi-elasticitate bugetară (CE/CF, metodologia DSA)
PONDERE_CONSUM = 0.60  # fracția din pierderea de PIB care cade pe consumul privat
M_CONSUM = PONDERE_CONSUM * M_OFICIAL   # 0,45 la multiplicatorul oficial
# Ponderea unui impuls fiscal rămasă în decalajul de producție în anii t, t+1, t+2
# (0 din t+3): decalajul se închide în 3 ani, ca în DSA-ul CE.
STINGERE = (1.0, 2 / 3, 1 / 3)

# ---------------------------------------------------------------------------
# 1. CONSOLIDAREA FISCALĂ: îmbunătățirea soldului primar (pp din PIB)
# ---------------------------------------------------------------------------
# Calculat din traseul deficitului ESA (Legea bugetului 2026 / recomandarea
# Consiliului UE) minus evoluția dobânzilor:
#   sold primar = dobânzi(%PIB) − deficit ESA(%PIB)
#   dPB_t = sold primar_t − sold primar_{t−1}
# 2025: deficit ESA 9,3 → 7,8 (pe PIB-ul semidefinitiv INS), dobânzi 2,2 → 2,6
# (sold primar −7,1 → −5,2).
# 2026–2030: soldul primar al scenariului S2 din model_dsa (deficit ESA
# 6,0 → 5,2 → 4,2 → 3,2 → 2,8, dobânzile rezultate din model).
def _d_pb(an_final=2040):
    from model_dsa import scenarii, DEFICIT, INTERES_PIB
    s2 = scenarii()["S2 Consolidare conform planului (PDE)"].set_index("an")
    pb = {2025: INTERES_PIB[2025] - DEFICIT["esa"][2025]}
    for an in range(2026, an_final + 1):
        pb[an] = s2.loc[an, "sold_primar_%pib"]
    d = {2025: pb[2025] - (INTERES_PIB[2024] - DEFICIT["esa"][2024])}
    for an in range(2026, an_final + 1):
        d[an] = pb[an] - pb[an - 1]
    return d

D_PB_TOT = _d_pb()                                   # 2025-2040
D_PB = {an: v for an, v in D_PB_TOT.items() if an <= 2030}
ANI = list(D_PB.keys())                              # 2025-2030 (tabelul de efecte)

def decalaj(impulsuri, ani):
    """Decalajul de producție (pp, pozitiv = PIB sub traiectoria fără măsuri) din
    impulsurile an -> m·dPB, cu stingerea STINGERE."""
    return {an: sum(v * STINGERE[an - s] for s, v in impulsuri.items()
                    if 0 <= an - s < len(STINGERE))
            for an in ani}

# Consum privat (% din PIB) — pondere în economie pentru context
CONSUM_PIB = 62.0

# ---------------------------------------------------------------------------
# 2. CALCULUL EFECTELOR
# ---------------------------------------------------------------------------
def efecte(m=M_OFICIAL, eps=EPS_OFICIAL, m_consum=None):
    """Returnează efectele consolidate ale pachetului de măsuri.
    Multiplicatorul consumului scalează cu m (m_c = 0,6 × m), dacă nu e dat explicit."""
    if m_consum is None:
        m_consum = PONDERE_CONSUM * m
    gap_y = decalaj({an: m * D_PB[an] for an in ANI}, ANI)
    gap_c = decalaj({an: m_consum * D_PB[an] for an in ANI}, ANI)
    rand = []
    y_cum = 0.0
    c_cum = 0.0
    for an in ANI:
        dpb = D_PB[an]
        y_flow = m * dpb                 # impactul în anul măsurii (pp)
        y_cum += y_flow                  # limită superioară: fără recuperare
        c_flow = m_consum * dpb
        c_cum += c_flow
        rand.append({
            "an": an,
            "consolidare_pp_pib": dpb,
            "pierdere_pib_flux_pp": y_flow,
            "decalaj_pib_pp": gap_y[an],
            "pierdere_pib_cumulata_pp": y_cum,
            "pierdere_consum_flux_pp": c_flow,
            "decalaj_consum_pp": gap_c[an],
            "pierdere_consum_cumulata_pp": c_cum,
            "consum_crestere_pierduta_pp": c_flow / CONSUM_PIB * 100,
            "feedback_bugetar_pp": eps * gap_y[an],    # componenta ciclică a soldului
            "efect_net_menținut_%": (1 - m * eps) * 100,
        })
    return pd.DataFrame(rand)

def traseu_datorie_cu_feedback(m=M_OFICIAL, eps=EPS_OFICIAL):
    """Traseul datoriei (S2) ajustat cu feedback-ul macro al consolidării.

    Punct de plecare: scenariul S2 din model_dsa (aceleași ipoteze de creștere,
    dobândă, deficit și datorie inițială). Proiecțiile oficiale includ deja
    efectul pentru m=0,75, deci m=0,75 reproduce exact S2. Ajustări pentru alt m,
    din impulsurile din 2026 încolo (2025 este deja în date):
      - decalajul suplimentar Gap_t = (m − 0,75)·Σ ΔPB_s·w(t−s) (se închide în 3 ani);
      - creșterea nominală scade cu variația decalajului (și revine când se închide);
      - deficitul se deteriorează cu ε·Gap_t (componenta ciclică).
    Cursul EUR/RON și alte ajustări stoc-flux (prefinanțarea SAFE din 2026) urmează S2.
    """
    from model_dsa import (crestere_nominala_pib, rata_dobanda, DATORIE_PIB,
                           depreciere_leu, PONDERE_VALUTA, scenarii)
    d = DATORIE_PIB[2025]         # datorie ESA la finalul lui 2025 (% PIB)
    g0 = crestere_nominala_pib()  # nominal, S2
    s2 = scenarii()["S2 Consolidare conform planului (PDE)"].set_index("an")
    def0 = s2["deficit_esa_%pib"]
    sfa = s2["ajustare_stoc_flux_%pib"]
    r = rata_dobanda()
    e = depreciere_leu()
    ani = [an for an in D_PB_TOT if an >= 2026]
    gap = decalaj({an: (m - M_OFICIAL) * D_PB_TOT[an] for an in ani}, ani)
    gap_prev = 0.0
    rand = []
    for an in ani:
        pierdere_supl = gap[an] - gap_prev       # pierderea de creștere a anului
        gap_prev = gap[an]
        g = g0[an] - pierdere_supl
        deficit = def0[an] + eps * gap[an]
        r_an = r[an] / 100
        g_an = g / 100
        e_an = PONDERE_VALUTA * e[an] / 100   # reevaluarea părții în valută
        interes = r_an * d * (1 + e_an) / (1 + g_an)   # % din PIB-ul anului curent
        sold_primar = interes - deficit
        d_nou = d * (1 + r_an) * (1 + e_an) / (1 + g_an) - sold_primar + sfa[an]
        rand.append({
            "an": an, "multiplicator": m,
            "crestere_nominala_%": g, "deficit_esa_%pib": deficit,
            "datorie_%pib": d_nou, "pierdere_supl_pib_pp": pierdere_supl,
            "decalaj_supl_pp": gap[an],
        })
        d = d_nou
    return pd.DataFrame(rand)

# ---------------------------------------------------------------------------
# 3. RULARE + GRAFICE
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    scen = {"m=0,4 (măsuri puțin contracționiste)": 0.40,
            "m=0,75 (oficial CE/Consiliul Fiscal)": M_OFICIAL,
            "m=1,2 (recesiune, consumatori constrânși)": 1.20}
    toate = []
    for nume, m in scen.items():
        df = efecte(m=m)
        df.insert(0, "scenariu", nume)
        toate.append(df)
    tab = pd.concat(toate, ignore_index=True)
    tab.to_csv(os.path.join(OUT, "feedback_macro.csv"), index=False,
               encoding="utf-8-sig")
    print("=== Efectele consolidării 2025-2030 (oficial m=0,75; ε=0,32) ===")
    print(tab[tab["scenariu"].str.startswith("m=0,75")][
        ["an", "consolidare_pp_pib", "decalaj_pib_pp", "pierdere_pib_cumulata_pp",
         "decalaj_consum_pp", "pierdere_consum_cumulata_pp", "consum_crestere_pierduta_pp",
         "feedback_bugetar_pp", "efect_net_menținut_%"]]
        .to_string(index=False, float_format=lambda x: f"{x:6.2f}"))

    # --- grafic 6: pierderea cumulată de PIB ---
    plt.rcParams.update({"font.size": 10, "axes.grid": True,
                         "grid.alpha": 0.3, "figure.dpi": 130})
    fig, ax = plt.subplots(figsize=(9, 5))
    culori = {"m=0,4": "#1f77b4", "m=0,75": "#e07b00", "m=1,2": "#b22222"}
    for nume, m in scen.items():
        df = efecte(m=m)
        cheie = nume.split(" ")[0]
        ax.plot(df["an"], df["decalaj_pib_pp"], marker="o",
                lw=2.2, label=nume, color=culori[cheie])
        ax.plot(df["an"], df["pierdere_pib_cumulata_pp"], ls=":",
                lw=1.4, color=culori[cheie], alpha=0.8)
        ax.plot(df["an"], df["decalaj_consum_pp"], ls="--",
                lw=1.6, color=culori[cheie], alpha=0.7)
    ax.set_title("Costul consolidării fiscale 2025–2030: PIB sub traiectoria fără măsuri\n"
                 "continuu = PIB (decalajul se închide în 3 ani) · punctat = fără recuperare"
                 " · întrerupt = consum")
    ax.set_xlabel("An"); ax.set_ylabel("pp din PIB (nivel, față de traiectoria fără măsuri)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig6_cost_consolidare.png"))
    plt.close(fig)

    # --- grafic 7: datoria cu feedback ---
    fig, ax = plt.subplots(figsize=(9, 5))
    for nume, m in scen.items():
        df = traseu_datorie_cu_feedback(m=m)
        cheie = nume.split(" ")[0]
        ax.plot(df["an"], df["datorie_%pib"], marker="o", lw=2.2,
                label=nume, color=culori[cheie])
    ax.axhline(60, color="black", ls="--", lw=1, label="60% din PIB")
    ax.set_title("Datoria publică (S2) ajustată cu feedback macro al consolidării")
    ax.set_xlabel("An"); ax.set_ylabel("% din PIB")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig7_datorie_feedback.png"))
    plt.close(fig)

    # --- tabel trasee datorie ---
    trasee = pd.concat([traseu_datorie_cu_feedback(m=m) for m in scen.values()],
                       ignore_index=True)
    trasee.to_csv(os.path.join(OUT, "datorie_cu_feedback.csv"),
                  index=False, encoding="utf-8-sig")
    print("\n=== Datoria (S2) cu feedback macro (% din PIB) ===")
    print(trasee.pivot(index="an", columns="multiplicator",
                       values="datorie_%pib").to_string(
        float_format=lambda x: f"{x:6.2f}"))

    # --- testul „autodestructiv" ---
    print("\n=== Testul de autodestrucție a consolidării (1 − m·ε) ===")
    for nume, m in scen.items():
        print(f"  {nume}: se păstrează {(1 - m * EPS_OFICIAL) * 100:.0f}% "
              f"din efectul bugetar; se pierde {m * EPS_OFICIAL * 100:.0f}%")
    print("\nGata. Figuri:", FIG)
