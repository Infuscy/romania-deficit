# -*- coding: utf-8 -*-
"""
Spațiul fiscal pentru cheltuieli discreționare în 2027–2030: cât pot da primăriilor și
firmelor un guvern PSD fără ca deficitul să înceapă din nou să crească
=====================================================================================
Întrebarea: măsurile de consolidare din 2025–2026 (guvernul Bolojan: TVA, accize, CASS,
impozite pe proprietate, suprataxarea băncilor, înghețarea salariilor și a punctului de
pensie) rămân în vigoare. Cât pot adăuga, peste ele, transferurile către primării
(programul Anghel Saligny, alocările din Fondul de rezervă) și ajutoarele pentru firme
înainte ca deficitul să crească din nou?

Patru traiectorii de bază (deficit ESA, % din PIB; 2026 = ținta de 6,0% în toate):
  B1 Doar măsurile Bolojan, varianta CF din ianuarie 2026 (= S1): din 2027, deficitul
     primar rămâne la 2,3% din PIB (structura bugetară de la finalul lui 2026; Opinia CF
     2026). Nicio măsură nouă: deficitul total urcă odată cu dobânzile.
  B2 Doar măsurile Bolojan, varianta CF din septembrie 2026: deficit de ~5,5% în 2027
     (CF: „realist”, cu salariile și pensiile crescând cel mult cât PIB-ul), apoi soldul
     primar rămâne la nivelul din 2027.
  B3 Programul de guvernare Niculescu (= S2): 5,2% în 2027, 4,2% în 2028, 3,2% în 2029,
     2,8% în 2030. Față de B1/B2 cere măsuri noi, încă nespecificate.
  B4 Programul cu taxe înghețate și pensii indexate (= S7): 5,5% în 2027, apoi panta S2.

Variantele de pensii și salarii bugetare (indexare după formulă, pensii +12%, salarii
+10%) sunt tratate tot ca o cheltuială permanentă: costul peste creșterea PIB-ului nominal
din 2027 (§7 din cod).

Cheltuielile suplimentare E (pp din PIB) se adaugă peste efortul primar al bazei: soldul
primar scade cu E, iar dobânzile la datoria suplimentară trec în deficit. Feedback macro cu
metoda CE/CF din model_macro_feedback: fiecare modificare a lui E deschide un decalaj de
producție m·ΔE care se închide în 3 ani; creșterea nominală urmează decalajul, iar soldul
bugetar recuperează ε·decalaj (m = 0,75, ε = 0,32: ~24% din cheltuială revine la buget în
primul an, apoi efectul dispare). Retragerea cheltuielilor (E scade) lucrează invers.
Varianta cu primă de risc urcă randamentele pieței cu 50 pb din 2027 (ca S7 + 50 pb).
Fără cheltuieli suplimentare, B1 reproduce exact S1, iar B3 reproduce exact S2.

Contabilitate (ESA 2010): transferurile de la bugetul de stat la bugetele locale sunt în
interiorul administrației publice; deficitul crește când primăriile cheltuie banii
(lucrări executate). Plata restanțelor pentru lucrări deja executate (ex. cele 2,3 mld. lei
din Anghel Saligny) nu schimbă deficitul ESA, care le-a înregistrat la executare, dar
crește deficitul cash și datoria (datoriile comerciale nu intră în datoria Maastricht).
Garanțiile de stat pentru firme intră în deficit doar când sunt executate.

Surse (vezi Raport_spatiu_fiscal_2027-2030.md):
- Consiliul Fiscal, Opinia privind bugetul 2026 (scenariul no-policy change, OUG 89/2025)
- Consiliul UE, ST 11135/26 (rate maxime de creștere a cheltuielilor nete, evaluarea CE)
- Programul de guvernare Niculescu (15 oct. 2026), condițiile PSD; MDLPA (Anghel Saligny)
- _research/stiri_2026-10-16.md (CF: deficit realist de 5,5% în 2027)
"""

import os
from functools import lru_cache
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from model_dsa import (ANI, DATORIE_PIB, PIB_NOMINAL, DEFICIT_S2, ruleaza_dsa, scenarii,
                       crestere_nominala_pib, rata_dobanda, randament_piata, depreciere_leu)
from model_macro_feedback import M_OFICIAL, EPS_OFICIAL, decalaj

