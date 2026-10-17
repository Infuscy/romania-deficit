# -*- coding: utf-8 -*-
"""Convertor Markdown -> PDF pentru raportul de sustenabilitate.

Folosește același parser ca md2docx.py (md_comun.py), generează un HTML
autonom (imaginile încorporate ca base64) și îl tipărește în PDF cu un
browser Chromium în mod headless (Microsoft Edge sau Google Chrome).

Utilizare:
    python tools/md2pdf.py raport.md raport.pdf [--html raport.html] [--browser cale]

--html păstrează HTML-ul intermediar (util pentru depanarea aspectului).
Browserul se caută automat; poate fi forțat cu --browser sau cu variabila de
mediu BROWSER_PDF.
"""
import argparse
import base64
import html
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from md_comun import (citeste, definitii_referinte, tokeni_inline, blocuri,
                      titlu, imagine, randuri_tabel, element_lista, url_public)

BROWSERE = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]
BROWSERE_PATH = ["msedge", "google-chrome", "chromium", "chromium-browser", "chrome"]

# Aspect aliniat cu md2docx.py: A4, margini 2,0 / 1,8 cm, Calibri 10,5 pt,
# tabele cu grilă la 9 pt, imagini de 16 cm, linkuri #0563C1.
CSS = """
@page {
  size: A4;
  margin: 1.8cm 2.0cm;
  @bottom-center { content: counter(page) " / " counter(pages);
                   font-family: Calibri, Carlito, sans-serif; font-size: 8.5pt; color: #666; }
}
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: Calibri, Carlito, "Segoe UI", Arial, sans-serif; font-size: 10.5pt;
       line-height: 1.32; color: #111; margin: 0; }
p { margin: 0 0 6pt 0; text-align: left; }
a { color: #0563C1; text-decoration: underline; }
code { font-family: Consolas, "Courier New", monospace; font-size: 9.5pt; }
pre { font-family: "Courier New", monospace; font-size: 9.5pt; margin: 0 0 6pt 0.6cm;
      white-space: pre-wrap; break-inside: avoid; }
h1, h2, h3, h4 { color: #1F3864; break-after: avoid; page-break-after: avoid;
                 margin: 12pt 0 5pt 0; line-height: 1.2; }
h1.titlu { font-size: 24pt; font-weight: normal; color: #17365D;
           border-bottom: 1px solid #4F81BD; padding-bottom: 4pt; margin-top: 0; }
h1 { font-size: 16pt; }
h2 { font-size: 13.5pt; color: #2E74B5; }
h3 { font-size: 12pt; color: #2E74B5; }
h4 { font-size: 11pt; color: #2E74B5; font-style: italic; }
table { border-collapse: collapse; width: 100%; margin: 2pt 0 12pt 0; font-size: 9pt; }
th, td { border: 0.5pt solid #000; padding: 2pt 4pt; vertical-align: top; text-align: left; }
th { font-weight: bold; }
tr { break-inside: avoid; page-break-inside: avoid; }
thead { display: table-header-group; }
figure { margin: 6pt 0 10pt 0; text-align: center; break-inside: avoid; page-break-inside: avoid; }
figure img { width: 16cm; max-width: 100%; }
figcaption { font-style: italic; font-size: 9pt; margin-top: 2pt; }
ul { margin: 0 0 6pt 0; padding-left: 0.9cm; }
li { margin: 0 0 3pt 0; }
p.numar { margin-left: 0.9cm; text-indent: -0.5cm; }
"""


def inline(s, refdefs):
    out = []
    for tok in tokeni_inline(s, refdefs):
        tip = tok[0]
        if tip == "text":
            out.append(html.escape(tok[1]))
        elif tip == "bold":
            out.append(f"<strong>{html.escape(tok[1])}</strong>")
        elif tip == "italic":
            out.append(f"<em>{html.escape(tok[1])}</em>")
        elif tip == "code":
            out.append(f"<code>{html.escape(tok[1])}</code>")
        elif tip in ("link", "ref"):
            eticheta, url = tok[1], url_public(tok[2])
            if url:
                out.append(f'<a href="{html.escape(url, quote=True)}">{html.escape(eticheta)}</a>')
            else:
                out.append(html.escape(eticheta))
    return "".join(out)


