# Poate România să „plătească” deficitul?

Analiză de sustenabilitate a datoriei publice a României (2026–2040): raportul, modelele
Python, rezultatele și sub-rapoartele tematice pe care se sprijină.

- **Articolul web:** <https://infuscy.github.io/romania-deficit/>
- **Raportul:** [`Raport_Romania_Deficit_Sustenabilitate.md`](Raport_Romania_Deficit_Sustenabilitate.md)
  (și în format [PDF](Raport_Romania_Deficit_Sustenabilitate.pdf) și
  [DOCX](Raport_Romania_Deficit_Sustenabilitate.docx))
- **Ediția:** 17 octombrie 2026
- **Autor:** Buse Florin-Emilian

Repo-ul este copia publică a proiectului și se actualizează la fiecare ediție a raportului.

## Conținut

| Fișier sau dosar | Ce conține |
|---|---|
| [`Raport_Romania_Deficit_Sustenabilitate.md`](Raport_Romania_Deficit_Sustenabilitate.md) | raportul principal, sursa pentru PDF, DOCX și articolul web |
| [`Raport_fiscal_Romania_2024-2026.md`](Raport_fiscal_Romania_2024-2026.md) | execuția bugetară și datoria publică, 2023–2026 |
| [`Raport_piata_titluri_de_stat_RO_2025-2026.md`](Raport_piata_titluri_de_stat_RO_2025-2026.md) | piața titlurilor de stat |
| [`Raport_efecte_macro_consolidare_2025-2026.md`](Raport_efecte_macro_consolidare_2025-2026.md) | efectele consolidării fiscale asupra economiei și consumului |
| [`raport_energie_petrol_2025_2026.md`](raport_energie_petrol_2025_2026.md) | șocul energetic: petrol, gaze, electricitate, Cernavodă |
| [`Raport_spatiu_fiscal_2027-2030.md`](Raport_spatiu_fiscal_2027-2030.md) | spațiul fiscal pentru cheltuieli noi (primării, firme, pensii, salarii), 2027–2030 |
| [`Raport_sustenabilitate_datorie_deficit_Romania.md`](Raport_sustenabilitate_datorie_deficit_Romania.md) | prognozele instituționale (cercetare documentară) |
| [`_research/`](_research/) | dosare proprii: știrile care pot schimba parametrii modelelor, multiplicatorii fiscali, șomajul și investițiile străine |
| [`model/`](model/) | modelele Python, caietul [`Model_DSA_Romania.xlsx`](model/Model_DSA_Romania.xlsx), seriile CSV ([`outputs/`](model/outputs/)) și graficele ([`figuri/`](model/figuri/)) |
| [`tools/`](tools/) | convertoarele raport → DOCX și PDF și extractoarele de text din PDF |

## Cum se rulează

Python 3 cu `numpy`, `pandas`, `matplotlib`, `python-docx`, `openpyxl` și `xlsxwriter`.
Modelele se rulează din `model/`, pentru că se importă unul pe altul:

```bash
cd model
python model_dsa.py                 # scenariile S1–S7, simularea stocastică, figurile 1–5 și 10
python model_macro_feedback.py      # efectul consolidării asupra economiei (multiplicatori)
python model_energie_soc.py         # șocul energetic (E0–E4)
python model_dezindustrializare.py  # șomajul și retragerea investitorilor străini (D0–D3)
python model_spatiu_fiscal.py       # spațiul pentru cheltuieli noi (B1–B4)
python raport_excel.py              # Model_DSA_Romania.xlsx
```

Raportul DOCX și PDF se generează din rădăcina repo-ului cu
`python tools/genereaza_raport.py`; PDF-ul are nevoie de Microsoft Edge sau Google Chrome.

## Surse

Cifrele preluate din documente sunt referențiate în rapoarte cu [S1], [S2]…, iar lista de
surse dă linkul original al fiecăruia. Copiile documentelor altor instituții (Ministerul
Finanțelor, BNR, Consiliul Fiscal, Comisia și Consiliul UE, FMI, BCR), folosite la
verificarea cifrelor, nu sunt republicate aici, pentru că unele nu permit redistribuirea.

## Licență

- Textele, datele (CSV, Excel) și graficele: Creative Commons Atribuire 4.0 Internațional
  (CC BY 4.0), vezi [`LICENSE-continut.md`](LICENSE-continut.md).
- Codul (`model/*.py`, `tools/*.py`): MIT, vezi [`LICENSE`](LICENSE).

## Transparență

Analiza a fost redactată cu asistența unui sistem de inteligență artificială; cifrele au fost
verificate pe surse primare, iar textul a fost revizuit și corectat de autor. Este o analiză
independentă, cu scop informativ: nu este o prognoză oficială și nici consiliere de
investiții. Rezultatele marcate „model propriu” provin din modelele din acest repo.
