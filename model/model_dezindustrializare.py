# -*- coding: utf-8 -*-
"""
Model de stres: creșterea șomajului și retragerea investitorilor străini
(dezindustrializare) și efectul asupra sustenabilității datoriei României
==========================================================================
Extinde scenariul S2 (consolidare conform planului PDE) cu patru canale:

1. CREȘTERE: plecarea producătorilor străini (relocări în Maroc, Turcia, Serbia,
   în afara UE) reduce creșterea POTENȚIALĂ (pierdere permanentă de nivel al PIB),
   iar concedierile și cererea slabă deschid un decalaj de producție (output gap)
   temporar. Ambele intră în creșterea nominală g → r − g mai prost.
2. ȘOMAJ: legea lui Okun leagă decalajul de producție de rata șomajului
   (Δu = −OKUN × gap). Costul bugetar DIRECT al șomajului (indemnizații) este
   foarte mic în România; costul real vine din impozitele și contribuțiile pierdute,
   prinse de semi-elasticitatea bugetară 0,32 (CE / Consiliul Fiscal).
3. BAZA FISCALĂ: producția relocată este formală, exportatoare și plătește
   contribuții și impozite peste media economiei; înlocuirea ei cu activități mai
   puțin productive scade veniturile/PIB permanent (eroziune structurală).
4. FINANȚARE EXTERNĂ: investițiile străine directe (ISD) finanțează o parte din
   deficitul de cont curent. Mai puține ISD → nevoie de finanțare externă ↑ →
   presiune pe curs → leu mai slab → reevaluarea datoriei în valută (~49%).
   Același mecanism ca în model_energie_soc (elasticitate FMI 0,33, jumătate din
   decalaj închis prin curs).

Politica fiscală: soldul primar structural rămâne cel din S2 (nicio măsură
suplimentară); componenta ciclică și eroziunea bazei fiscale îl înrăutățesc.
Fără șoc (D0), motorul reproduce exact S2.

Date de calibrare (vezi raportul, secțiunea 6.8, și _research/somaj_isd_2026.md):
- INS: șomaj BIM 6,4% în aug. 2026, 523.400 șomeri (494.800 în aug. 2025)
- ANOFM: 260.919 șomeri înregistrați, din care 61.718 indemnizați (aug. 2026);
  concedieri colective ian.–aug. 2026: 10.451 persoane (+25% a/a)
- BNR: ISD 7.907 mil. € în 2025; 1.127 mil. € în ian.–iul. 2026 (−77% a/a)
- INS: producția industrială −3,7% în ian.–iul. 2026, prelucrătoare −4,8%
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
# Semi-elasticitatea soldului bugetar la decalajul de producție (CE / Consiliul
# Fiscal), aceeași ca în model_macro_feedback.
SEMI_ELAST_BUGET = 0.32
# Coeficientul Okun: pp de șomaj per pp de decalaj de producție. Ipoteză,
# aproximativ în linie cu 2025–2026: șomajul a urcat cu ~0,5 pp (494.800 →
# 523.400 șomeri) pe un decalaj de producție de ~2 pp. Coeficientul este mic în
# România: o parte din cei concediați emigrează sau trec în inactivitate.
OKUN = 0.3
SOMAJ_2026 = 6.4                  # % (INS, aug. 2026, serie ajustată sezonier)
POPULATIE_ACTIVA_MII = 523.4 / 0.064   # ~8.180 mii persoane (INS)
# Costul indemnizațiilor de șomaj: 61.718 indemnizați din 523.400 șomeri BIM
# (~12%); indemnizația = 75% din ISR (660 lei) + 3–10% din salariul brut mediu
# anterior după stagiu; ipoteză: ~900 lei/lună în medie.
ACOPERIRE_INDEMNIZATIE = 61.718 / 523.4
INDEMNIZATIE_LUNARA_LEI = 900.0
# Eroziunea bazei fiscale: pp din PIB venituri pierdute la 1% din PIB activitate
# relocată, peste efectul proporțional. Ipoteză: producția exportatoare relocată
# poartă impozite și contribuții cu ~10 pp din valoarea adăugată peste media
# economiei (~27–28% din PIB venituri) → 0,10 (sensibilitate 0 / 0,1 / 0,2).
EROZIUNE_BAZA = 0.10
# ISD: 7.907 mil. € în 2025 ≈ 2,1% din PIB (PIB 2025 ≈ 380 mld. €); media 2022–2025
# ≈ 7,7 mld. €/an. În ian.–iul. 2026, 1.127 mil. € (anualizat ~1,9 mld. €, ~0,5% din
# PIB): un deficit de finanțare nedatorie de ~1,5 pp din PIB față de normal.
ISD_2025_MIL_EUR = 7907
ISD_2026_IAN_IUL_MIL_EUR = 1127

AN_START_SOC = 2027      # 2026 e deja în datele observate și în bugetul executat

# ---------------------------------------------------------------------------
# 2. SCENARII
# ---------------------------------------------------------------------------
# pot:  pierderea de creștere potențială reală (pp/an), an -> valoare
# gap:  decalajul de producție față de S2 (pp din PIB potențial), an -> valoare
# isd:  ISD mai mici decât normal (pp din PIB), an -> valoare
# prima: randamente de piață peste bază (pp), din 2027 (risc de rating)
SOC = {
    "D0 Bază (S2, fără șoc)": {"pot": {}, "gap": {}, "isd": {}, "prima": 0.0},
    "D1 Răcire ciclică (șomaj temporar)": {
        "pot": {},
        "gap": {2027: -1.0, 2028: -0.5},
        "isd": {2027: 0.75},
        "prima": 0.0,
    },
    "D2 Dezindustrializare graduală": {
        "pot": {an: -0.4 for an in range(2027, 2033)},
        "gap": {2027: -1.0, 2028: -1.0, 2029: -0.5},
        "isd": {2027: 1.5, 2028: 1.5, 2029: 0.75, 2030: 0.75},
        "prima": 0.0,
    },
    "D3 Exod sever al investitorilor (stres)": {
        "pot": {an: -0.8 for an in range(2027, 2032)},
        "gap": {2027: -2.0, 2028: -1.5, 2029: -0.5},
        "isd": {2027: 2.0, 2028: 2.0, 2029: 2.0, 2030: 2.0},
        "prima": 1.0,
    },
}

def _baza_s2():
    from model_dsa import scenarii
    return scenarii()["S2 Consolidare conform planului (PDE)"].set_index("an")

# ---------------------------------------------------------------------------
# 3. MOTORUL
# ---------------------------------------------------------------------------
def ruleaza(nume_soc, baza=None, eroziune=EROZIUNE_BAZA, pondere_curs=None, okun=OKUN,
            p=None):
    """p = parametrii șocului (implicit SOC[nume_soc]); folosit de descompunere()."""
    from model_dsa import DATORIE_PIB, PONDERE_VALUTA, transmitere_soc
    from model_energie_soc import ELAST_CC_CURS, PONDERE_CURS
    if pondere_curs is None:
        pondere_curs = PONDERE_CURS
    if baza is None:
        baza = _baza_s2()
    if p is None:
        p = SOC[nume_soc]
    ani = list(baza.index)
    soc_r = transmitere_soc({an: p["prima"] for an in ani if an >= AN_START_SOC}, ani)

    rand = []
    d = DATORIE_PIB[2025]
    gap_prev = 0.0
    nivel_pot = 0.0           # pierderea de nivel a PIB potențial față de S2 (%)
    nivel_curs = 0.0          # % cu cât e leul mai slab decât în S2 (nivel)
    for an in ani:
        b = baza.loc[an]
        pot = p["pot"].get(an, 0.0)
        gap = p["gap"].get(an, 0.0)
        # creșterea reală față de S2 = pierderea potențială + variația decalajului
        delta_g = pot + (gap - gap_prev)
        gap_prev = gap
        g_an = (b["crestere_nominala_%"] + delta_g) / 100
        nivel_pot = ((1 + nivel_pot / 100) * (1 + pot / 100) - 1) * 100
        nivel_pib = ((1 + nivel_pot / 100) * (1 + gap / 100) - 1) * 100

        # șomaj: Okun pe decalajul de producție
        delta_u = -okun * gap
        someri_supl_mii = delta_u / 100 * POPULATIE_ACTIVA_MII
        # cost indemnizații, % din PIB-ul anului
        pib_mld = b["pib_mld"] * (1 + nivel_pib / 100)
        cost_somaj = (someri_supl_mii * 1e3 * ACOPERIRE_INDEMNIZATIE
                      * INDEMNIZATIE_LUNARA_LEI * 12) / (pib_mld * 1e9) * 100

        # buget: componenta ciclică + eroziunea bazei fiscale (nivel permanent)
        ciclic = SEMI_ELAST_BUGET * gap                   # negativ = deficit mai mare
        erodare = eroziune * (-nivel_pot)
        sold_primar = b["sold_primar_%pib"] + ciclic - erodare - cost_somaj

        # canalul valutar: ISD lipsă → finanțare externă ↑ → curs
        isd_lipsa = p["isd"].get(an, 0.0)
        nivel_nou = max(nivel_curs, pondere_curs * isd_lipsa / ELAST_CC_CURS)
        depr_supl = ((1 + nivel_nou / 100) / (1 + nivel_curs / 100) - 1) * 100
        nivel_curs = nivel_nou
        depr_total = ((1 + b["depreciere_leu_%"] / 100) * (1 + depr_supl / 100) - 1) * 100
        e_an = PONDERE_VALUTA * depr_total / 100

        r_an = (b["rata_dobanda_%"] + soc_r[an]) / 100
        interes = r_an * d * (1 + e_an) / (1 + g_an)
        deficit = interes - sold_primar
        ajustare_valutara = e_an * d / (1 + g_an)
        d_nou = (d * (1 + r_an) * (1 + e_an) / (1 + g_an) - sold_primar
                 + b["ajustare_stoc_flux_%pib"])

        rand.append({
            "an": an, "scenariu": nume_soc,
            "crestere_nominala_%": g_an * 100,
            "pierdere_crestere_reala_pp": delta_g,
            "decalaj_productie_%": gap,
            "pib_sub_s2_%": -nivel_pib,
            "somaj_supl_pp": delta_u,
            "rata_somaj_%": SOMAJ_2026 + delta_u,
            "someri_supl_mii": someri_supl_mii,
            "cost_indemnizatii_%pib": cost_somaj,
            "efect_ciclic_buget_%pib": ciclic,
            "eroziune_baza_%pib": -erodare,
            "isd_lipsa_%pib": isd_lipsa,
            "curs_peste_baza_%": nivel_curs,
            "rata_dobanda_%": r_an * 100,
            "sold_primar_%pib": sold_primar,
            "interes_%pib": interes,
            "deficit_esa_%pib": deficit,
            "ajustare_valutara_%pib": ajustare_valutara,
            "datorie_%pib": d_nou,
        })
        d = d_nou
    return pd.DataFrame(rand)

def toate(baza=None):
    if baza is None:
        baza = _baza_s2()
    return pd.concat([ruleaza(n, baza) for n in SOC], ignore_index=True)

def descompunere(nume_soc, baza=None, an=2035):
    """Contribuția fiecărui canal la datoria din `an` față de S2 (pp din PIB),
    adăugând canalele pe rând: creștere + ciclu (inclusiv șomaj), eroziunea bazei
    fiscale, ISD → curs, prima de risc."""
    if baza is None:
        baza = _baza_s2()
    p = SOC[nume_soc]
    gol = {"pot": {}, "gap": {}, "isd": {}, "prima": 0.0}
    pasi = [
        ("Creștere și ciclu (inclusiv șomaj)", dict(gol, pot=p["pot"], gap=p["gap"]), 0.0),
        ("Eroziunea bazei fiscale", dict(gol, pot=p["pot"], gap=p["gap"]), EROZIUNE_BAZA),
        ("ISD mai mici → curs", dict(gol, pot=p["pot"], gap=p["gap"], isd=p["isd"]), EROZIUNE_BAZA),
        ("Prima de risc", p, EROZIUNE_BAZA),
    ]
    rez, prec = {}, baza.loc[an, "datorie_%pib"]
    for eticheta, pp, eroz in pasi:
        d = ruleaza(nume_soc, baza, eroziune=eroz, p=pp).set_index("an").loc[an, "datorie_%pib"]
        rez[eticheta] = d - prec
        prec = d
    rez["Total față de S2"] = prec - baza.loc[an, "datorie_%pib"]
    return pd.Series(rez)

def sensibilitate(baza=None, an=2035):
    """Datoria din `an` după eroziunea bazei fiscale și fracția închisă prin curs."""
    if baza is None:
        baza = _baza_s2()
    rez = {}
    for n in SOC:
        cheie = n.split(" ", 1)[0]
        rez[cheie] = {
            **{f"eroziune {k:g}": ruleaza(n, baza, eroziune=k).set_index("an").loc[an, "datorie_%pib"]
               for k in (0.0, 0.1, 0.2)},
            **{f"curs {k:g}": ruleaza(n, baza, pondere_curs=k).set_index("an").loc[an, "datorie_%pib"]
               for k in (0.0, 1.0)},
        }
    return pd.DataFrame(rez).T

# ---------------------------------------------------------------------------
# 4. RULARE + GRAFICE
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    baza = _baza_s2()
    tab = toate(baza)
    tab.to_csv(os.path.join(OUT, "dezindustrializare.csv"), index=False,
               encoding="utf-8-sig")

    # verificare: D0 reproduce S2
    d0 = tab[tab["scenariu"].str.startswith("D0")].set_index("an")["datorie_%pib"]
    abatere = (d0 - baza["datorie_%pib"]).abs().max()
    print(f"Verificare D0 = S2: abatere maximă {abatere:.2e} pp")

    ani_af = [2027, 2028, 2030, 2032, 2035, 2040]
    for col, titlu in [("datorie_%pib", "Datoria publică (% din PIB)"),
                       ("deficit_esa_%pib", "Deficitul ESA (% din PIB)"),
                       ("rata_somaj_%", "Rata șomajului estimată (%)"),
                       ("pib_sub_s2_%", "PIB sub S2 (%, nivel)"),
                       ("curs_peste_baza_%", "Leul față de S2 (%, nivel)"),
                       ("eroziune_baza_%pib", "Eroziunea bazei fiscale (% din PIB)"),
                       ("cost_indemnizatii_%pib", "Cost indemnizații șomaj (% din PIB)")]:
        print(f"\n=== {titlu} ===")
        pv = tab.pivot(index="an", columns="scenariu", values=col).loc[ani_af]
        print(pv.to_string(float_format=lambda x: f"{x:7.3f}"))

    sens = sensibilitate(baza)
    sens.to_csv(os.path.join(OUT, "dezindustrializare_sensibilitate.csv"),
                encoding="utf-8-sig")
    print("\n=== Datoria 2035: sensibilitate (eroziune bază fiscală / fracție prin curs) ===")
    print(sens.to_string(float_format=lambda x: f"{x:6.2f}"))

    desc = pd.DataFrame({n.split(" ", 1)[0]: descompunere(n, baza) for n in SOC if not n.startswith("D0")})
    desc.to_csv(os.path.join(OUT, "dezindustrializare_canale.csv"), encoding="utf-8-sig")
    print("\n=== Datoria 2035 peste S2, pe canale (pp din PIB) ===")
    print(desc.to_string(float_format=lambda x: f"{x:6.2f}"))

    # grafice
    plt.rcParams.update({"font.size": 10, "axes.grid": True,
                         "grid.alpha": 0.3, "figure.dpi": 130})
    culori = ["#1f6f2f", "#1f77b4", "#e07b00", "#b22222"]
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    panouri = [
        (axes[0, 0], "datorie_%pib", "Datoria publică (% din PIB)", 60, "60% din PIB"),
        (axes[0, 1], "deficit_esa_%pib", "Deficitul bugetar ESA (% din PIB)", 3, "ținta 3%"),
        (axes[1, 0], "rata_somaj_%", "Rata șomajului estimată (%; 6,4% în aug. 2026)", None, None),
        (axes[1, 1], "pib_sub_s2_%", "PIB sub S2 (%, linie) și leul față de S2 (%, punctat)", None, None),
    ]
    for ax, col, titlu, prag, eticheta in panouri:
        for i, nume in enumerate(SOC):
            df = tab[tab["scenariu"] == nume]
            ax.plot(df["an"], df[col], marker="o", ms=3, lw=2,
                    label=nume.split(" ", 1)[0], color=culori[i])
        if prag is not None:
            ax.axhline(prag, color="black", ls="--", lw=1, label=eticheta)
        ax.set_title(titlu)
        ax.set_xlabel("An")
        ax.legend(fontsize=7.5)
    ax2 = axes[1, 1].twinx()
    for i, nume in enumerate(SOC):
        df = tab[tab["scenariu"] == nume]
        ax2.plot(df["an"], df["curs_peste_baza_%"], ls=":", lw=1.6, color=culori[i])
    ax2.set_ylabel("% depreciere peste S2 (nivel)")
    ax2.grid(False)
    fig.suptitle("Șomaj în creștere și retragerea investitorilor străini: efectul asupra "
                 "datoriei (plecând de la scenariul S2)", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig11_dezindustrializare.png"))
    plt.close(fig)
    print("\nGata. Figura:", os.path.join(FIG, "fig11_dezindustrializare.png"))
