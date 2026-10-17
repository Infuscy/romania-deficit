# -*- coding: utf-8 -*-
"""Generează DOCX și PDF din același Markdown, ca cele două să nu divergă.

Utilizare (din rădăcina proiectului):
    python tools/genereaza_raport.py [raport.md]

Implicit: Raport_Romania_Deficit_Sustenabilitate.md -> .docx + .pdf alături.
"""
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
md = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(TOOLS), "Raport_Romania_Deficit_Sustenabilitate.md")
baza = os.path.splitext(md)[0]

for script, iesire in (("md2docx.py", baza + ".docx"), ("md2pdf.py", baza + ".pdf")):
    subprocess.run([sys.executable, os.path.join(TOOLS, script), md, iesire], check=True)
