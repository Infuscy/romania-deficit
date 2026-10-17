# -*- coding: utf-8 -*-
"""Generează caietul de lucru Excel cu modelul DSA al României."""
import os
import numpy as np
import pandas as pd
from model_dsa import (scenarii, simulare_stocastica, DATORIE_PIB, PIB_NOMINAL,
                       CURS_EUR_RON, PONDERE_VALUTA, DEPRECIERE_2026, curs_variante_s2,
                       CULORI_SCENARII, RANDAMENT_PIATA, sensibilitate_stoc_flux,
                       DEFICIT, INTERES_PIB, CURS_2026, CRESTERE_NOMINALA_2026,
                       RATA_EFECTIVA_2026, AJUSTARE_STOC_FLUX, DOBANZI_2026_MLD, s7_variante)
from model_macro_feedback import efecte, traseu_datorie_cu_feedback, D_PB
from model_energie_soc import ruleaza_soc, SOC
import model_dezindustrializare as dez
import model_spatiu_fiscal as sf

BASE = os.path.dirname(__file__)
XLSX = os.path.join(BASE, "Model_DSA_Romania.xlsx")

S = scenarii()
fan = simulare_stocastica(S["S2 Consolidare conform planului (PDE)"])
pct = np.percentile(fan, [5, 25, 50, 75, 95], axis=0)
df_fan = pd.DataFrame({
    "an": S["S2 Consolidare conform planului (PDE)"]["an"].values,
    "p5": pct[0], "p25": pct[1], "p50": pct[2], "p75": pct[3], "p95": pct[4],
})

parametri = pd.DataFrame({
    "Indicator": [
        "Datorie publică 2025 (% PIB, ESA)", "PIB nominal 2025 (mld. lei)",
        "Deficit cash 2025 (% PIB)", "Deficit ESA 2025 (% PIB)",
        "Deficit cash 2026 țintă (% PIB)", "Deficit ESA 2026 țintă (% PIB)",
        "Dobânzi 2026 (% PIB, estimare)", "Scadențe anuale din stoc (%)",
        "Creștere PIB nominal 2026 / din 2031 (%)", "Rată efectivă dobândă 2026 (%)",
        "Randament de piață emisiuni noi 2027 / din 2032 (%)", "Pondere refinanțată anual (%)",
        "Alte ajustări stoc-flux, bază: 2026 / din 2027 (pp PIB)",
        "Pondere datorie în valută (%)", "Curs mediu EUR/RON 2025", "Curs mediu EUR/RON 2026",
        "Depreciere leu 2026 (%)", "Depreciere leu 2027-2030 / din 2031 (%/an)",
        "Șoc de curs S4, 2028 (%)", "Volatilitate curs, simulare (σ, %)",
        "Abatere deficit S7 față de S2, din 2027 (pp PIB)",
    ],
    "Valoare": [DATORIE_PIB[2025], PIB_NOMINAL[2025], DEFICIT["cash"][2025], DEFICIT["esa"][2025],
                DEFICIT["cash"][2026], DEFICIT["esa"][2026], INTERES_PIB[2026], 13.0,
                f"{CRESTERE_NOMINALA_2026:.1f} / 5,0".replace(".", ","), RATA_EFECTIVA_2026,
                f"{RANDAMENT_PIATA[2027]:.1f} / 5,5".replace(".", ","), 20.0,
                f"{AJUSTARE_STOC_FLUX[2026]:.1f} / 0".replace(".", ","),
                PONDERE_VALUTA * 100, CURS_EUR_RON[2025], round(CURS_2026, 4),
                DEPRECIERE_2026, "1,5 / 1,0", 10.0, 4.5, 0.3],
    "Sursa": [
        "Eurostat, aprilie 2026 (ST 11135/26): 59,3% pe PIB provizoriu; recalculat pe PIB-ul "
        "semidefinitiv INS (9 oct. 2026); cifra oficială: notificarea Eurostat din 21 oct. 2026",
        "INS, date semidefinitive (9 oct. 2026); provizoriu 1.916,4 mld. lei",
        "MF: 146,03 mld. lei pe PIB-ul semidefinitiv (7,65% în comunicatul din 26 ian. 2026)",
        "Eurostat, aprilie 2026: 7,9% pe PIB provizoriu; recalculat pe PIB-ul semidefinitiv",
        "Legea bugetului 2026 (127,8 mld. lei); MF, oct. 2026", "Legea bugetului 2026 / CF / MF",
        "MF: 50,63 mld. lei în ian.–sep. 2026 (+26,8% a/a) → ~"
        + f"{DOBANZI_2026_MLD:.1f}".replace(".", ",")
        + " mld. lei pe an (estimare proprie, profilul lunar din 2025)",
        "MFP: 148 mld scadențe 2026 / stoc ESA ~1.138 mld",
        "2026: FMI (oct. 2026) −0,5% real + deflator ~7,5% (INS: PIB nominal sem. I +9% a/a); "
        "din 2031: potențial real ~2,5% (CF) + deflator ~2,5%",
        "Calculat: dobânzi 2026 estimate / stoc ESA la începutul anului (S&P: 5,6%); "
        "apoi converge spre randamentul pieței",
        "10 ani lei ~7,6% (sept.–oct. 2026); licitații oct. 6,81-7,18%; ipoteză de scădere cu dezinflația",
        "Scadențe ~13% + finanțarea deficitului; ~81% din datorie cu dobândă fixă",
        "2026: prefinanțarea SAFE (2,502 mld. €, aug. 2026); apoi convenția DSA CE; reziduu "
        "istoric +1,2 pp (2024), +0,8 pp (2025); sensibilitate 0,5 / 1,0 pp/an din 2027",
        "MF, Raport datoria publică 07.2026: ~51% lei, ~39% EUR, ~10% USD",
        "Eurostat, ert_bil_eur_a",
        "Eurostat, medii lunare ian.–sep. 2026 (ert_bil_eur_m); oct.–dec. la nivelul din oct. (~5,34)",
        "Față de 2025", "Diferențial de inflație față de zona euro; media 2005-2025: 1,7%/an",
        "~2/3 din anul 2009 (+15,1%); saltul datoriei apropiat de testul de stres CF",
        "Variații anuale EUR/RON 2006-2024 (Eurostat)",
        "CF: deficit 2027 realist ~5,5% vs ținta 5,2% (ESA); PSD: fără taxe noi, pensii indexate",
    ],
})