OUT = os.path.join(os.path.dirname(__file__), "outputs")
FIG = os.path.join(os.path.dirname(__file__), "figuri")
os.makedirs(OUT, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. PARAMETRI
# ---------------------------------------------------------------------------
DEFICIT_2026 = DEFICIT_S2[2026]   # 6,0% ESA: ținta din 2026, punctul de plecare comun
# Consiliul Fiscal, sept. 2026 (Raportul anual 2025, declarațiile lui Dăianu): deficitul
# realist din 2027 este ~5,5% din PIB, dacă salariile și pensiile nu cresc mai repede
# decât PIB-ul (_research/stiri_2026-10-16.md, §5).
DEFICIT_CF_2027 = 5.5
PRIMA_RISC = 0.5                  # pp pe randamentele pieței din 2027, ca în S7 + 50 pb
PRAG_PDE = 3.0                    # pragul din tratat pentru deficit (% din PIB)
AN_START = 2027                   # primul buget al noului guvern

# Regula de cheltuieli din PDE (Consiliul UE, recomandarea din 8 iul. 2025, reluată în
# ST 11135/26, considerentul 7): rate maxime de creștere a cheltuielilor nete (cheltuieli
# primare finanțate național, fără componenta ciclică a șomajului, după efectul măsurilor
# discreționare de venituri), anual și cumulat față de 2024.
PLAFON_ANUAL = {2025: 2.8, 2026: 2.6, 2027: 4.6, 2028: 4.4, 2029: 4.2, 2030: 4.0}
PLAFON_CUMULAT = {2025: 2.8, 2026: 5.5, 2027: 10.4, 2028: 15.2, 2029: 20.1, 2030: 24.9}
# Evaluarea CE (prognoza de primăvară 2026, ST 11135/26, considerentele 16-17): +0,5% în
# 2025, +1,8% în 2026, +2,3% cumulat.
CRESTERE_CHELT_NETE_CE = {2025: 0.5, 2026: 1.8}
CRESTERE_CUMULATA_CE_2026 = 2.3
# Cheltuielile nete ca pondere în PIB (estimare proprie): cheltuieli totale 2025 = 42,4%
# din PIB (cash, MF), minus dobânzi 2,6%, minus plățile din fonduri UE și PNRR (78,55 mld.
# lei = 4,1% din PIB) ≈ 35,7%; 2026: 42,3% − 3,1% − 4,8% ≈ 34,4%. Rotunjit: 35%.
CHELT_NETE_PIB = 35.0

ETICHETE_BAZE = {
    "B1": "B1 Doar măsurile Bolojan (CF, ian. 2026: deficit primar 2,3%)",
    "B2": "B2 Doar măsurile Bolojan (CF, sept. 2026: deficit 5,5% în 2027)",
    "B3": "B3 Programul de guvernare (S2: 5,2% în 2027)",
    "B4": "B4 Program cu taxe înghețate și pensii indexate (S7: 5,5% în 2027)",
}

# Pachete tipice (pp din PIB pe an), PESTE cheltuielile din 2026. Anghel Saligny
# decontează deja ~10-11 mld. lei pe an (31,0 mld. lei decontați la 30 iun. 2026, față de
# 19,6 mld. la 30 iun. 2025; 10 mld. lei alocați în 2025, 9 mld. în 2026), deci ritmul
# actual este în bază. Repere pentru cheltuieli noi: 1.159 de contracte Saligny nesemnate,
# de ~11,25 mld. lei (sept. 2026); alocări din Fondul de rezervă către primării de ~16,3
# mld. lei sub guvernul Ciolacu (iun. 2023–iun. 2025, ~8 mld. lei/an).
PACHETE = {
    "Mic (0,25 pp ≈ 5,5 mld. lei/an)": 0.25,
    "Mediu (0,5 pp ≈ 11 mld. lei/an)": 0.50,
    "Mare (1,0 pp ≈ 22 mld. lei/an), ca în 2023–2024": 1.00,
}

# Pensii și salarii bugetare în 2027. Costul se măsoară peste o creștere cât PIB-ul nominal
# (6,5% în 2027 în S2): CF consideră deficitul de 5,5% (B2) realist doar dacă pensiile și
# salariile nu cresc mai repede decât PIB-ul. Majorarea rămâne în nivel, deci costul ca
# pondere în PIB este permanent.
# - Pensiile publice: 154,7 mld. lei în 2026 (7,6% din PIB, proiectul legii BASS 2026,
#   economica.net, 10 mart. 2026), deci 1 pp de indexare a tuturor pensiilor ≈ 1,55 mld.
#   lei pe an. Monitorul Fiscal (aug.–sept. 2026): formula din Legea 360/2023 dă ~7,3%,
#   iar o indexare de 12% ar costa ~12 mld. lei în plus pe an, adică ~1,0 mld. lei pe pp.
#   Folosim intervalul 1,0–1,55.
# - Cheltuielile de personal: 8,2% din PIB în 2026 (Opinia CF 2026).
COST_PP_INDEXARE_PENSII = (1.0, 1.55)   # mld. lei pe an pentru 1 pp de indexare
INDEXARE_FORMULA_2027 = 7.3             # %, formula din Legea 360/2023 (Monitorul Fiscal)
CHELT_PERSONAL_PIB = 8.2                # % din PIB, 2026
VARIANTE_PENSII_SALARII = {             # nume -> (creștere pensii %, creștere salarii %)
    "Pensii indexate după formulă (7,3%)": (INDEXARE_FORMULA_2027, None),
    "Pensii +12%": (12.0, None),
    "Salarii bugetare +10%": (None, 10.0),
    "Pensii +12% și salarii bugetare +10%": (12.0, 10.0),
}

# ---------------------------------------------------------------------------
# 2. MOTORUL
# ---------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _scenarii():
    return scenarii()

@lru_cache(maxsize=None)
def _sold_primar_baza(baza):
    S = _scenarii()
    s2 = S["S2 Consolidare conform planului (PDE)"].set_index("an")
    if baza == "B3":
        return tuple(s2["sold_primar_%pib"].items())
    if baza == "B4":
        s7 = S["S7 Buget 2027 relaxat: taxe înghețate, pensii indexate"].set_index("an")
        return tuple(s7["sold_primar_%pib"].items())
    s1 = S["S1 Nicio schimbare de politică (no-policy change)"]
    pb = dict(zip(s1["an"], s1["sold_primar_%pib"]))
    if baza == "B2":
        # dobânzile din 2027 sunt aceleași în toate bazele (datoria din 2026 e aceeași)
        pb27 = s2.loc[2027, "interes_%pib"] - DEFICIT_CF_2027
        pb = {an: (v if an < 2027 else pb27) for an, v in pb.items()}
    return tuple(pb.items())

def sold_primar_baza(baza):
    """Soldul primar al bazei (pp din PIB), an -> valoare."""
    return dict(_sold_primar_baza(baza))

def ruleaza(baza="B3", cheltuieli=None, m=M_OFICIAL, eps=EPS_OFICIAL, prima=0.0):
    """Traseul datoriei cu cheltuieli suplimentare `cheltuieli` (an -> pp din PIB) peste
    efortul primar al bazei. `prima` = pp adăugate randamentelor pieței din 2027."""
    E = {an: (cheltuieli or {}).get(an, 0.0) for an in ANI}
    pb0 = sold_primar_baza(baza)
    g0 = crestere_nominala_pib()
    impuls = {an: m * (E[an] - E.get(an - 1, 0.0)) for an in ANI}
    gap = decalaj(impuls, ANI)            # pozitiv = PIB peste traiectoria bazei
    g = {an: g0[an] + gap[an] - gap.get(an - 1, 0.0) for an in ANI}
    pb = {an: pb0[an] - E[an] + eps * gap[an] for an in ANI}
    r = rata_dobanda(piata=randament_piata(delta=prima))
    df = ruleaza_dsa(DATORIE_PIB[2025], {an: (lambda a, i: i - pb[a]) for an in ANI},
                     r, g, PIB_NOMINAL[2025], ANI, depreciere_leu())
    df["cheltuieli_supl_%pib"] = [E[an] for an in ANI]
    df["cheltuieli_supl_mld_lei"] = df["cheltuieli_supl_%pib"] / 100 * df["pib_mld"]
    df["decalaj_pib_pp"] = [gap[an] for an in ANI]
    return df

def profil(tip, nivel):
    """`permanent`: E = nivel din 2027 încolo (program recurent, ca Anghel Saligny sau
    alocările anuale din Fondul de rezervă). `electoral`: E = nivel în 2027 și 2028 (anul
    alegerilor locale și parlamentare), retras complet din 2029."""
    if tip == "permanent":
        return {an: nivel for an in ANI if an >= AN_START}
    if tip == "electoral":
        return {2027: nivel, 2028: nivel}
    raise ValueError(tip)

def _mld(pp, an):
    """pp din PIB -> mld. lei, pe PIB-ul din S2."""
    pib = _scenarii()["S2 Consolidare conform planului (PDE)"].set_index("an")["pib_mld"]
    return pp / 100 * pib[an]

# ---------------------------------------------------------------------------
# 3. CE LASĂ MĂSURILE BOLOJAN, AN DE AN
# ---------------------------------------------------------------------------
def tabel_baze(ani=range(2027, 2032)):
    """Pentru fiecare bază: deficitul, cât spațiu rămâne ca deficitul să nu crească față
    de anul precedent sau față de 2026 (negativ = măsuri noi necesare), și cât cere
    programul (B3) peste măsurile Bolojan (diferența de sold primar)."""
    rand = []
    pb3 = sold_primar_baza("B3")
    for baza in ("B1", "B2", "B3"):
        x = ruleaza(baza).set_index("an")
        pb = sold_primar_baza(baza)
        for an in ani:
            d, d_ant = x.loc[an, "deficit_esa_%pib"], x.loc[an - 1, "deficit_esa_%pib"]
            rand.append({
                "baza": ETICHETE_BAZE[baza], "an": an,
                "deficit_esa_%pib": d,
                "variatie_deficit_pp": d - d_ant,
                "variatie_dobanzi_pp": x.loc[an, "interes_%pib"] - x.loc[an - 1, "interes_%pib"],
                "spatiu_fata_de_anul_anterior_pp": d_ant - d,
                "spatiu_fata_de_anul_anterior_mld": _mld(d_ant - d, an),
                "spatiu_fata_de_2026_pp": DEFICIT_2026 - d,
                "spatiu_fata_de_2026_mld": _mld(DEFICIT_2026 - d, an),
                "masuri_noi_cerute_de_program_pp": pb3[an] - pb[an],
                "masuri_noi_cerute_de_program_mld": _mld(pb3[an] - pb[an], an),
                "datorie_%pib": x.loc[an, "datorie_%pib"],
            })
    return pd.DataFrame(rand)

# ---------------------------------------------------------------------------
# 4. SPAȚIUL MAXIM, PE CRITERII
# ---------------------------------------------------------------------------
def _k1(df):
    d = df.set_index("an")["deficit_esa_%pib"]
    return all(d[an] <= d[an - 1] + 1e-9 for an in range(2027, 2031))

def _k2(df):
    return df.set_index("an").loc[2030, "deficit_esa_%pib"] <= PRAG_PDE

def _k3(df):
    d = df.set_index("an")["datorie_%pib"]
    return all(d[an] < d[an - 1] for an in range(2031, 2041))

def _k4(df):
    d = df.set_index("an")["deficit_esa_%pib"]
    return all(d[an] <= DEFICIT_S2[an] + 1e-9 for an in range(2027, 2031))

CRITERII = {
    "K0 Țintele de deficit din program (5,2/4,2/3,2/2,8%)": _k4,
    "K1 Deficitul nu crește de la un an la altul (2027–2030)": _k1,
    "K2 Deficit sub 3% în 2030 (PDE închisă la termen)": _k2,
    "K3 Datoria scade în fiecare an din 2031 până în 2040": _k3,
}

def spatiu_maxim(criteriu, baza="B3", tip="permanent", prima=0.0,
                 lo=None, hi=6.0, tol=1e-4):
    """Cel mai mare nivel E (pp din PIB pe an, profilul `tip`) pentru care criteriul
    este îndeplinit; negativ = măsuri noi necesare. NaN dacă nici lo nu îl îndeplinește;
    hi dacă nici hi nu îl încalcă (criteriul nu limitează). Profilul electoral se caută
    doar de la 0: măsuri temporare retrase în 2029 nu sunt monotone în criterii."""
    if lo is None:
        lo = 0.0 if tip == "electoral" else -6.0
    def ok(L):
        return criteriu(ruleaza(baza, profil(tip, L), prima=prima))
    if not ok(lo):
        return np.nan
    if ok(hi):
        return hi
    while hi - lo > tol:
        mij = (lo + hi) / 2
        lo, hi = (mij, hi) if ok(mij) else (lo, mij)
    return lo

def tabel_spatiu_maxim():
    rand = []
    for baza in ("B3", "B4", "B2", "B1"):
        for tip in ("permanent", "electoral"):
            for nume, k in CRITERII.items():
                # Pe B1/B2 deficitul crește oricum din 2028 (dobânzi): un nivel constant de
                # măsuri nu oprește creșterea (K1), iar măsurile temporare nu închid PDE.
                # Acolo rezultatul este doar volumul de măsuri permanente necesare.
                if baza in ("B1", "B2") and (nume[:2] in ("K0", "K1") or tip == "electoral"):
                    continue
                if baza == "B4" and nume[:2] == "K0":
                    continue
                L = spatiu_maxim(k, baza, tip)
                rand.append({"baza": ETICHETE_BAZE[baza], "profil": tip, "criteriu": nume,
                             "spatiu_pp_pib": L, "spatiu_mld_lei_2027": _mld(L, 2027),
                             "spatiu_mld_lei_2028": _mld(L, 2028)})
    return pd.DataFrame(rand)

# ---------------------------------------------------------------------------
# 5. PACHETE TIPICE PESTE PROGRAM
# ---------------------------------------------------------------------------
def an_inchidere_pde(df):
    """Primul an din care deficitul rămâne sub 3% până în 2040."""
    d = df.set_index("an")["deficit_esa_%pib"]
    for an in d.index:
        if an >= 2027 and (d.loc[an:] < PRAG_PDE).all():
            return an
    return None

def rezumat(df, eticheta):
    x = df.set_index("an")
    varf = x["datorie_%pib"].idxmax()
    sub60 = x.index[(x["datorie_%pib"] < 60) & (x.index > varf)]
    return {
        "varianta": eticheta,
        "cheltuieli_2027_mld": x.loc[2027, "cheltuieli_supl_mld_lei"],
        "cheltuieli_2027_2030_mld": x.loc[2027:2030, "cheltuieli_supl_mld_lei"].sum(),
        "deficit_2027": x.loc[2027, "deficit_esa_%pib"],
        "deficit_2028": x.loc[2028, "deficit_esa_%pib"],
        "deficit_2030": x.loc[2030, "deficit_esa_%pib"],
        "inchidere_pde": an_inchidere_pde(df),
        "varf_datorie": x["datorie_%pib"].max(), "an_varf": varf,
        "datorie_2030": x.loc[2030, "datorie_%pib"],
        "datorie_2035": x.loc[2035, "datorie_%pib"],
        "datorie_2040": x.loc[2040, "datorie_%pib"],
        "sub_60_din": sub60[0] if len(sub60) else None,
        "dobanzi_2035_%pib": x.loc[2035, "interes_%pib"],
    }

def tabel_pachete():
    """Pachetele peste program (B3), plus pachetul mediu permanent peste S7 (B4) și peste
    măsurile Bolojan fără nimic nou (B2)."""
    def rz(baza, df, et):
        return {"baza": baza, **rezumat(df, et)}
    rand = [rz("B3", ruleaza("B3"), "fără cheltuieli suplimentare")]
    for nume, L in PACHETE.items():
        for tip, et in (("electoral", "2027–2028, retras din 2029"), ("permanent", "permanent")):
            rand.append(rz("B3", ruleaza("B3", profil(tip, L)), f"{nume}; {et}"))
    nume, L = list(PACHETE.items())[-1]
    rand.append(rz("B3", ruleaza("B3", profil("permanent", L), prima=PRIMA_RISC),
                   f"{nume}; permanent, randamente +50 pb"))
    nume, L = list(PACHETE.items())[1]
    for baza in ("B4", "B2"):
        rand.append(rz(baza, ruleaza(baza), "fără cheltuieli suplimentare"))
        rand.append(rz(baza, ruleaza(baza, profil("permanent", L)), f"{nume}; permanent"))
    return pd.DataFrame(rand)

# ---------------------------------------------------------------------------
# 6. REGULA DE CHELTUIELI A UE
# ---------------------------------------------------------------------------
def marja_regula_cheltuieli():
    """Cât de mult ar putea crește cheltuielile nete în 2027 peste plafonul anual de 4,6%
    fără să depășească plafonul cumulat (față de 2024), dacă 2026 se încheie cum a
    proiectat CE (+2,3% cumulat). Rezultat în pp din PIB 2027 și mld. lei (estimare)."""
    crestere_permisa_2027 = ((1 + PLAFON_CUMULAT[2027] / 100)
                             / (1 + CRESTERE_CUMULATA_CE_2026 / 100) - 1) * 100
    marja_pct = crestere_permisa_2027 - PLAFON_ANUAL[2027]       # % din cheltuielile nete 2026
    S2 = _scenarii()["S2 Consolidare conform planului (PDE)"].set_index("an")
    mld = marja_pct / 100 * CHELT_NETE_PIB / 100 * S2.loc[2026, "pib_mld"]
    return {"crestere_permisa_2027_%": crestere_permisa_2027,
            "marja_%_din_cheltuieli_nete": marja_pct,
            "marja_mld_lei": mld, "marja_pp_pib_2027": mld / S2.loc[2027, "pib_mld"] * 100}

# ---------------------------------------------------------------------------
# 7. PENSII ȘI SALARII BUGETARE
# ---------------------------------------------------------------------------
def cost_pensii_salarii(pensii=None, salarii=None, cost_pp=COST_PP_INDEXARE_PENSII[0]):
    """Costul permanent (pp din PIB) al unei creșteri a pensiilor și/sau a salariilor
    bugetare în 2027 peste creșterea PIB-ului nominal. `pensii`, `salarii` în %;
    `cost_pp` = mld. lei pe an pentru 1 pp de indexare a pensiilor."""
    g27 = crestere_nominala_pib()[2027]
    pib27 = _scenarii()["S2 Consolidare conform planului (PDE)"].set_index("an").loc[2027, "pib_mld"]
    cost = 0.0
    if pensii is not None:
        cost += (pensii - g27) * cost_pp / pib27 * 100
    if salarii is not None:
        cost += (salarii - g27) * CHELT_PERSONAL_PIB / 100
    return cost

def tabel_pensii_salarii():
    """Variantele de pensii și salarii, ca cheltuială permanentă din 2027 peste B2 (doar
    măsurile Bolojan) și B3 (programul), la ambele capete ale costului de indexare."""
    rand = []
    for nume, (p, s) in VARIANTE_PENSII_SALARII.items():
        # costul salariilor nu depinde de costul indexării pensiilor
        costuri = COST_PP_INDEXARE_PENSII if p is not None else COST_PP_INDEXARE_PENSII[:1]
        for cost_pp in costuri:
            E = cost_pensii_salarii(p, s, cost_pp)
            for baza in ("B2", "B3"):
                df = ruleaza(baza, profil("permanent", E))
                rand.append({"baza": ETICHETE_BAZE[baza], "cost_pp_indexare_mld": cost_pp,
                             "cost_pp_pib": E, **rezumat(df, nume)})
    return pd.DataFrame(rand)

# ---------------------------------------------------------------------------
# 8. GRAFICE
# ---------------------------------------------------------------------------
def grafic():
    plt.rcParams.update({"font.size": 10, "axes.grid": True,
                         "grid.alpha": 0.3, "figure.dpi": 130})
    L = list(PACHETE.values())[-1]
    linii = [
        ("B1 Doar Bolojan (CF, ian. 2026)", ruleaza("B1"), "#b22222", "-"),
        ("B2 Doar Bolojan (CF, sept. 2026)", ruleaza("B2"), "#e07b00", "-"),
        ("B3 Programul (S2)", ruleaza("B3"), "#1f6f2f", "-"),
        ("B3 + pachet mare (1 pp), 2027–2028", ruleaza("B3", profil("electoral", L)),
         "#6a3d9a", "--"),
        ("B3 + pachet mare (1 pp), permanent", ruleaza("B3", profil("permanent", L)),
         "#8c564b", "--"),
    ]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.4))
    for et, df, c, ls in linii:
        x = df[df["an"] <= 2035]
        ax1.plot(x["an"], x["deficit_esa_%pib"], color=c, ls=ls, lw=2, marker="o", ms=3,
                 label=et)
        ax2.plot(x["an"], x["datorie_%pib"], color=c, ls=ls, lw=2, marker="o", ms=3)
    ax1.axhline(PRAG_PDE, color="black", ls=":", lw=1)
    ax1.axhline(DEFICIT_2026, color="gray", ls=":", lw=1)
    ax1.annotate("pragul de 3%", (2033.2, 2.75), fontsize=8)
    ax1.annotate("nivelul din 2026 (6,0%)", (2031.0, 5.75), fontsize=8, color="gray")
    ax1.set_title("Deficit ESA (% din PIB)")
    ax2.axhline(60, color="black", ls=":", lw=1)
    ax2.set_title("Datoria publică (% din PIB)")
    for ax in (ax1, ax2):
        ax.set_xlabel("An")
    fig.legend(*ax1.get_legend_handles_labels(), loc="lower center", ncol=3, fontsize=8,
               frameon=False)
    fig.suptitle("Cheltuieli suplimentare pentru primării și firme peste măsurile Bolojan")
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(os.path.join(FIG, "fig12_spatiu_fiscal.png"))
    plt.close(fig)

