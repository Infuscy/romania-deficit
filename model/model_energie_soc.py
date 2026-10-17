# -*- coding: utf-8 -*-
"""
Model de impact al șocului energetic (războiul din Orientul Mijlociu / Iran, gaze rusești,
Cernavodă, prețuri electricitate) asupra sustenabilității datoriei României
===================================================================================
Extinde scenariile DSA cu canalele energetice:

1. PREȚUL ENERGIEI → inflație → deflator PIB mai mare (denominator effect pozitiv
   pentru raportul datorie/PIB) DAR și r-g mai prost (randamente suverane ↑),
   salarii/pensii indexate (2027+) și presiuni pe cheltuielile de ajutor social.
2. COSTUL IMPORTULUI DE ENERGIE → deficit de cont curent ↑ → nevoi de finanțare
   externă ↑ → presiune pe curs → depreciere suplimentară a leului → reevaluarea
   în lei a datoriei în valută (~49% din datorie, în EUR/USD).
3. BUGET: compensări/plafonări pentru consumatori vulnerabili + indexări +
   dobânzi mai mari = cheltuieli suplimentare; venituri mai mici (baze de
   impozitare afectate de stagnare).
4. CERNAVODĂ: risc de disponibilitate nucleară → mai mult gaz/cărbune în mix →
   preț electricitate mai mare → mai multă inflație și importuri.
5. GAZE RUSEȘTI: expunere la întreruperea tranzitului (TurkStream/Bulgaria/Serbia)
   → șoc de aprovizionare dacă alternativele (Neptun Deep, GNL) nu acoperă.

Toate șocurile sunt INCREMENTALE față de scenariul S2 și încep în 2027: execuția
bugetară din 2026 (deficit cash 3,82% din PIB după 9 luni, față de 5,35% în 2025; ținta
de 6,0% ESA / 6,2% cash confirmată de MF, S&P, Moody's și BERD) arată că bugetul 2026 absoarbe
deja șocul observat, inclusiv compensările plătite. Scenariile testează persistența sau
agravarea șocului după 2026 (Brent: 100-107 USD/baril în oct. 2026, în banda de bază).

Scenarii:
  E0    Șocul actual persistă moderat în 2027–2028 (prețuri +25%)
  E0bis Prețurile de vârf din 2026 persistă 2 ani (petrol +93%, PZU +88%,
        Cernavodă indisponibilă) — test de stres, nu prognoză
  E1    Șoc sever prelungit (războiul continuă, prețuri +60%, 4 ani)
  E2    Cernavodă: oprire neplanificată + întârziere unități 3/4 (3 ani)
  E3    Întrerupere gaze rusești (TurkStream) în iarna 2026-2027
  E4    Combinat (E0bis prelungit la 4 ani + E2 + E3) — worst case
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

# ---------------------------------------------------------------------------
# 1. PARAMETRI DE CALIBRARE
# ---------------------------------------------------------------------------
# Importul net de energie al României ca % din PIB (aproximativ, 2025)
IMPORT_ENERGIE_PIB = 3.5          # petrol + gaze + electricitate net
# Ponderea energiei în coșul de consum (INS, aproximativ)
ENERGIE_COS_CONSUM = 12.0         # %
# Elasticitatea inflației la prețul energiei (efect direct = ponderea în coș)
# Energie 12% din coș + efecte de runda a doua (BNR: ~2 pp din inflație la o
# liberalizare de preț; aici folosim direct ponderea în coș × intensitatea șocului)
ELAST_INFLATIE = 0.50             # multiplicator de transmitere (direct + runda a doua)
# Elasticitatea deficitului de cont curent la prețul energiei
ELAST_CONT_CURENT = 0.30          # pp deficit cont curent per pp preț energie
# Costul compensărilor pentru consumatori vulnerabili (% din PIB per pp preț energie)
# Ipoteză de stres: ~1,5% din PIB/an la +100% preț. Este peste ordinul de mărime
# observat: compensările decontate în criza energetică (>20 mld. lei cumulat,
# ANRE) înseamnă ~1,2% din PIB pe mai mulți ani, adică sub 0,5% din PIB/an.
# Rezultatele scenariilor E sunt deci mai degrabă o limită superioară.
ELAST_COMPENSATII = 0.015         # pp din PIB cheltuială per pp preț energie
# Indexarea pensiilor/salariilor (din 2027, legea pensiilor indexează cu inflația medie)
ELAST_INDEXARE = 0.15             # pp cheltuială per pp inflație suplimentară
# Sensibilitatea randamentului suveran la inflație (r-g)
ELAST_RANDAMENT = 0.40            # pp randament per pp inflație
# Contribuția nuclearului (Cernavodă) la mixul de electricitate
CERNAVODA_MIX = 20.0              # %
# Costul suplimentar pentru economie dacă Cernavodă cade (gaz, cărbune și
# importuri înlocuiesc ~10 TWh/an). Nu este un cost bugetar direct: în motor,
# reduce creșterea reală cu 0,5 × 1,2 = 0,6 pp pe an (decalaj de producție care se
# cumulează cât durează șocul) și adaugă 0,15 × 1,2 = 0,18 pp din PIB compensări.
# Ipoteză de stres: o estimare de jos în sus (10 TWh × prima de înlocuire,
# plus efectul asupra prețului marginal) dă un cost economic de ordinul a
# 0,5% din PIB/an.
CERNAVODA_COST = 1.2              # pp din PIB cost energie suplimentar pe an
# Canalul valutar: o parte din deficitul de cont curent suplimentar se închide
# prin curs. Deprecierea reală necesară pentru a închide 1 pp din PIB de deficit
# de cont curent = 1 / 0,33 ≈ 3% (elasticitatea contului curent la cursul real
# efectiv, FMI, Country Report 25/294, Anexa I; FMI estimează și o supraevaluare
# reală a leului de ~18,5% în 2024). Regimul de curs este de facto „stabilizat”
# (FMI): BNR intervine, iar rezervele (~20% din PIB), fondurile UE și împrumuturile
# externe pot finanța o parte din deficit. Ipoteză: jumătate din deficitul
# suplimentar se închide prin curs (sensibilitate: 0 / 0,5 / 1).
ELAST_CC_CURS = 0.33              # pp cont curent per 1% depreciere reală (FMI)
PONDERE_CURS = 0.5                # fracția din deficitul suplimentar închisă prin curs
# Ciclul: pierderea de creștere deschide un decalaj de producție (nivel), care se
# cumulează cât timp șocul e activ și se închide liniar în 3 ani după încheierea
# lui (convenția DSA a CE). Bugetul pierde 0,32 pp din PIB per pp de decalaj
# (semi-elasticitatea CE/CF), ca în model_dezindustrializare.
ANI_INCHIDERE_DECALAJ = 3
# Randamentele: prima legată de inflație lovește randamentele de piață, iar rata
# efectivă o preia treptat, pe măsură ce datoria se refinanțează (transmitere_soc
# din model_dsa, ~20% din stoc pe an), ca în S3 și S4.
# Deprecierea nu se recuperează după încheierea șocului (ca după 2009; leul este
# supraevaluat în termeni reali, FMI/BNR): nivelul cursului față de bază rămâne
# la maximul atins. Transmiterea deprecierii în prețuri (deflator mai mare, care
# ar reduce puțin raportul datorie/PIB) nu este modelată.

# ---------------------------------------------------------------------------
# 2. SCENARII DE ȘOC ENERGETIC
# ---------------------------------------------------------------------------
# Parametri: preț_energie (% peste nivelul de bază), durata (ani),
# Cernavodă indisponibilă (0/1), gaze rusești întrerupte (0/1)
SOC = {
    "E0 Șocul actual persistă moderat": {
        "pret_energie": 25, "durata": 2, "cernavoda": 0, "gaze_rusesti": 0,
    },
    "E0bis Prețurile de vârf din 2026 persistă (stres)": {
        "pret_energie": 90, "durata": 2, "cernavoda": 1, "gaze_rusesti": 0,
    },
    "E1 Șoc sever prelungit": {
        "pret_energie": 60, "durata": 4, "cernavoda": 0, "gaze_rusesti": 0,
    },
    "E2 Cernavodă oprit + întârziere 3/4": {
        "pret_energie": 35, "durata": 3, "cernavoda": 1, "gaze_rusesti": 0,
    },
    "E3 Întrerupere gaze rusești (iarna 2026-27)": {
        "pret_energie": 45, "durata": 2, "cernavoda": 0, "gaze_rusesti": 1,
    },
    "E4 Combinat (worst case)": {
        "pret_energie": 90, "durata": 4, "cernavoda": 1, "gaze_rusesti": 1,
    },
}

ANI = list(range(2026, 2036))
AN_START_SOC = 2027          # 2026 e deja absorbit în execuția bugetară (vezi sus)
CRESTERE_REALA_BAZA = 1.5    # % — referința față de care se măsoară pierderea

# Punct de pornire: scenariul S2 (consolidare PDE) din model_dsa — aceleași
# ipoteze de creștere, dobândă, deficit și datorie inițială. Fără șoc, motorul
# de mai jos reproduce exact S2.
def _baza_s2():
    from model_dsa import scenarii
    df = scenarii()["S2 Consolidare conform planului (PDE)"].set_index("an")
    return df

# ---------------------------------------------------------------------------
# 3. MOTORUL
# ---------------------------------------------------------------------------
def ruleaza_soc(nume_soc, baza=None, pondere_curs=PONDERE_CURS):
    from model_dsa import DATORIE_PIB, PONDERE_VALUTA, transmitere_soc
    p = SOC[nume_soc]
    if baza is None:
        baza = _baza_s2()
    # prima de randament pe piață (pp) în anii de șoc, transmisă treptat în rata efectivă
    prima_piata = {}
    for an in ANI:
        if 0 <= an - AN_START_SOC < p["durata"]:
            prima_piata[an] = (p["pret_energie"] / 100.0 * ENERGIE_COS_CONSUM
                               * ELAST_INFLATIE * ELAST_RANDAMENT)
    prima_efectiva = transmitere_soc(prima_piata, ANI)
    rand = []
    d = DATORIE_PIB[2025]                 # 59,3% ESA la finalul lui 2025 (Eurostat)
    nivel_curs = 0.0                      # % cu cât e leul mai slab decât în bază
    decalaj = 0.0                         # decalajul de producție față de bază (%, ≤ 0)
    pas_inchidere = 0.0                   # cât se închide decalajul pe an după șoc

    for an in ANI:
        k = an - AN_START_SOC             # anul de șoc (0 = primul an)
        activ = 0 <= k < p["durata"]
        # intensitatea șocului de preț în anul curent
        intens = p["pret_energie"] / 100.0 if activ else 0.0
        # canalul Cernavodă: cost suplimentar cât timp e indisponibilă
        soc_cernavoda = CERNAVODA_COST if (p["cernavoda"] and activ) else 0.0
        # gaze rusești: iarna 2026-27 → efect în 2027
        soc_gaze = 0.5 if (p["gaze_rusesti"] and k == 0) else 0.0

        # inflația din șoc: preț energie ↑ × pondere în coș (12%) × transmitere
        inflatie_soc = intens * (ENERGIE_COS_CONSUM / 100.0) * ELAST_INFLATIE * 100
        # pierderea de creștere reală față de bază
        pierdere_reala = intens * 2.0 + soc_cernavoda * 0.5 + soc_gaze * 0.3
        # decalajul de producție: se adâncește în anii de șoc, apoi se închide
        decalaj_prec = decalaj
        if pierdere_reala > 0:
            decalaj -= pierdere_reala
            pas_inchidere = -decalaj / ANI_INCHIDERE_DECALAJ
        else:
            decalaj = min(decalaj + pas_inchidere, 0.0)
        delta_crestere = decalaj - decalaj_prec          # < 0 în șoc, > 0 la revenire
        crestere_reala = CRESTERE_REALA_BAZA + delta_crestere
        # creștere nominală: baza S2 + variația decalajului + deflator mai mare
        crestere_nominala = baza.loc[an, "crestere_nominala_%"] + delta_crestere \
            + inflatie_soc * 0.3

        # buget: cheltuieli suplimentare (compensări + indexări)
        chelt_compensatii = intens * ELAST_COMPENSATII * 100 + soc_cernavoda * 0.15
        chelt_indexare = inflatie_soc * ELAST_INDEXARE
        # venituri: componenta ciclică (semi-elasticitate bugetară 0,32 × decalaj)
        venit_pierdut = -decalaj * 0.32

        # dobânzi: randamente suverane ↑ cu inflația, transmise treptat
        r_an = (baza.loc[an, "rata_dobanda_%"] + prima_efectiva[an]) / 100
        g_an = crestere_nominala / 100

        # cont curent: importul de energie (3,5% din PIB) × creșterea prețului
        cont_curent_soc = intens * (IMPORT_ENERGIE_PIB / 100.0) * 100 + soc_gaze * 0.3

        # canalul valutar: deprecierea necesară pentru partea din deficitul
        # suplimentar închisă prin curs; nivelul nu revine după șoc
        nivel_nou = max(nivel_curs, pondere_curs * cont_curent_soc / ELAST_CC_CURS)
        depr_supl = ((1 + nivel_nou / 100) / (1 + nivel_curs / 100) - 1) * 100
        nivel_curs = nivel_nou
        depr_total = ((1 + baza.loc[an, "depreciere_leu_%"] / 100)
                      * (1 + depr_supl / 100) - 1) * 100
        e_an = PONDERE_VALUTA * depr_total / 100
        interes = r_an * d * (1 + e_an) / (1 + g_an)    # dobânzi, % din PIB-ul anului curent

        sold_primar = (baza.loc[an, "sold_primar_%pib"]
                       - chelt_compensatii - chelt_indexare - venit_pierdut)
        deficit = interes - sold_primar

        # ecuația datoriei (identică cu model_dsa, inclusiv reevaluarea
        # datoriei în valută la deprecierea de bază + cea din șoc și alte ajustări
        # stoc-flux din S2)
        d_nou = (d * (1 + r_an) * (1 + e_an) / (1 + g_an) - sold_primar
                 + baza.loc[an, "ajustare_stoc_flux_%pib"])
        ajustare_valutara = e_an * d / (1 + g_an)

        rand.append({
            "an": an, "scenariu": nume_soc,
            "pret_energie_peste_%": intens * 100,
            "inflatie_soc_pp": inflatie_soc,
            "crestere_reala_%": crestere_reala,
            "crestere_nominala_%": crestere_nominala,
            "decalaj_productie_%": decalaj,
            "venit_pierdut_%pib": venit_pierdut,
            "rata_dobanda_%": r_an * 100,
            "chelt_compensatii_%pib": chelt_compensatii,
            "chelt_indexare_%pib": chelt_indexare,
            "interes_%pib": interes,
            "deficit_esa_%pib": deficit,
            "datorie_%pib": d_nou,
            "cont_curent_soc_pp": cont_curent_soc,
            "depreciere_suplimentara_%": depr_supl,
            "curs_peste_baza_%": nivel_curs,
            "ajustare_valutara_%pib": ajustare_valutara,
        })
        d = d_nou
    return pd.DataFrame(rand)

# ---------------------------------------------------------------------------
# 4. RULARE + GRAFICE
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    toate = []
    baza = _baza_s2()
    for nume in SOC:
        df = ruleaza_soc(nume, baza)
        toate.append(df)
    tab = pd.concat(toate, ignore_index=True)
    tab.to_csv(os.path.join(OUT, "energie_soc.csv"), index=False,
               encoding="utf-8-sig")

    print("=== Impactul șocului energetic asupra datoriei (plecând de la S2) ===")
    pivot = tab.pivot(index="an", columns="scenariu", values="datorie_%pib")
    print(pivot.to_string(float_format=lambda x: f"{x:6.2f}"))

    print("\n=== Impactul asupra deficitului ESA ===")
    pivot2 = tab.pivot(index="an", columns="scenariu", values="deficit_esa_%pib")
    print(pivot2.to_string(float_format=lambda x: f"{x:6.2f}"))

    print("\n=== Canalul valutar: leul față de bază (%, nivel) ===")
    pivot4 = tab.pivot(index="an", columns="scenariu", values="curs_peste_baza_%")
    print(pivot4.to_string(float_format=lambda x: f"{x:6.2f}"))

    print("\n=== Datoria 2030 după fracția din deficitul de cont curent închisă prin curs ===")
    sens = pd.DataFrame({
        f"curs {k:g}": {n.split(" ", 1)[0]: ruleaza_soc(n, baza, pondere_curs=k)
                        .set_index("an").loc[2030, "datorie_%pib"] for n in SOC}
        for k in (0.0, PONDERE_CURS, 1.0)})
    sens.to_csv(os.path.join(OUT, "energie_soc_curs.csv"), encoding="utf-8-sig")
    print(sens.to_string(float_format=lambda x: f"{x:6.2f}"))

    print("\n=== Inflația din șoc (pp peste nivelul de bază) ===")
    pivot3 = tab.pivot(index="an", columns="scenariu", values="inflatie_soc_pp")
    print(pivot3.to_string(float_format=lambda x: f"{x:6.2f}"))

    # grafice
    plt.rcParams.update({"font.size": 10, "axes.grid": True,
                         "grid.alpha": 0.3, "figure.dpi": 130})

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    culori = ["#1f77b4", "#ff7f0e", "#e07b00", "#b22222", "#6a3d9a", "#2ca02c"]

    # datorie
    ax = axes[0, 0]
    for i, nume in enumerate(SOC):
        df = tab[tab["scenariu"] == nume]
        ax.plot(df["an"], df["datorie_%pib"], marker="o", lw=2,
                label=nume.split(" ", 1)[0], color=culori[i])
    ax.axhline(60, color="black", ls="--", lw=1, label="60% din PIB")
    ax.set_title("Datoria publică (% din PIB)")
    ax.set_xlabel("An"); ax.set_ylabel("% din PIB")
    ax.legend(fontsize=7)

    # deficit
    ax = axes[0, 1]
    for i, nume in enumerate(SOC):
        df = tab[tab["scenariu"] == nume]
        ax.plot(df["an"], df["deficit_esa_%pib"], marker="o", lw=2,
                label=nume.split(" ", 1)[0], color=culori[i])
    ax.axhline(3, color="black", ls="--", lw=1, label="ținta 3%")
    ax.set_title("Deficitul bugetar ESA (% din PIB)")
    ax.set_xlabel("An"); ax.set_ylabel("% din PIB")
    ax.legend(fontsize=7)

    # inflație din șoc
    ax = axes[1, 0]
    for i, nume in enumerate(SOC):
        df = tab[tab["scenariu"] == nume]
        ax.plot(df["an"], df["inflatie_soc_pp"], marker="o", lw=2,
                label=nume.split(" ", 1)[0], color=culori[i])
    ax.set_title("Inflația din șocul energetic (pp peste nivelul de bază)")
    ax.set_xlabel("An"); ax.set_ylabel("pp")
    ax.legend(fontsize=7)

    # cont curent
    ax = axes[1, 1]
    for i, nume in enumerate(SOC):
        df = tab[tab["scenariu"] == nume]
        ax.plot(df["an"], df["cont_curent_soc_pp"], marker="o", lw=2,
                label=nume.split(" ", 1)[0], color=culori[i])
    ax.set_title("Deficit de cont curent (pp, linie) și leul față de bază (%, punctat)")
    ax.set_xlabel("An"); ax.set_ylabel("pp din PIB")
    ax2 = ax.twinx()
    for i, nume in enumerate(SOC):
        df = tab[tab["scenariu"] == nume]
        ax2.plot(df["an"], df["curs_peste_baza_%"], ls=":", lw=1.6, color=culori[i])
    ax2.set_ylabel("% depreciere peste bază (nivel)")
    ax2.grid(False)
    ax.legend(fontsize=7, loc="center right")

    fig.suptitle("Impactul șocului energetic (războiul din Orientul Mijlociu / gaze rusești / "
                 "Cernavodă) asupra sustenabilității datoriei României", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig8_energie_soc.png"))
    plt.close(fig)

    # grafic separat cu datoria (mare)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for i, nume in enumerate(SOC):
        df = tab[tab["scenariu"] == nume]
        ax.plot(df["an"], df["datorie_%pib"], marker="o", lw=2.2,
                label=nume, color=culori[i])
    ax.axhline(60, color="black", ls="--", lw=1.2, label="Prag UE: 60% din PIB")
    ax.set_title("Datoria publică a României sub șocuri energetice (plecând de la scenariul S2)")
    ax.set_xlabel("An"); ax.set_ylabel("% din PIB")
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig9_datorie_energie.png"))
    plt.close(fig)

    print("\nGata. Figuri:", FIG)