rezumat = pd.DataFrame({
    "Scenariu": list(S.keys()),
    "Datorie 2030 (% PIB)": [df.loc[df["an"] == 2030, "datorie_%pib"].iloc[0] for df in S.values()],
    "Datorie 2035 (% PIB)": [df.loc[df["an"] == 2035, "datorie_%pib"].iloc[0] for df in S.values()],
    "Datorie 2040 (% PIB)": [df.loc[df["an"] == 2040, "datorie_%pib"].iloc[0] for df in S.values()],
    "Dobânzi 2035 (% PIB)": [df.loc[df["an"] == 2035, "interes_%pib"].iloc[0] for df in S.values()],
})

with pd.ExcelWriter(XLSX, engine="xlsxwriter") as xw:
    rezumat.to_excel(xw, sheet_name="Rezumat", index=False)
    parametri.to_excel(xw, sheet_name="Parametri", index=False)
    df_fan.to_excel(xw, sheet_name="S2 fan chart", index=False)
    for nume, df in S.items():
        df.to_excel(xw, sheet_name=nume.split()[0], index=False)
    # foi noi: feedback macro al consolidării
    fb = pd.concat([efecte(m=m).assign(multiplicator=m)
                    for m in (0.4, 0.75, 1.2)], ignore_index=True)
    fb.to_excel(xw, sheet_name="Feedback macro", index=False)
    tr_fb = pd.concat([traseu_datorie_cu_feedback(m=m) for m in (0.4, 0.75, 1.2)],
                      ignore_index=True)
    tr_fb.to_excel(xw, sheet_name="Datorie cu feedback", index=False)
    # foi noi: șoc energetic
    energie = pd.concat([ruleaza_soc(nume) for nume in SOC], ignore_index=True)
    energie.to_excel(xw, sheet_name="Șoc energetic", index=False)
    # foaie nouă: efectul cursului de schimb asupra datoriei (S2)
    curs = pd.DataFrame({nume: df.set_index("an")["datorie_%pib"]
                         for nume, df in curs_variante_s2().items()})
    curs.to_excel(xw, sheet_name="Curs de schimb S2")
    pd.DataFrame({f"stoc-flux {v:g} pp/an din 2027": df.set_index("an")["datorie_%pib"]
                  for v, df in sensibilitate_stoc_flux().items()}).to_excel(
        xw, sheet_name="Stoc-flux S2")
    # foaie nouă: bugetul 2027 relaxat (S7) și variante
    pd.DataFrame({nume: df.set_index("an")["datorie_%pib"]
                  for nume, df in s7_variante().items()}).to_excel(
        xw, sheet_name="S7 variante")
    # foi noi: șomaj și retragerea investitorilor străini (dezindustrializare)
    baza_s2 = dez._baza_s2()
    dez.toate(baza_s2).to_excel(xw, sheet_name="Dezindustrializare", index=False)
    pd.DataFrame({n.split(" ", 1)[0]: dez.descompunere(n, baza_s2)
                  for n in dez.SOC if not n.startswith("D0")}).to_excel(
        xw, sheet_name="Dezindustrializare canale")
    # foi noi: spațiul fiscal pentru cheltuieli noi (primării, firme, pensii, salarii)
    sf.tabel_baze().to_excel(xw, sheet_name="Spațiu fiscal baze", index=False)
    sf.tabel_spatiu_maxim().to_excel(xw, sheet_name="Spațiu fiscal criterii", index=False)
    sf.tabel_pachete().to_excel(xw, sheet_name="Spațiu fiscal pachete", index=False)
    sf.tabel_pensii_salarii().to_excel(xw, sheet_name="Pensii și salarii", index=False)

    wb = xw.book
    ws = wb.add_worksheet("Grafic datorie")
    # datele pentru grafic: an + un scenariu pe coloană
    ani = list(S.values())[0]["an"].values
    ws.write_row(0, 0, ["An"] + [n.split()[0] for n in S])
    for i, an in enumerate(ani):
        ws.write(i + 1, 0, int(an))
        for j, df in enumerate(S.values()):
            ws.write(i + 1, j + 1, float(df["datorie_%pib"].iloc[i]))
    chart = wb.add_chart({"type": "line"})
    for j, nume in enumerate(S):
        chart.add_series({
            "name": nume.split()[0],
            "categories": ["Grafic datorie", 1, 0, len(ani), 0],
            "values": ["Grafic datorie", 1, j + 1, len(ani), j + 1],
            "line": {"color": CULORI_SCENARII[nume.split()[0]], "width": 2},
        })
    chart.set_title({"name": "Datoria publică (% din PIB) — scenarii"})
    chart.set_x_axis({"name": "An"})
    chart.set_y_axis({"name": "% din PIB"})
    chart.set_size({"width": 760, "height": 460})
    ws.insert_chart("H2", chart)

print("Scris:", XLSX)
print(rezumat.to_string(index=False, float_format=lambda x: f"{x:6.2f}"))
