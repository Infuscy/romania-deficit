# -*- coding: utf-8 -*-
"""Parser Markdown comun pentru md2docx.py și md2pdf.py.

Ambele convertoare folosesc aceleași reguli, ca DOCX-ul și PDF-ul să nu
divergă. Subsetul suportat: titluri (#–####), paragrafe, liste (-, 1.),
tabele pipe, imagini, blocuri de cod, **bold**, *italic*, `code`,
[text](url) și referințe [S1] (legate către URL-ul din definițiile
`[S1]: url` din secțiunea „Surse").

Tot aici este lista fișierelor publicate în repo-ul public (FISIERE_PUBLICE,
copiate de tools/publica_github.py) și url_public(), care transformă linkurile
către fișiere locale în linkuri GitHub, ca să funcționeze în PDF, DOCX și pe web.
"""
import fnmatch
import re


def citeste(md_path):
    with open(md_path, encoding="utf-8") as f:
        return f.read()


def definitii_referinte(text):
    """Colectează definițiile de referințe `[S1]: url`."""
    refdefs = {}
    for m in re.finditer(r"^\[(S\d+)\]:\s*(\S+)\s*$", text, re.M):
        refdefs[m.group(1)] = m.group(2)
    return refdefs


# Repo-ul public: rapoartele, modelele, rezultatele și convertoarele. Documentele altor
# instituții (pdf/, downloads/, date/pdf/, PDF-urile și textele din _research/) rămân
# private: unele nu permit redistribuirea, iar sursele dau linkul original.
REPO_PUBLIC = "https://github.com/Infuscy/romania-deficit"
FISIERE_PUBLICE = (
    "Raport_Romania_Deficit_Sustenabilitate.md",
    "Raport_Romania_Deficit_Sustenabilitate.pdf",
    "Raport_Romania_Deficit_Sustenabilitate.docx",
    "Raport_efecte_macro_consolidare_2025-2026.md",
    "Raport_fiscal_Romania_2024-2026.md",
    "Raport_piata_titluri_de_stat_RO_2025-2026.md",
    "Raport_spatiu_fiscal_2027-2030.md",
    "Raport_sustenabilitate_datorie_deficit_Romania.md",
    "raport_energie_petrol_2025_2026.md",
    "_research/raport_consolidare_fiscala_2025-2026.md",
    "_research/somaj_isd_2026.md",
    "_research/stiri_*.md",
    "model/*.py",
    "model/Model_DSA_Romania.xlsx",
    "model/outputs/*.csv",
    "model/figuri/*.png",
    "tools/md_comun.py",
    "tools/md2docx.py",
    "tools/md2pdf.py",
    "tools/genereaza_raport.py",
    "tools/pdf_text.py",
    "tools/pdf_text2.py",
)
DOSARE_PUBLICE = ("model", "model/outputs", "model/figuri", "tools")


def _cale_relativa(cale):
    cale = cale.replace("\\", "/")
    return cale[2:] if cale.startswith("./") else cale


def este_public(cale):
    """True dacă fișierul (cale relativă la rădăcina proiectului) intră în repo-ul public."""
    cale = _cale_relativa(cale)
    return any(fnmatch.fnmatchcase(cale, tipar) for tipar in FISIERE_PUBLICE)


def url_public(url):
    """URL-ul pentru un link: neschimbat pentru web, ancore și e-mail; pentru un fișier
    sau un dosar local, linkul din repo-ul public dacă este publicat, altfel None (linkul
    devine text simplu, pentru că un link relativ nu duce nicăieri în afara proiectului)."""
    if not url or url.startswith(("http://", "https://", "#", "mailto:")):
        return url
    cale = _cale_relativa(url.split("#")[0])
    dosar = cale.rstrip("/")
    if dosar in DOSARE_PUBLICE:
        return f"{REPO_PUBLIC}/tree/main/{dosar}"
    if cale.endswith("/") or not este_public(cale):
        return None
    return f"{REPO_PUBLIC}/blob/main/{cale}"


INLINE = re.compile(
    r"(\*\*.+?\*\*"          # bold
    r"|\*[^*]+?\*"           # italic
    r"|`[^`]+?`"             # code
    r"|\[[^\]]+\]\([^)]+\)"  # link
    r"|\[S\d+\])")           # ref