def imagine_html(cale, base):
    p = os.path.normpath(os.path.join(base, cale))
    if not os.path.exists(p):
        return f"<p>[imagine lipsă: {html.escape(cale)}]</p>"
    mime = mimetypes.guess_type(p)[0] or "image/png"
    with open(p, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f'<img src="data:{mime};base64,{data}" alt="">'


def construieste_html(md_path):
    text = citeste(md_path)
    refdefs = definitii_referinte(text)
    base = os.path.dirname(os.path.abspath(md_path))
    corp = []
    titlu_doc = Path(md_path).stem
    first_heading = True
    lista_deschisa = False

    for tip, payload in blocuri(text):
        if tip != "bullet" and lista_deschisa:
            corp.append("</ul>")
            lista_deschisa = False
        if tip == "cod":
            corp.append(f"<pre>{html.escape(payload)}</pre>")
        elif tip == "par":
            corp.append(f"<p>{inline(payload, refdefs)}</p>")
        elif tip == "head":
            nivel, txt = titlu(payload)
            if nivel == 1 and first_heading:
                corp.append(f'<h1 class="titlu">{html.escape(txt)}</h1>')
                titlu_doc = txt
                first_heading = False
            else:
                n = min(nivel, 4)
                corp.append(f"<h{n}>{inline(txt, refdefs)}</h{n}>")
        elif tip == "img":
            img = imagine(payload)
            if img:
                alt, cale = img
                corp.append(f"<figure>{imagine_html(cale, base)}"
                            f"<figcaption>{html.escape(alt)}</figcaption></figure>")
        elif tip == "table":
            celule = randuri_tabel(payload)
            if celule:
                rows = ["<table><thead><tr>"
                        + "".join(f"<th>{inline(c, refdefs)}</th>" for c in celule[0])
                        + "</tr></thead><tbody>"]
                for row in celule[1:]:
                    rows.append("<tr>" + "".join(f"<td>{inline(c, refdefs)}</td>" for c in row)
                                + "</tr>")
                rows.append("</tbody></table>")
                corp.append("".join(rows))
        elif tip == "bullet":
            if not lista_deschisa:
                corp.append("<ul>")
                lista_deschisa = True
            _, continut = element_lista(tip, payload)
            corp.append(f"<li>{inline(continut, refdefs)}</li>")
        elif tip == "numar":
            prefix, continut = element_lista(tip, payload)
            corp.append(f'<p class="numar"><strong>{html.escape(prefix)}</strong>'
                        f"{inline(continut, refdefs)}</p>")
    if lista_deschisa:
        corp.append("</ul>")

    return ("<!doctype html>\n<html lang=\"ro\"><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(titlu_doc)}</title><style>{CSS}</style></head>"
            "<body>\n" + "\n".join(corp) + "\n</body></html>\n")


def gaseste_browser(explicit=None):
    candidati = [explicit, os.environ.get("BROWSER_PDF")] + BROWSERE
    for c in candidati:
        if c and os.path.exists(c):
            return c
    for nume in BROWSERE_PATH:
        c = shutil.which(nume)
        if c:
            return c
    return None


def tipareste_pdf(browser, html_path, pdf_path):
    pdf_path = os.path.abspath(pdf_path)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    # profil temporar: evită conflictul cu o instanță deschisă a browserului
    with tempfile.TemporaryDirectory(prefix="md2pdf_profil_") as profil:
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run",
               "--no-default-browser-check", "--disable-extensions",
               f"--user-data-dir={profil}", "--no-pdf-header-footer",
               "--generate-pdf-document-outline",
               f"--print-to-pdf={pdf_path}", Path(html_path).resolve().as_uri()]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        raise RuntimeError("Browserul nu a generat PDF-ul.\n"
                           f"cod {res.returncode}\n{res.stderr[-2000:]}")


def main():
    ap = argparse.ArgumentParser(description="Markdown -> PDF (prin HTML + Edge/Chrome headless)")
    ap.add_argument("md")
    ap.add_argument("pdf")
    ap.add_argument("--html", help="păstrează HTML-ul intermediar la această cale")
    ap.add_argument("--browser", help="calea către msedge.exe / chrome.exe")
    a = ap.parse_args()

    browser = gaseste_browser(a.browser)
    if not browser:
        sys.exit("Nu am găsit Microsoft Edge sau Google Chrome; folosiți --browser <cale>.")

    doc_html = construieste_html(a.md)
    if a.html:
        html_path = a.html
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(doc_html)
        tipareste_pdf(browser, html_path, a.pdf)
    else:
        with tempfile.TemporaryDirectory(prefix="md2pdf_") as tmp:
            html_path = os.path.join(tmp, "raport.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(doc_html)
            tipareste_pdf(browser, html_path, a.pdf)
    print("Scris:", a.pdf, f"({os.path.getsize(a.pdf) / 1024:.0f} KB)")
    print("Browser:", browser)


if __name__ == "__main__":
    main()
