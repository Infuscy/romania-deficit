# -*- coding: utf-8 -*-
"""
Model de sustenabilitate a datoriei publice a României (DSA)
==============================================================
Răspunde la întrebarea: „Poate România să plătească deficitul?"

Identitatea de datorie (anuală, % din PIB), cu efectul cursului de schimb
(forma DSA FMI/CE pentru datorie parțial în valută):
    d[t] = d[t-1] * (1 + r[t]) * (1 + a * e[t]) / (1 + g[t]) - pb[t]
unde:
    d  = datoria publică consolidată (% din PIB, ESA)
    r  = rata efectivă a dobânzii plătite pe datorie
    g  = rata de creștere nominală a PIB
    pb = soldul bugetar primar (% din PIB, pozitiv = excedent)
    a  = ponderea datoriei în valută (EUR/USD) în total
    e  = deprecierea anuală a leului față de euro (creșterea cursului EUR/RON)

Dobânzile anului t, ca pondere în PIB-ul anului t: r[t] * d[t-1] * (1 + a*e[t]) / (1 + g[t])
(dobânzile la datoria în valută se plătesc la cursul nou).
Deficitul bugetar (ESA) = dobânzi (% PIB) - sold primar (% PIB). Reevaluarea în lei a
stocului în valută, a * e[t] * d[t-1] / (1 + g[t]), nu trece prin deficit: este o
ajustare stoc-flux. Echivalent: d[t] = d[t-1] / (1 + g[t]) + deficit[t] + ajustare_valutară[t].
De ce contează: inflația din lei umflă PIB-ul nominal și erodează datoria în lei, dar
nu și datoria în valută, dacă leul se depreciază în același ritm.

Surse pentru parametri (vezi raportul, secțiunea „Surse"):
- Consiliul Fiscal, Opinia privind Legea bugetului de stat pe anul 2026 (martie 2026)
- Consiliul UE, Recomandarea revizuită art. 126(7) TFUE, adoptată la 8 iulie 2025 (ST 10349/2025)
- Ministerul Finanțelor, Proiecția serviciului datoriei publice 2025-2034 (date 30.11.2025)
- Ministerul Finanțelor, comunicate execuție bugetară 2025 / 2026 (ultimul: ian.–sep. 2026)
- S&P Global Ratings, evaluarea suverană a României, 2 octombrie 2026
- INS, PIB 2025 (date semidefinitive) și PIB T2 2026, 9 octombrie 2026
- FMI, World Economic Outlook, octombrie 2026; Eurostat, ert_bil_eur_m (cursuri medii lunare)
- Știrile până la 16 oct. 2026: _research/stiri_2026-10-16.md

Autor: analiză proprie (model DSA în stilul metodologiei CE / Bruegel DSA).
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

# ----------------------------------------------------------------------------
# 1. DATE DE PLECARE (istorice)
# ----------------------------------------------------------------------------
# PIB nominal (mld. lei), seria MF din Structura datoriei publice 07.2026;
# 2025: 1.929,9 mld. lei, date INS semidefinitive (9 oct. 2026; provizoriu: 1.916,4;
# creștere reală 0,8%, deflator 108,4%). Comunicatul MF din 26 ian. 2026 (deficit cash
# 7,65%) folosea PIB provizoriu de 1.909 mld. lei; pe PIB-ul semidefinitiv, 146,03 mld.
# lei = 7,6% din PIB. 2024 rămâne în versiunea folosită de Eurostat în aprilie 2026
# (consecventă cu datoria și deficitul din 2024 de mai jos); INS a publicat la 9 oct. și
# datele finale 2024 (creștere reală 1,1%, PIB implicit ~1.766 mld. lei). Reziduul din
# 2025 (verifica_istoric) nu depinde de această revizie: contează doar stocul datoriei
# din 2024 și PIB-ul din 2025.
PIB_NOMINAL = {
    2019: 1059.8, 2020: 1063.7, 2021: 1186.0, 2022: 1384.6,
    2023: 1590.7, 2024: 1759.2, 2025: 1929.9,
}
# Datorie publică consolidată (% din PIB, ESA 2010)
# 2024: 54,8% (Eurostat / Consiliul UE ST 10349/2025)
# 2025: Eurostat (notificarea din aprilie 2026; preluat de Consiliul UE, ST 11135/26,
#       considerentul 13, și de CE): 59,3% pe PIB-ul provizoriu, adică ~1.136 mld. lei;
#       pe PIB-ul semidefinitiv INS (9 oct. 2026): 58,9% (calcul propriu; notificarea
#       Eurostat din 21 oct. 2026 dă cifra oficială). MF raportează 1.138,3 mld. lei
#       (Raport datoria publică 12.2025), adică 59,0% pe PIB-ul semidefinitiv.
DATORIE_PIB = {2019: 35.0, 2023: 48.9, 2024: 54.8, 2025: 58.9}

# Deficit bugetar (% din PIB): cash și ESA
# 2024: cash 8,67% / ESA 9,3% (Eurostat, 22 apr. 2025)
# 2025: cash 7,6% (MF, 146,03 mld. lei pe PIB-ul semidefinitiv) / ESA 7,8% (Eurostat,
#       apr. 2026: 7,9% pe PIB-ul provizoriu, ~151 mld. lei; recalculat pe PIB-ul
#       semidefinitiv)
# 2026: țintă cash 6,2% (127,8 mld. lei; legea bugetului: 6,25% pe PIB-ul de atunci) /
#       ESA 6,0% (Legea bugetului 2026; MF, oct. 2026)
DEFICIT = {
    "cash": {2023: 5.58, 2024: 8.67, 2025: 7.6, 2026: 6.2},
    "esa":  {2023: 6.6,  2024: 9.3,  2025: 7.8,  2026: 6.0},
}

# Dobânzi plătite (% din PIB). 2025: 50,1 mld. lei (MF, cash). 2026: MF a plătit 50,63
# mld. lei în ian.–sep. 2026 (+10,69 mld., +26,8% a/a); cu profilul din 2025 (anul
# întreg = 1,254 × primele 9 luni; la fel după 7 și 8 luni) rezultă ~63,5 mld. lei, adică
# ~3,1% din PIB (estimare proprie; proiecția MF din nov. 2025, 58,4 mld., acoperea doar
# stocul de atunci; CF, Opinia 2026: 3,0%).
INTERES_PIB = {2024: 2.2, 2025: 2.6, 2026: 3.1}
DOBANZI_2026_MLD = 63.5

# Cursul EUR/RON, media anuală (Eurostat, ert_bil_eur_a, actualizat iulie 2026).
# 2005-2025: depreciere medie 1,7%/an (1,9%/an din 2008, 1,3%/an din 2015);
# variații anuale 2006-2024: medie 1,8%, abatere standard 4,5%, maxim +15,1% (2009).
CURS_EUR_RON = {
    2005: 3.6209, 2006: 3.5258, 2007: 3.3353, 2008: 3.6826, 2009: 4.2399,
    2010: 4.2122, 2011: 4.2391, 2012: 4.4593, 2013: 4.4190, 2014: 4.4437,
    2015: 4.4454, 2016: 4.4904, 2017: 4.5688, 2018: 4.6540, 2019: 4.7453,
    2020: 4.8383, 2021: 4.9215, 2022: 4.9313, 2023: 4.9467, 2024: 4.9746,
    2025: 5.0424,
}

# Ponderea datoriei guvernamentale în valută: ~49% (iulie 2026: ~51% lei, ~39% EUR,
# ~10% USD; MF, Raport datoria publică 07.2026, ultimul publicat la 16 oct. 2026).
# Ținută constantă: strategia MF menține ponderea în lei în banda indicativă 45-55%.
# Prefinanțarea SAFE (2,5 mld. €, aug. 2026) o poate urca cu ~1 pp. Datoria în USD este
# tratată ca mișcându-se cu cursul EUR/RON (curs EUR/USD constant, ca în ipotezele BNR).
PONDERE_VALUTA = 0.49

# ----------------------------------------------------------------------------
# 2. IPOTEZE MACROECONOMICE (creștere nominală a PIB, %)
# ----------------------------------------------------------------------------
# Scenariu de bază: 2026 ~7,0% nominal = contracția reală estimată de FMI (WEO oct.
# 2026) și S&P (-0,5%) + un deflator de ~7,5%: INS (9 oct. 2026) dă un PIB nominal în
# sem. I 2026 cu ~9% peste sem. I 2025 (907,2 mld. lei; real -0,6%), iar inflația a scăzut
# în sem. II (6,6% în sept.), deci deflatorul anual coboară spre 7-7,5%. CNSP (primăvara
# 2026) dădea 7,1% (PIB 2.056 mld. lei, cel folosit de MF în execuție).
# 2027-2030 în linie cu prognozele CE/FMI (FMI: +2,2% real în 2027, inflație 4,1%;
# start 6,5% nominal), apoi spre 5,5% în 2030;
# din 2031: ~5,0% nominal = creștere reală potențială de ~2,5% (capătul de jos al
# intervalului CF de 2,5-3,5%, cu rezerva CF privind forța de muncă) + deflator ~2,5%
# (puțin peste inflația din zona euro, ca la o economie în convergență).
CRESTERE_NOMINALA_2026 = 7.0

def crestere_nominala_pib(baza_2026=CRESTERE_NOMINALA_2026, start_2027=6.5, terminal=5.0,
                          ani=range(2026, 2041)):
    g = {}
    for i, an in enumerate(ani):
        if an == 2026:
            g[an] = baza_2026
        elif an <= 2030:
            # liniar de la start_2027 la 5,5% în 2030
            g[an] = start_2027 + (5.5 - start_2027) * (an - 2027) / 3.0
        else:
            g[an] = terminal
    return g

# Transmiterea randamentelor de piață în rata efectivă: în fiecare an se
# refinanțează ~20% din stoc (scadențe ~13% + finanțarea deficitului), iar ~81%
# din datorie are dobândă fixă, deci doar partea refinanțată preia randamentul
# nou: r_efectiv[t] = (1 − s)·r_efectiv[t−1] + s·randament_piata[t].
PONDERE_REFINANTATA = 0.20

# Randamentul de piață al emisiunilor noi (%, mix lei/EUR). Oct. 2026: 10 ani lei
# ~7,6% pe piața secundară la final de sept. (7,64% la 2 oct.), licitațiile MF din 5-15
# oct. la 6,81-7,18%, emisiunile din 2026 la 6,3-7,5%, Fidelis 7,75% (lei) / 6,60% (EUR).
# Ipoteză: ~7,0% în 2027, apoi scădere odată cu dezinflația și
# închiderea PDE, la 5,5% din 2032 (r − g ≈ +0,5 pp față de creșterea nominală
# terminală de 5,0%, o primă de risc moderată pentru ratingul BBB-).
RANDAMENT_PIATA = {2027: 7.0, 2028: 6.6, 2029: 6.2, 2030: 5.8, 2031: 5.6}

def randament_piata(terminal=5.5, delta=0.0, ani=range(2026, 2041)):
    """Randamentul de piață al emisiunilor noi (%), an -> valoare; `delta` = pp
    adăugate (negativ = randamente mai mici)."""
    return {an: RANDAMENT_PIATA.get(an, terminal) + delta for an in ani if an >= 2027}

# Rata efectivă a dobânzii pe datorie (%), dobânzi / stocul ESA de la începutul anului
# (partea în valută la cursul nou): ~5,2% în 2025 (50,2 / 964,3 mld. lei); ~5,5% în 2026
# (dobânzile estimate din execuția pe 9 luni, ~63,5 mld. lei, pe un stoc de ~1.136 mld.
# lei; ediția din 4 oct. folosea 5,1% = proiecția MF de 58,4 mld., care nu includea
# datoria nouă). Valoarea e consecventă cu regula de mai jos aplicată din 2025:
# 0,8 × 5,2% + 0,2 × ~7% (randamentele din 2026) ≈ 5,5%; S&P estimează 5,6%. Din 2027,
# rata efectivă converge treptat spre randamentul de piață al emisiunilor noi (vezi
# PONDERE_REFINANTATA): urcă atâta timp cât datoria nouă e mai scumpă decât costul
# mediu al celei vechi.
RATA_EFECTIVA_2026 = 5.5

def rata_dobanda(r_2026=RATA_EFECTIVA_2026, piata=None, ani=range(2026, 2041),
                 s=PONDERE_REFINANTATA):
    if piata is None:
        piata = randament_piata(ani=ani)
    r, prev = {}, r_2026
    for an in ani:
        if an > 2026:
            prev = (1 - s) * prev + s * piata[an]
        r[an] = prev
    return r

def transmitere_soc(soc_piata, ani, s=PONDERE_REFINANTATA):
    """soc_piata: dict an -> pp peste randamentele de bază. Întoarce șocul
    asupra ratei efective (pp), an -> valoare."""
    rez, prev = {}, 0.0
    for an in ani:
        prev = (1 - s) * prev + s * soc_piata.get(an, 0.0)
        rez[an] = prev
    return rez

# Deprecierea anuală a leului față de euro (%). 2026: mediile lunare Eurostat
# (ert_bil_eur_m) din ian.–sep. (5,092 până în apr., 5,23-5,26 după căderea guvernului
# din mai), iar oct.–dec. la nivelul din octombrie (~5,34; record BNR 5,3527 la 6 oct.):
# media anuală ≈ 5,22 lei/EUR, +3,5% față de 5,04 în 2025 (ediția din 4 oct. folosea
# 5,18, prognoza de primăvară CNSP). Nivelul din oct. (~5,34) este puțin peste media din
# 2027 a modelului (~5,30): baza presupune că leul rămâne aproximativ la nivelul actual.
# 2027-2030: 1,5%/an, diferențialul de inflație față de zona euro din ipotezele
# de creștere (deflator 3-4% față de ~2%) și aproape de media istorică
# (1,7%/an 2005-2025). Din 2031: 1%/an, cu un deflator de ~2,5% (diferențial de
# ~0,5 pp față de zona euro): o depreciere reală de ~0,5%/an, care corectează
# treptat supraevaluarea reală a leului estimată de FMI (~18,5% în 2024). Prognoza
# oficială CNSP (dec. 2025: 5,15 / 5,20 / 5,25 lei/EUR în 2027-2029, apoi constant)
# este mai optimistă; ritmul ei (~1%/an până în 2029, apoi 0), aplicat de la nivelul
# din 2026, este folosit în S6 (~5,36 lei/EUR).
CURS_LUNAR_2026 = [5.0919, 5.0945, 5.0954, 5.0991, 5.2296, 5.2421, 5.2372, 5.2493, 5.2633]
CURS_OCT_2026 = 5.34
CURS_2026 = (sum(CURS_LUNAR_2026) + CURS_OCT_2026 * (12 - len(CURS_LUNAR_2026))) / 12
DEPRECIERE_2026 = (CURS_2026 / CURS_EUR_RON[2025] - 1) * 100
DEPRECIERE_CNSP = {2027: (5.15 / 5.11 - 1) * 100, 2028: (5.20 / 5.15 - 1) * 100,
                   2029: (5.25 / 5.20 - 1) * 100}

def depreciere_leu(trend=1.5, terminal=1.0, ani=range(2026, 2041), oficial=False):
    """Deprecierea anuală a leului față de euro (%), an -> valoare: `trend` în
    2027-2030, `terminal` din 2031. oficial=True: ritmul prognozei CNSP (dec. 2025) din
    2027, constant după 2029."""
    e = {}
    for an in ani:
        if an == 2026:
            e[an] = DEPRECIERE_2026
        elif oficial:
            e[an] = DEPRECIERE_CNSP.get(an, 0.0)
        else:
            e[an] = trend if an <= 2030 else terminal
    return e

# ----------------------------------------------------------------------------
# 3. MOTORUL DSA
# ----------------------------------------------------------------------------
# Scadențe anuale ≈ 13% din stoc (MFP: 148 mld. lei scadențe 2026 / stoc ESA
# ~1.138 mld. lei). Nu se deduce direct din scadența medie (4,1 ani interne,
# 8,1 ani euroobligațiuni): profilul de rambursare e concentrat pe titlurile scurte.
RATURA_SCADENTA_ANUALA = 0.13

# Alte ajustări stoc-flux (în afara reevaluării valutare), pp din PIB pe an:
# acumularea de lichidități în trezorerie (prefinanțare), împrumuturi UE trase înaintea
# cheltuielii, active financiare. Istoric (vezi verifica_istoric): reziduul identității
# a fost +1,2 pp în 2024 și +0,8 pp în 2025 (cu cursuri medii anuale; la cursurile de
# final de an ar fi ceva mai mic). 2026: prefinanțarea SAFE (2,502 mld. €, ~13 mld. lei,
# încasată la 25-26 aug. 2026, cheltuită pe apărare abia din 2027) crește datoria brută
# fără să treacă prin deficit: +0,6 pp din PIB. Din 2027, convenția DSA a CE (zero după
# orizontul de prognoză); dacă banii se cheltuiesc în limita țintelor de deficit, efectul
# se inversează (datorie cu ~0,5 pp mai mică). Sensibilitatea la 0,5 și 1,0 pp/an din
# 2027 este în sensibilitate_stoc_flux().
AJUSTARE_STOC_FLUX = {2026: 0.6}

def ruleaza_dsa(datorie_start, deficit_esa, r, g, pib_start, ani, e=None,
                alfa=PONDERE_VALUTA, sfa=AJUSTARE_STOC_FLUX):
    """Integrează datoria. deficit_esa/r/g/e = dict an->valoare (% sau mld).
    deficit_esa[an] poate fi și o funcție callable(an, interes_%pib) -> deficit.
    e = deprecierea anuală a leului față de euro (%); None = curs constant.
    sfa = alte ajustări stoc-flux (pp din PIB pe an; număr sau dict an->valoare)."""
    rand = []
    d = datorie_start
    pib = pib_start
    curs = CURS_EUR_RON[2025]
    for an in ani:
        g_an = g[an] / 100.0
        pib_anterior = pib
        pib = pib_anterior * (1 + g_an)
        r_an = r[an] / 100.0
        e_an = (e[an] if e is not None else 0.0) / 100.0
        curs = curs * (1 + e_an)
        # dobânzi plătite pe stocul de la începutul anului, ca % din PIB-ul
        # anului curent (de aici împărțirea la 1+g); partea în valută se
        # plătește la cursul nou
        interes = r_an * d * (1 + alfa * e_an) / (1 + g_an)
        val = deficit_esa[an]
        def_an = val(an, interes) if callable(val) else val
        sold_primar = interes - def_an              # pozitiv = excedent
        # reevaluarea în lei a stocului în valută (ajustare stoc-flux)
        ajustare_valutara = alfa * e_an * d / (1 + g_an)
        ajustare_sf = sfa.get(an, 0.0) if isinstance(sfa, dict) else sfa
        d_nou = d / (1 + g_an) + def_an + ajustare_valutara + ajustare_sf
        # Necesar brut de finanțare = scadențe anuale + deficitul bugetar (+ alte
        # ajustări stoc-flux, care trebuie și ele finanțate).
        # ~13% din stoc ajunge la scadență anual (calibrat pe MFP: 148 mld lei
        # scadențe 2026 / stoc ~1.138 mld lei). Verificat cu MFP: NBF 2026 ≈
        # 278 mld lei.
        scadente = d * RATURA_SCADENTA_ANUALA / (1 + g_an)
        nbf = scadente + def_an + ajustare_sf
        rand.append({
            "an": an,
            "pib_mld": pib,
            "crestere_nominala_%": g[an],
            "rata_dobanda_%": r[an],
            "depreciere_leu_%": e_an * 100,
            "curs_eur_ron": curs,
            "deficit_esa_%pib": def_an,
            "interes_%pib": interes,
            "sold_primar_%pib": sold_primar,
            "ajustare_valutara_%pib": ajustare_valutara,
            "ajustare_stoc_flux_%pib": ajustare_sf,
            "datorie_%pib": d_nou,
            "datorie_mld_lei": d_nou / 100 * pib,
            "dobanzi_mld_lei": interes / 100 * pib,
            "scadente_%pib": scadente,
            "necesar_finantare_%pib": nbf,
        })
        d = d_nou
    return pd.DataFrame(rand)

# ----------------------------------------------------------------------------
# 4. SCENARII
# ----------------------------------------------------------------------------
ANI = list(range(2026, 2041))
SOC_CURS_S4 = 10.0   # depreciere suplimentară a leului în 2028 în S4 (%)
# S7: abaterea deficitului ESA față de S2 din 2027 (pp din PIB). Consiliul Fiscal
# estimează pentru 2027 un deficit realist de ~5,5% din PIB, față de ținta de 5,2% (ESA)
# din Strategia fiscal-bugetară, cu condiția ca salariile și pensiile să nu crească mai
# repede decât PIB-ul; condițiile PSD pentru guvernul Niculescu (oct. 2026): fără taxe
# noi în 2027, pensii indexate conform legii.
ABATERE_S7 = 0.3
DEFICIT_S2 = {2026: 6.0, 2027: 5.2, 2028: 4.2, 2029: 3.2, 2030: 2.8,
              2031: 2.5, 2032: 2.3, 2033: 2.1, 2034: 2.0, 2035: 2.0,
              2036: 2.0, 2037: 2.0, 2038: 2.0, 2039: 2.0, 2040: 2.0}

def scenarii():
    g = crestere_nominala_pib()
    r = rata_dobanda()
    e = depreciere_leu()
    S = {}

    # S1 „Nimic nu se schimbă" (no-policy change) - replică CF Opinie 2026:
    # 2026 conform țintei bugetare (6,0% ESA, ca în S2), apoi din 2027 soldul
    # primar rămâne blocat la ~-2,3% din PIB (structura bugetară de la finalul
    # lui 2026 se păstrează), deci deficitul total CREȘTE odată cu dobânzile.
    # CF: datorie 80% din PIB în 2034, 100% în 2040.
    def_s1 = {an: (lambda a, interes: interes + 2.3) for an in ANI}
    def_s1[2026] = 6.0
    S["S1 Nicio schimbare de politică (no-policy change)"] = ruleaza_dsa(
        DATORIE_PIB[2025], def_s1, r, g, PIB_NOMINAL[2025], ANI, e)

    # S2 „Consolidare conform planului" - traiectoria PDE / SFB 2026-2029 +
    # închiderea PDE în 2030 (2,8%), apoi apropiere de MTO (2% ESA).
    def_s2 = dict(DEFICIT_S2)
    S["S2 Consolidare conform planului (PDE)"] = ruleaza_dsa(
        DATORIE_PIB[2025], def_s2, r, g, PIB_NOMINAL[2025], ANI, e)

    # Scenariile de stres S3 și S4 fixează traseul soldului PRIMAR (efortul de
    # politică), nu deficitul total: astfel, dobânzile mai mari se văd în
    # deficit și în datorie. Șocul de randament se transmite treptat în rata
    # efectivă (vezi transmitere_soc).
    def sold_primar_fix(pb):
        return {an: (lambda a, interes, pb=pb: interes - pb[a]) for an in ANI}

    # S3 „Derapaj / ajustare amânată": efortul primar corespunde unui deficit
    # de ~5,6-5,8% în 2027-2028 (la dobânzile de bază), apoi corecție tardivă;
    # piețele cer +100 pb permanent din 2027 (risc de rating).
    def_s3 = {2026: 6.0, 2027: 5.8, 2028: 5.6, 2029: 5.2, 2030: 4.5,
              2031: 3.8, 2032: 3.2, 2033: 2.8, 2034: 2.5, 2035: 2.3,
              2036: 2.2, 2037: 2.1, 2038: 2.0, 2039: 2.0, 2040: 2.0}
    baza_s3 = ruleaza_dsa(DATORIE_PIB[2025], def_s3, r, g, PIB_NOMINAL[2025], ANI, e)
    pb3 = dict(zip(baza_s3["an"], baza_s3["sold_primar_%pib"]))
    soc3 = transmitere_soc({an: 1.0 for an in ANI if an >= 2027}, ANI)
    r3 = {an: r[an] + soc3[an] for an in ANI}
    S["S3 Derapaj: ajustare amânată + randamente +100 pb"] = ruleaza_dsa(
        DATORIE_PIB[2025], sold_primar_fix(pb3), r3, g, PIB_NOMINAL[2025], ANI, e)

    # S4 „Șoc sever în 2028" (stres stilizat, de tipul celui din analiza CF):
    # randamente de piață +300 pb în 2028, +200 pb în 2029, +100 pb în 2030
    # (transmise treptat în rata efectivă), PIB nominal cu 2 pp mai mic în 2028
    # și cu 1 pp în 2029, sold primar mai slab cu 1,5 pp în 2028 și cu 1 pp în
    # 2029 față de S2, plus o depreciere a leului cu 10% peste trend în 2028
    # (nivel permanent). Calibrare: ~2/3 din cel mai sever an istoric 2005-2024
    # (+15,1% în 2009); cu ea, saltul datoriei în 2028 este apropiat de cel din
    # testul de stres al CF (care asociază șocului o depreciere a leului).
    pb2 = dict(zip(S["S2 Consolidare conform planului (PDE)"]["an"],
                   S["S2 Consolidare conform planului (PDE)"]["sold_primar_%pib"]))
    pb4 = dict(pb2)
    pb4[2028] -= 1.5
    pb4[2029] -= 1.0
    soc4 = transmitere_soc({2028: 3.0, 2029: 2.0, 2030: 1.0}, ANI)
    r4 = {an: r[an] + soc4[an] for an in ANI}
    g4 = dict(g)
    g4[2028] = g[2028] - 2.0
    g4[2029] = g[2029] - 1.0
    e4 = dict(e)
    e4[2028] += SOC_CURS_S4
    S["S4 Șoc sever 2028 (r-g reversat)"] = ruleaza_dsa(
        DATORIE_PIB[2025], sold_primar_fix(pb4), r4, g4, PIB_NOMINAL[2025], ANI, e4)

    # S5 „Ținta Consiliului Fiscal": excedent primar structural de ~2% din PIB
    # potențial în 2030, echivalent (CF) cu un excedent primar de ~1,4% din PIB,
    # menținut ulterior. Modelul impune direct traseul soldului primar; deficitul
    # total rezultă din dobânzi. Ipotezele macro (creștere, randamente, curs) sunt
    # cele de bază, ca în S2: S5 izolează efectul țintei fiscale.
    sp5 = {2027: -1.6, 2028: -0.5, 2029: 0.5}
    def_s5 = {an: (lambda a, interes: interes - sp5.get(a, 1.4)) for an in ANI}
    def_s5[2026] = 6.0
    S["S5 Ținta CF (ipoteze macro de bază)"] = ruleaza_dsa(
        DATORIE_PIB[2025], def_s5, r, g, PIB_NOMINAL[2025], ANI, e)

    # S6 „Ținta CF + creștere (best case)": același traseu al soldului primar ca în
    # S5, plus creștere nominală mai bună (fonduri UE + investiții; 7,5% în 2027,
    # 5,5% din 2031), randamente de piață cu 0,75 pp mai mici (credibilitate,
    # perspectivă de rating îmbunătățită), iar cursul urmează ritmul prognozei
    # oficiale CNSP (~1%/an până în 2029, apoi constant, ~5,36 lei/EUR).
    g6 = crestere_nominala_pib(start_2027=7.5, terminal=5.5)
    r6 = rata_dobanda(piata=randament_piata(delta=-0.75))
    e6 = depreciere_leu(oficial=True)
    S["S6 Ținta CF + creștere (best case)"] = ruleaza_dsa(
        DATORIE_PIB[2025], def_s5, r6, g6, PIB_NOMINAL[2025], ANI, e6)

    # S7 „Buget 2027 relaxat": noul guvern nu majorează taxele în 2027 și indexează
    # pensiile (condițiile PSD, oct. 2026); deficitul ESA din 2027 este cel estimat de CF
    # (~5,5%, nu 5,2%), iar consolidarea continuă apoi cu aceeași pantă ca în S2, cu
    # abaterea păstrată (măsurile sunt permanente): PDE se închide abia în 2031. Ipotezele
    # macro sunt cele de bază; ca în S2, deficitul total este fixat.
    S["S7 Buget 2027 relaxat: taxe înghețate, pensii indexate"] = ruleaza_dsa(
        DATORIE_PIB[2025], deficit_s7(), r, g, PIB_NOMINAL[2025], ANI, e)
    return S

def deficit_s7(abatere=ABATERE_S7):
    return {an: v + (abatere if an >= 2027 else 0.0) for an, v in DEFICIT_S2.items()}

def s7_variante():
    """S7 și două variante: consolidarea amânată cu un an (2027 la nivelul din 2026, apoi
    traseul S2 decalat cu un an) și S7 cu randamente de piață +50 pb din 2027 (risc de
    retrogradare), cu efortul primar din S7 ținut fix (dobânzile mai mari trec în deficit)."""
    g, r, e = crestere_nominala_pib(), rata_dobanda(), depreciere_leu()
    s7 = ruleaza_dsa(DATORIE_PIB[2025], deficit_s7(), r, g, PIB_NOMINAL[2025], ANI, e)
    amanat = {an: DEFICIT_S2[max(an - 1, 2026)] for an in ANI}
    pb7 = dict(zip(s7["an"], s7["sold_primar_%pib"]))
    r_prima = rata_dobanda(piata=randament_piata(delta=0.5))
    return {
        "S7 (deficit 2027 de 5,5%, aceeași pantă)": s7,
        "Consolidarea amânată cu un an": ruleaza_dsa(
            DATORIE_PIB[2025], amanat, r, g, PIB_NOMINAL[2025], ANI, e),
        "S7 + randamente +50 pb (efort primar fix)": ruleaza_dsa(
            DATORIE_PIB[2025], {an: (lambda a, i: i - pb7[a]) for an in ANI},
            r_prima, g, PIB_NOMINAL[2025], ANI, e),
    }

# ----------------------------------------------------------------------------
# 5. SIMULARE STOCASTICĂ (fan chart) pentru scenariul S2
# ----------------------------------------------------------------------------
def simulare_stocastica(df_baza, nr_sim=10000, seed=7,
                        sd_g=1.6, sd_r=0.9, sd_pb=1.1, rho=0.3, sd_e=4.5,
                        alfa=PONDERE_VALUTA):
    """Șocuri simetrice pe g, r, sold primar și curs (σ calibrate pe volatilitatea
    istorică 2005-2024 a României, în stilul DSA-CE). Șocul de curs (σ = 4,5%,
    variațiile anuale EUR/RON 2006-2024, Eurostat) se adaugă deprecierii de bază
    și este permanent (mers aleator în nivel). Șocurile sunt independente; în
    criză, deprecierea coincide de obicei cu creștere mai mică și dobânzi mai mari
    (vezi testul de stres CF), deci cozile benzii sunt mai degrabă subestimate."""
    rng = np.random.default_rng(seed)
    ani = df_baza["an"].values
    n = len(ani)
    d0 = DATORIE_PIB[2025]
    traiectorii = np.zeros((nr_sim, n))
    for k in range(nr_sim):
        d = d0
        eps_pb_prev = 0.0
        for i in range(n):
            row = df_baza.iloc[i]
            eps_g = rng.normal(0, sd_g)
            eps_r = rng.normal(0, sd_r)
            eps_pb = rho * eps_pb_prev + rng.normal(0, sd_rho(sd_pb, rho))
            eps_pb_prev = eps_pb
            eps_e = rng.normal(0, sd_e)
            g = (row["crestere_nominala_%"] + eps_g) / 100
            r = max(row["rata_dobanda_%"] + eps_r, 0.5) / 100
            e = (row["depreciere_leu_%"] + eps_e) / 100
            pb = row["sold_primar_%pib"] + eps_pb
            d = (d * (1 + r) * (1 + alfa * e) / (1 + g) - pb
                 + row["ajustare_stoc_flux_%pib"])
            traiectorii[k, i] = d
    return traiectorii

def sd_rho(sd, rho):
    return sd * np.sqrt(1 - rho ** 2)

# ----------------------------------------------------------------------------
# 6. GRAFICE
# ----------------------------------------------------------------------------
CULORI_SCENARII = {"S1": "#b22222", "S2": "#1f6f2f", "S3": "#e07b00",
                   "S4": "#6a3d9a", "S5": "#17becf", "S6": "#1f77b4", "S7": "#8c564b"}

def grafice(S, fan):
    plt.rcParams.update({"font.size": 10, "axes.grid": True,
                         "grid.alpha": 0.3, "figure.dpi": 130})

    # 6.1 Traseele datoriei pe scenarii
    fig, ax = plt.subplots(figsize=(9, 5.2))
    culori = CULORI_SCENARII
    for nume, df in S.items():
        cheie = nume.split()[0]
        ax.plot(df["an"], df["datorie_%pib"], marker="o", ms=3.5,
                lw=2, label=nume, color=culori.get(cheie))
    ax.axhline(60, color="black", ls="--", lw=1, label="Prag UE: 60% din PIB")
    ax.axhline(54.8, color="gray", ls=":", lw=1)
    ax.annotate("2024: 54,8%", (2024.05, 54.8), fontsize=8, color="gray")
    ax.scatter([2025], [DATORIE_PIB[2025]], color="black", zorder=5)
    ax.annotate(f"2025: {DATORIE_PIB[2025]:.1f}%".replace(".", ","), (2025.05, 57.6), fontsize=8)
    ax.set_title("Datoria publică a României — scenarii 2026–2040 (% din PIB)")
    ax.set_xlabel("An"); ax.set_ylabel("% din PIB")
    ax.legend(fontsize=7.5, loc="upper left")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig1_datorie_scenarii.png"))
    plt.close(fig)

    # 6.2 Fan chart S2
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ani = S["S2 Consolidare conform planului (PDE)"]["an"].values
    pct = np.percentile(fan, [5, 10, 25, 50, 75, 90, 95], axis=0)
    ax.fill_between(ani, pct[0], pct[6], alpha=0.15, color="green", label="5–95%")
    ax.fill_between(ani, pct[1], pct[5], alpha=0.25, color="green", label="10–90%")
    ax.fill_between(ani, pct[2], pct[4], alpha=0.4, color="green", label="25–75%")
    ax.plot(ani, pct[3], color="darkgreen", lw=2, label="Mediană")
    ax.plot(ani, S["S2 Consolidare conform planului (PDE)"]["datorie_%pib"],
            color="black", lw=1.5, ls="--", label="Cale deterministă S2")
    ax.axhline(60, color="black", ls=":", lw=1)
    ax.set_title("Scenariul consolidării (S2): bandă de incertitudine (10.000 simulări)")
    ax.set_xlabel("An"); ax.set_ylabel("Datorie, % din PIB")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig2_fan_s2.png"))
    plt.close(fig)

    # 6.3 Sarcina dobânzii
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for nume, df in S.items():
        cheie = nume.split()[0]
        ax.plot(df["an"], df["interes_%pib"], lw=2, marker="o", ms=3,
                label=cheie, color=culori.get(cheie))
    ax.set_title("Cheltuielile cu dobânzile (% din PIB)")
    ax.set_xlabel("An"); ax.set_ylabel("% din PIB")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig3_dobanzi.png"))
    plt.close(fig)

    # 6.4 Necesar de finanțare
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for nume, df in S.items():
        cheie = nume.split()[0]
        ax.plot(df["an"], df["necesar_finantare_%pib"], lw=2,
                label=cheie, color=culori.get(cheie))
    ax.set_title("Necesar brut de finanțare ≈ datorie rulantă + deficit (% din PIB)")
    ax.set_xlabel("An"); ax.set_ylabel("% din PIB")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig4_necesar_finantare.png"))
    plt.close(fig)

    # 6.5 Hartă de sensibilitate: datorie 2035 în funcție de (r-g) și sold primar
    ani_s = list(range(2026, 2036))
    delta_rg = np.arange(-3.0, 3.1, 0.5)   # abatere r-g față de scenariul de bază
    pb_path = np.arange(-1.0, 3.1, 0.5)    # sold primar constant, % PIB
    harta = np.zeros((len(pb_path), len(delta_rg)))
    g = crestere_nominala_pib()
    r = rata_dobanda()
    e = depreciere_leu()                   # deprecierea de bază, ca în S2
    for i, pb in enumerate(pb_path):
        for j, drg in enumerate(delta_rg):
            d = DATORIE_PIB[2025]
            for an in ani_s:
                g_an = (g[an] - drg) / 100   # r−g mai mare ⇔ g mai mic
                r_an = r[an] / 100
                e_an = PONDERE_VALUTA * e[an] / 100
                d = (d * (1 + r_an) * (1 + e_an) / (1 + g_an) - pb
                     + AJUSTARE_STOC_FLUX.get(an, 0.0))   # ca în S2 (SAFE în 2026)
            harta[i, j] = d
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    im = ax.imshow(harta, origin="lower", aspect="auto", cmap="RdYlGn_r",
                   extent=[delta_rg[0] - 0.25, delta_rg[-1] + 0.25,
                           pb_path[0] - 0.25, pb_path[-1] + 0.25])
    ax.contour(delta_rg, pb_path, harta, levels=[60], colors="black", linewidths=2)
    ax.set_xlabel("Abatere r − g față de scenariul de bază (puncte procentuale)")
    ax.set_ylabel("Sold bugetar primar constant (% din PIB)")
    ax.set_title("Datoria publică în 2035 (% din PIB) — sensibilitate la r−g și sold primar\n"
                 "(linia neagră = 60% din PIB)")
    fig.colorbar(im, ax=ax, label="% din PIB")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig5_sensibilitate.png"))
    plt.close(fig)

    # 6.6 Efectul cursului de schimb asupra datoriei (S2)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8))
    stil = {ETICHETA_CURS_CONSTANT: ("#7f7f7f", "--"),
            "Ritmul prognozei CNSP (constant din 2029)": ("#1f77b4", "-"),
            "Bază: 1,5%/an până în 2030, apoi 1%": ("#1f6f2f", "-"),
            "Depreciere 3%/an": ("#e07b00", "-"),
            "Bază + șoc 15% în 2027": ("#b22222", "-")}
    for nume, df in curs_variante_s2().items():
        c, ls = stil[nume]
        ax1.plot(df["an"], df["datorie_%pib"], lw=2, color=c, ls=ls, label=nume)
    ax1.axhline(60, color="black", ls=":", lw=1)
    ax1.set_title("S2: datoria (% din PIB) după traseul cursului EUR/RON")
    ax1.set_xlabel("An"); ax1.set_ylabel("% din PIB")
    ax1.legend(fontsize=7.5)
    rate, d35 = sensibilitate_curs_s2()
    ax2.plot(rate, d35, lw=2.2, color="#1f6f2f", marker="o", ms=3.5)
    ax2.axhline(60, color="black", ls=":", lw=1)
    d35_baza = _ruleaza_s2(depreciere_leu()).set_index("an").loc[2035, "datorie_%pib"]
    ax2.axhline(d35_baza, color="#1f6f2f", ls="--", lw=1)
    ax2.annotate("ipoteza de bază S2", (0.05, d35_baza + 0.3), fontsize=8, color="#1f6f2f")
    ax2.set_title("S2: datoria în 2035 după deprecierea anuală (din 2027)")
    ax2.set_xlabel("Depreciere anuală a leului față de euro (%)")
    ax2.set_ylabel("Datorie 2035, % din PIB")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig10_curs_schimb.png"))
    plt.close(fig)

def _ruleaza_s2(e):
    """S2 (aceleași ținte de deficit, dobânzi și creștere) cu alt traseu al cursului."""
    def_s2 = scenarii()["S2 Consolidare conform planului (PDE)"].set_index("an")["deficit_esa_%pib"]
    return ruleaza_dsa(DATORIE_PIB[2025], def_s2.to_dict(), rata_dobanda(),
                       crestere_nominala_pib(), PIB_NOMINAL[2025], ANI, e)

ETICHETA_CURS_CONSTANT = f"Curs constant ({CURS_2026:.2f} lei/EUR din 2026)".replace(".", ",")

def curs_variante_s2():
    """Traseul datoriei din S2 sub mai multe ipoteze de curs EUR/RON."""
    baza = depreciere_leu()
    soc = dict(baza)
    soc[2027] += 15.0      # un an ca 2009 (+15,1%), nivel permanent
    constant = {an: (DEPRECIERE_2026 if an == 2026 else 0.0) for an in ANI}
    return {
        ETICHETA_CURS_CONSTANT: _ruleaza_s2(constant),
        "Ritmul prognozei CNSP (constant din 2029)": _ruleaza_s2(depreciere_leu(oficial=True)),
        "Bază: 1,5%/an până în 2030, apoi 1%": _ruleaza_s2(baza),
        "Depreciere 3%/an": _ruleaza_s2(depreciere_leu(trend=3.0, terminal=3.0)),
        "Bază + șoc 15% în 2027": _ruleaza_s2(soc),
    }

def sensibilitate_curs_s2(rate=np.arange(0.0, 5.01, 0.5)):
    """Datoria din 2035 (S2) în funcție de deprecierea anuală din 2027."""
    d35 = []
    for t in rate:
        df = _ruleaza_s2(depreciere_leu(trend=t, terminal=t))
        d35.append(df.loc[df["an"] == 2035, "datorie_%pib"].iloc[0])
    return rate, np.array(d35)

def verifica_istoric():
    """Reziduul identității datoriei în 2024 și 2025 (pp din PIB): datoria observată
    minus cea prezisă din deficitul ESA, creșterea nominală și reevaluarea valutară
    (cursuri medii anuale, ca în model)."""
    rez = {}
    for an in (2024, 2025):
        g = PIB_NOMINAL[an] / PIB_NOMINAL[an - 1] - 1
        e = CURS_EUR_RON[an] / CURS_EUR_RON[an - 1] - 1
        prezis = DATORIE_PIB[an - 1] * (1 + PONDERE_VALUTA * e) / (1 + g) + DEFICIT["esa"][an]
        rez[an] = DATORIE_PIB[an] - prezis
    return rez

def sensibilitate_stoc_flux(valori=(0.0, 0.5, 1.0)):
    """Traseul datoriei din S2 cu alte ajustări stoc-flux constante din 2027 (pp din
    PIB/an), peste cele din bază (prefinanțarea SAFE în 2026)."""
    def_s2 = scenarii()["S2 Consolidare conform planului (PDE)"].set_index("an")["deficit_esa_%pib"]
    return {v: ruleaza_dsa(DATORIE_PIB[2025], def_s2.to_dict(), rata_dobanda(),
                           crestere_nominala_pib(), PIB_NOMINAL[2025], ANI,
                           depreciere_leu(),
                           sfa={an: AJUSTARE_STOC_FLUX.get(an, 0.0) + (v if an >= 2027 else 0.0)
                                for an in ANI})
            for v in valori}

def s2_efort_primar_fix(delta_piata):
    """S2 cu efortul primar din bază ținut fix și randamente de piață mai mari cu
    `delta_piata` pp din 2027: dobânzile suplimentare trec în deficit și în datorie."""
    s2 = scenarii()["S2 Consolidare conform planului (PDE)"]
    pb = dict(zip(s2["an"], s2["sold_primar_%pib"]))
    r = rata_dobanda(piata=randament_piata(delta=delta_piata))
    return ruleaza_dsa(DATORIE_PIB[2025], {an: (lambda a, i: i - pb[a]) for an in ANI},
                       r, crestere_nominala_pib(), PIB_NOMINAL[2025], ANI, depreciere_leu())

# ----------------------------------------------------------------------------
# 7. CALCULE SUPLIMENTARE PENTRU RĂSPUNS
# ----------------------------------------------------------------------------
def calcule_raspuns(S):
    rez = {}
    # Soldul primar necesar stabilizării datoriei la nivelul din 2025:
    # pb* = d * (r-g)/(1+g)
    for rg in (-2.0, -1.0, 0.0, 1.0, 2.0, 3.0):
        d = DATORIE_PIB[2025]
        pb = d * (rg / 100) / (1 + 0.055)
        rez[f"Sold primar necesar pt. stabilizare la {d:.1f}%, r-g={rg:+.0f} pp"] = pb
    return rez

# ----------------------------------------------------------------------------
if __name__ == "__main__":
    S = scenarii()
    for nume, df in S.items():
        df.to_csv(os.path.join(OUT, f"traseu_{nume.split()[0]}.csv"),
                  index=False, encoding="utf-8-sig")
        print(f"\n=== {nume} ===")
        sub = df[df["an"].isin([2027, 2030, 2035, 2040])]
        print(sub[["an", "deficit_esa_%pib", "sold_primar_%pib", "interes_%pib",
                   "datorie_%pib", "necesar_finantare_%pib"]]
              .to_string(index=False, float_format=lambda x: f"{x:6.2f}"))
    fan = simulare_stocastica(S["S2 Consolidare conform planului (PDE)"])
    np.save(os.path.join(OUT, "fan_s2.npy"), fan)
    pct = np.percentile(fan, [5, 25, 50, 75, 95], axis=0)
    pd.DataFrame({
        "an": S["S2 Consolidare conform planului (PDE)"]["an"].values,
        "p5": pct[0], "p25": pct[1], "p50": pct[2], "p75": pct[3], "p95": pct[4],
    }).to_csv(os.path.join(OUT, "fan_s2_percentile.csv"),
              index=False, encoding="utf-8-sig")
    ani_fan = list(S["S2 Consolidare conform planului (PDE)"]["an"].values)
    i30, i35 = ani_fan.index(2030), ani_fan.index(2035)
    print("\n" + "Probabilitate datorie < 60% din PIB în 2035 (S2):",
          f"{(fan[:, i35] < 60).mean() * 100:.1f}%")
    print("Probabilitate datorie mai mare în 2035 decât în 2025 (S2):",
          f"{(fan[:, i35] > DATORIE_PIB[2025]).mean() * 100:.1f}%")
    # criteriul CE (DSA): probabilitatea ca datoria să scadă în cei 5 ani de
    # după perioada de ajustare să fie de cel puțin 70%. Ca în analiza CF,
    # perioada de ajustare se încheie în 2030 (2030 → 2035); planul pe 7 ani
    # al României s-ar încheia în 2031 (2031 → 2036), afișat pentru comparație.
    i31, i36 = ani_fan.index(2031), ani_fan.index(2036)
    print("Probabilitate datorie 2035 < datorie 2030 (criteriul CE, S2):",
          f"{(fan[:, i35] < fan[:, i30]).mean() * 100:.1f}%")
    print("Probabilitate datorie 2036 < datorie 2031 (variantă 7 ani, S2):",
          f"{(fan[:, i36] < fan[:, i31]).mean() * 100:.1f}%")
    print("Mediana / percentila 95 în 2035 (S2):",
          f"{np.percentile(fan[:, i35], 50):.1f}% / {np.percentile(fan[:, i35], 95):.1f}%")
    grafice(S, fan)
    print("\n=== Efectul cursului EUR/RON (S2, datorie % din PIB) ===")
    tab_curs = pd.DataFrame({nume: df.set_index("an")["datorie_%pib"]
                             for nume, df in curs_variante_s2().items()})
    tab_curs.to_csv(os.path.join(OUT, "curs_schimb_s2.csv"), encoding="utf-8-sig")
    print(tab_curs.loc[[2027, 2030, 2035, 2040]].T.to_string(
        float_format=lambda x: f"{x:6.2f}"))
    for nume, df in S.items():
        df_an = df.set_index("an")
        print(f"  {nume.split()[0]}: reevaluare cumulată 2026-2035 = "
              f"{df_an.loc[2026:2035, 'ajustare_valutara_%pib'].sum():.2f} pp PIB; "
              f"curs 2035 = {df_an.loc[2035, 'curs_eur_ron']:.2f} lei/EUR")
    print("\n=== Reziduul identității (alte ajustări stoc-flux, pp din PIB) ===")
    for an, v in verifica_istoric().items():
        print(f"  {an}: {v:+.2f}")
    tab_sf = pd.DataFrame({f"stoc-flux {v:g} pp/an": df.set_index("an")["datorie_%pib"]
                           for v, df in sensibilitate_stoc_flux().items()})
    tab_sf.to_csv(os.path.join(OUT, "stoc_flux_s2.csv"), encoding="utf-8-sig")
    print("\n=== S2: datoria după alte ajustări stoc-flux ===")
    print(tab_sf.loc[[2030, 2035, 2040]].T.to_string(float_format=lambda x: f"{x:6.2f}"))
    print("\n=== S2 cu efortul primar fix și randamente de piață mai mari ===")
    for dp in (0.0, 1.0, 1.5, 2.0):
        x = s2_efort_primar_fix(dp).set_index("an")
        print(f"  +{dp:.1f} pp: datorie 2030/2035/2040 = "
              f"{x.loc[2030, 'datorie_%pib']:.1f} / {x.loc[2035, 'datorie_%pib']:.1f} / "
              f"{x.loc[2040, 'datorie_%pib']:.1f}; deficit 2030 = {x.loc[2030, 'deficit_esa_%pib']:.1f}")
    print("\n=== S7: bugetul 2027 relaxat și variante ===")
    var7 = s7_variante()
    pd.DataFrame({n: df.set_index("an")["datorie_%pib"] for n, df in var7.items()}).to_csv(
        os.path.join(OUT, "s7_variante.csv"), encoding="utf-8-sig")
    for nume, df in var7.items():
        x = df.set_index("an")
        varf = x["datorie_%pib"].idxmax()
        sub60 = x.index[(x["datorie_%pib"] < 60) & (x.index > varf)]
        print(f"  {nume}: deficit 2027/2030/2031 = {x.loc[2027, 'deficit_esa_%pib']:.2f} / "
              f"{x.loc[2030, 'deficit_esa_%pib']:.2f} / {x.loc[2031, 'deficit_esa_%pib']:.2f}; "
              f"datorie 2030/2035/2040 = {x.loc[2030, 'datorie_%pib']:.1f} / "
              f"{x.loc[2035, 'datorie_%pib']:.1f} / {x.loc[2040, 'datorie_%pib']:.1f}; "
              f"vârf {x['datorie_%pib'].max():.1f} în {varf}; "
              f"sub 60% din {sub60[0] if len(sub60) else '-'}")
    s2i = S["S2 Consolidare conform planului (PDE)"].set_index("an")
    print(f"\nS2 2026: PIB {s2i.loc[2026, 'pib_mld']:.1f} mld. lei; dobânzi "
          f"{s2i.loc[2026, 'dobanzi_mld_lei']:.1f} mld. lei ({s2i.loc[2026, 'interes_%pib']:.2f}% PIB); "
          f"datorie {s2i.loc[2026, 'datorie_%pib']:.2f}% ({s2i.loc[2026, 'datorie_mld_lei']:.0f} mld. lei); "
          f"curs {s2i.loc[2026, 'curs_eur_ron']:.4f} (+{DEPRECIERE_2026:.2f}%)")
    print("\nRata efectivă de bază:", {an: round(v, 2) for an, v in rata_dobanda().items()})
    print("\nCalcul suplimentar:", calcule_raspuns(S))
    print("\nGata. Figuri în:", FIG)