def tokeni_inline(s, refdefs):
    """Împarte un text în tokeni inline:
    ("text", s) / ("bold", s) / ("italic", s) / ("code", s) /
    ("link", eticheta, url) / ("ref", eticheta, url sau None).
    Conținutul bold/italic nu este procesat recursiv."""
    pos = 0
    for m in INLINE.finditer(s):
        if m.start() > pos:
            yield ("text", s[pos:m.start()])
        tok = m.group(0)
        if tok.startswith("**") and tok.endswith("**"):
            yield ("bold", tok[2:-2])
        elif tok.startswith("`") and tok.endswith("`"):
            yield ("code", tok[1:-1])
        elif tok.startswith("[") and "](" in tok:
            mm = re.match(r"\[([^\]]+)\]\(([^)]+)\)", tok)
            yield ("link", mm.group(1), mm.group(2))
        elif re.fullmatch(r"\[S\d+\]", tok):
            yield ("ref", tok, refdefs.get(tok[1:-1]))
        elif tok.startswith("*") and tok.endswith("*"):
            yield ("italic", tok[1:-1])
        pos = m.end()
    if pos < len(s):
        yield ("text", s[pos:])


def blocuri(text):
    """Împarte documentul în blocuri (tip, payload). Paragrafele înfășurate pe
    mai multe linii se unesc; liniile de continuare se lipesc de elementul de
    listă anterior, cu excepția celor neindentate aflate după o linie goală,
    care încep un paragraf nou. Tipuri: par, head, table, img, bullet, numar, cod."""
    rez = []
    buf_par = []
    cod_curent = None
    dupa_gol = False      # linia anterioară a fost goală

    def flush_par():
        if buf_par:
            rez.append(("par", " ".join(x.strip() for x in buf_par)))
            buf_par.clear()

    for linie in text.split("\n"):
        stripped = linie.strip()
        if stripped.startswith("```"):
            if cod_curent is None:
                flush_par()
                cod_curent = []
            else:
                rez.append(("cod", "\n".join(cod_curent)))
                cod_curent = None
            continue
        if cod_curent is not None:
            cod_curent.append(linie)
            continue
        if not stripped:
            flush_par()
            dupa_gol = True
            continue
        gol_anterior, dupa_gol = dupa_gol, False
        if re.fullmatch(r"\[S\d+\]:\s*\S+\s*", stripped):
            continue
        if stripped.startswith(("#", "|", "- ", "* ", "![", "1. ")) or \
           re.match(r"\d+\.\s+", stripped) or stripped == "---":
            flush_par()
            if stripped.startswith("#"):
                rez.append(("head", stripped))
            elif stripped.startswith("|"):
                if rez and rez[-1][0] == "table":
                    rez[-1][1].append(stripped)
                else:
                    rez.append(("table", [stripped]))
            elif stripped.startswith("!["):
                rez.append(("img", stripped))
            elif stripped == "---":
                pass
            else:
                rez.append(("bullet" if stripped.startswith(("- ", "* ")) else "numar",
                            [stripped]))
            continue
        # linie de continuare: adaugă la blocul anterior de listă sau la paragraf.
        # După o linie goală, o linie neindentată începe un paragraf nou
        # (regula Markdown); una indentată continuă elementul de listă.
        # Odată început, paragraful își păstrează liniile.
        continua_lista = not buf_par and not (gol_anterior and not linie[:1].isspace())
        if rez and rez[-1][0] in ("bullet", "numar") and continua_lista:
            rez[-1][1].append(("cont", stripped))
        else:
            buf_par.append(stripped)
    flush_par()
    if cod_curent is not None:
        rez.append(("cod", "\n".join(cod_curent)))
    return rez


def titlu(payload):
    """('# Titlu') -> (nivel, text)."""
    nivel = len(payload) - len(payload.lstrip("#"))
    return nivel, payload.lstrip("#").strip()


def imagine(payload):
    """('![alt](cale)') -> (alt, cale) sau None."""
    m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", payload)
    return (m.group(1), m.group(2)) if m else None


def randuri_tabel(payload):
    """Rândurile unui tabel pipe, fără linia separator, ca liste de celule
    (completate până la numărul maxim de coloane)."""
    randuri = [r for r in payload if not re.fullmatch(r"\|[\s:\-|]+\|", r)]
    celule = [[c.strip() for c in r.strip("|").split("|")] for r in randuri]
    if not celule:
        return []
    n_col = max(len(r) for r in celule)
    return [r + [""] * (n_col - len(r)) for r in celule]


def element_lista(tip, payload):
    """Un element de listă -> (prefix, conținut). Prefixul este „1. " pentru
    listele numerotate și gol pentru cele cu puncte."""
    continut = []
    prefix = ""
    for item in payload:
        if isinstance(item, tuple):
            continut.append(item[1])
        else:
            m = re.match(r"(?:[-*]|\d+\.)\s+(.*)", item)
            if m:
                if tip == "numar":
                    prefix = re.match(r"(\d+\.)", item.strip()).group(1) + " "
                continut.append(m.group(1))
            else:
                continut.append(item)
    return prefix, " ".join(continut)
