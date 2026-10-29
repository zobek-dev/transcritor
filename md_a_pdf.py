"""Convierte archivos Markdown a PDF (markdown -> HTML -> fpdf2)."""

import argparse
import os
import sys
from pathlib import Path

import markdown
from fpdf import FPDF

# Fuentes TTF del sistema para soportar acentos y signos (¿, ¡, ñ, —), por plataforma.
# Se usa el primer juego que exista completo; si ninguno existe, se usa Helvetica.
FUENTES_CANDIDATAS = [
    {  # macOS
        "": "/System/Library/Fonts/Supplemental/Arial.ttf",
        "B": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "I": "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
        "BI": "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
    },
    {  # Windows
        "": Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf",
        "B": Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arialbd.ttf",
        "I": Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "ariali.ttf",
        "BI": Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arialbi.ttf",
    },
    {  # Linux
        "": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "B": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "I": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
        "BI": "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
    },
]


def buscar_fuentes() -> dict | None:
    for fuentes in FUENTES_CANDIDATAS:
        if all(Path(f).exists() for f in fuentes.values()):
            return fuentes
    return None


def md_a_pdf(ruta_md: Path, ruta_pdf: Path | None = None) -> Path:
    ruta_pdf = ruta_pdf or ruta_md.with_suffix(".pdf")
    html = markdown.markdown(ruta_md.read_text(encoding="utf-8"))

    pdf = FPDF(format="A4")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(True, margin=20)
    pdf.set_title(ruta_md.stem)

    familia = "Helvetica"
    fuentes = buscar_fuentes()
    if fuentes:
        familia = "Sistema"
        for estilo, archivo in fuentes.items():
            pdf.add_font(familia, estilo, str(archivo))
    else:
        # Las fuentes base de PDF solo admiten latin-1.
        html = html.encode("latin-1", "replace").decode("latin-1")

    pdf.add_page()
    pdf.set_font(familia, size=11)
    pdf.write_html(html, font_family=familia)
    pdf.output(str(ruta_pdf))
    return ruta_pdf


def main():
    parser = argparse.ArgumentParser(description="Convierte archivos .md a .pdf")
    parser.add_argument("archivos", nargs="+", help="Archivos .md a convertir")
    args = parser.parse_args()

    for archivo in args.archivos:
        ruta = Path(archivo).expanduser()
        if not ruta.is_file():
            print(f"Aviso: no existe '{archivo}', se omite.", file=sys.stderr)
            continue
        print(f"  -> {md_a_pdf(ruta)}")


if __name__ == "__main__":
    main()