# Deficitul ESA istoric din grafic: 2024 = 9,3% și 2025 = 7,9% (Eurostat, aprilie 2026, pe
# PIB-ul provizoriu; 7,8% pe PIB-ul semidefinitiv din oct. 2026, folosit în model).
DEFICIT_ISTORIC_GRAFIC = {2024: 9.3, 2025: 7.9}

def grafic_simplu(cale=os.path.join(FIG, "fig13_spatiu_fiscal_simplu.png"), pana_la=2032):
    """Varianta pentru public a figurii 12: doar deficitul, trei trasee (programul B3,
    doar măsurile Bolojan B2, programul + pachetul mare permanent), cu etichete directe."""
    ani = list(range(2026, pana_la + 1))
    def serie(df):
        x = df.set_index("an")["deficit_esa_%pib"]
        return [x[a] for a in ani]
    plan, bolojan = serie(ruleaza("B3")), serie(ruleaza("B2"))
    pachet = serie(ruleaza("B3", profil("permanent", list(PACHETE.values())[-1])))
    ist_ani = sorted(DEFICIT_ISTORIC_GRAFIC) + [2026]
    ist = [DEFICIT_ISTORIC_GRAFIC[a] for a in ist_ani[:-1]] + [DEFICIT_2026]

    FUNDAL, TEXT, TEXT2, ESTOMPAT, GRILA = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
    ALBASTRU, PORTOCALIU, GRI = "#2a78d6", "#eb6834", "#8a8984"
    fmt = lambda v: f"{v:.1f}%".replace(".", ",")
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 15, "axes.grid": False}):
        fig, ax = plt.subplots(figsize=(12, 9), dpi=100)
        fig.patch.set_facecolor(FUNDAL)
        ax.set_facecolor(FUNDAL)
        ax.axvspan(2027.5, 2028.5, color="#efeee9", zorder=0)
        ax.text(2028, 9.55, "Alegeri locale\nși parlamentare", ha="center", va="top",
                fontsize=13, color=TEXT2, zorder=1)
        ax.axhline(PRAG_PDE, color=TEXT2, lw=1, ls=(0, (4, 3)), zorder=1)
        ax.text(pana_la + 0.35, PRAG_PDE + 0.08, "Pragul UE: 3%", ha="right", va="bottom",
                fontsize=13, color=TEXT2)
        ax.plot(ist_ani, ist, color=TEXT, lw=3, marker="o", ms=9, zorder=4,
                markeredgecolor=FUNDAL, markeredgewidth=2)
        for a in ist_ani[:-1]:
            ax.text(a + 0.12, DEFICIT_ISTORIC_GRAFIC[a] + 0.08, f"{fmt(DEFICIT_ISTORIC_GRAFIC[a])}\n({a})",
                    fontsize=13, color=TEXT, va="bottom")
        ax.text(2025.85, DEFICIT_2026 - 0.15, f"{fmt(DEFICIT_2026)}\n(ținta 2026)", fontsize=13,
                color=TEXT, ha="right", va="top")
        for y, c, ls, et in (
                (plan, GRI, (0, (5, 3)), "Planul guvernului"),
                (bolojan, ALBASTRU, "-", "Doar măsurile Bolojan, nimic nou"),
                (pachet, PORTOCALIU, "-", "Planul + 22 mld. lei/an pentru primari și firme")):
            ax.plot(ani, y, color=c, lw=3, ls=ls, marker="o", ms=8, zorder=3, label=et,
                    markeredgecolor=FUNDAL, markeredgewidth=2)
        x_et = pana_la + 0.25
        ax.text(x_et, bolojan[-1], fmt(bolojan[-1]) + "\ncrește din nou", color=TEXT,
                fontsize=14, va="center", fontweight="bold")
        ax.text(x_et, pachet[-1], fmt(pachet[-1]) + "\nrămâne peste 3%", color=TEXT,
                fontsize=14, va="center", fontweight="bold")
        ax.text(x_et, plan[-1], fmt(plan[-1]) + "\nplanul", color=TEXT2, fontsize=14, va="center")
        ax.set_xlim(2023.6, pana_la + 1.6)
        ax.set_ylim(1.5, 9.8)
        ax.set_xticks(range(2024, pana_la + 1))
        ax.set_yticks(range(2, 10))
        ax.set_yticklabels([f"{t}%" for t in range(2, 10)])
        ax.tick_params(colors=TEXT2, labelsize=14, length=0)
        ax.grid(axis="y", color=GRILA, lw=1)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(ESTOMPAT)
        leg = ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.86), frameon=False,
                        fontsize=14, handlelength=2.6)
        for t in leg.get_texts():
            t.set_color(TEXT)
        fig.text(0.06, 0.955, "Fără măsuri noi, deficitul o ia din nou în sus", fontsize=26,
                 fontweight="bold", color=TEXT, ha="left")
        fig.text(0.06, 0.915, "Deficitul bugetar, % din PIB (metodologia UE). Din 2027: simulări.",
                 fontsize=15, color=TEXT2, ha="left")
        fig.text(0.06, 0.025, "Surse: Eurostat, Ministerul Finanțelor, Consiliul Fiscal; simulări "
                 "proprii (model de sustenabilitate a datoriei).", fontsize=11.5, color=ESTOMPAT,
                 ha="left")
        fig.subplots_adjust(left=0.08, right=0.9, top=0.88, bottom=0.08)
        fig.savefig(cale, facecolor=FUNDAL)
        plt.close(fig)
    return {"plan": plan, "doar_bolojan": bolojan, "plan_plus_pachet_mare": pachet}

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    fmt = lambda v: f"{v:6.2f}"
    # verificare: fără cheltuieli suplimentare, B1 = S1 și B3 = S2
    S = _scenarii()
    for baza, cheie in (("B1", "S1 Nicio schimbare de politică (no-policy change)"),
                        ("B3", "S2 Consolidare conform planului (PDE)")):
        dif = (ruleaza(baza)["datorie_%pib"] - S[cheie]["datorie_%pib"]).abs().max()
        print(f"Verificare {baza} = {cheie.split()[0]}: diferență maximă datorie {dif:.2e} pp")

    baze = tabel_baze()
    baze.to_csv(os.path.join(OUT, "spatiu_fiscal_baze.csv"), index=False, encoding="utf-8-sig")
    print("\n=== Ce lasă măsurile Bolojan (deficit ESA; spațiu + / măsuri necesare −) ===")
    print(baze.drop(columns=["baza"]).assign(b=baze["baza"].str[:2]).to_string(
        index=False, float_format=fmt))

    maxim = tabel_spatiu_maxim()
    maxim.to_csv(os.path.join(OUT, "spatiu_fiscal_maxim.csv"), index=False, encoding="utf-8-sig")
    print("\n=== Spațiul maxim pe criterii (pp din PIB pe an; negativ = măsuri necesare) ===")
    print(maxim.assign(baza=maxim["baza"].str[:2]).to_string(index=False, float_format=fmt))

    pachete = tabel_pachete()
    pachete.to_csv(os.path.join(OUT, "spatiu_fiscal_pachete.csv"), index=False,
                   encoding="utf-8-sig")
    print("\n=== Pachete tipice (B3 = S2; B4 = S7; B2 = doar măsurile Bolojan) ===")
    print(pachete.to_string(index=False, float_format=fmt))

    print("\n=== Regula de cheltuieli a UE (estimare) ===")
    for k, v in marja_regula_cheltuieli().items():
        print(f"  {k}: {v:.2f}")

    print("\n=== Feedback: fracția din cheltuială care revine la buget în primul an ===")
    print(f"  m·ε = {M_OFICIAL * EPS_OFICIAL:.2f}")

    ps = tabel_pensii_salarii()
    ps.to_csv(os.path.join(OUT, "spatiu_fiscal_pensii_salarii.csv"), index=False,
              encoding="utf-8-sig")
    print("\n=== Pensii și salarii în 2027, peste creșterea PIB (permanent; B2 și B3) ===")
    print(ps[["baza", "varianta", "cost_pp_indexare_mld", "cost_pp_pib", "cheltuieli_2027_mld",
              "deficit_2027", "deficit_2028", "deficit_2030", "inchidere_pde",
              "datorie_2035"]].assign(baza=ps["baza"].str[:2]).to_string(index=False,
                                                                         float_format=fmt))
    grafic()
    trasee = grafic_simplu()
    print("\n=== Figura 13 (deficit ESA 2026–2032) ===")
    for k, v in trasee.items():
        print(f"  {k}: " + " ".join(f"{x:.2f}" for x in v))
    print("\nGata. Figuri:", os.path.join(FIG, "fig12_spatiu_fiscal.png"), "și",
          os.path.join(FIG, "fig13_spatiu_fiscal_simplu.png"))
