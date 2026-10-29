"""Transcribe archivos de audio a Markdown usando Whisper (faster-whisper) en local."""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from faster_whisper import WhisperModel

from md_a_pdf import md_a_pdf

EXTENSIONES = {".ogg", ".opus", ".mp3", ".m4a", ".wav", ".flac", ".aac", ".webm", ".mp4"}


def formatear_tiempo(segundos: float) -> str:
    h, resto = divmod(int(segundos), 3600)
    m, s = divmod(resto, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def agrupar_parrafos(segmentos, pausa: float = 1.5, max_caracteres: int = 600):
    """Une segmentos en párrafos, cortando en pausas largas o cuando el texto crece mucho."""
    parrafos, actual = [], []
    for seg in segmentos:
        if actual and (
            seg.start - actual[-1].end > pausa
            or sum(len(s.text) for s in actual) > max_caracteres
        ):
            parrafos.append(actual)
            actual = []
        actual.append(seg)
    if actual:
        parrafos.append(actual)
    return parrafos


def transcribir(modelo: WhisperModel, ruta: Path, idioma: str | None, con_tiempos: bool,
                progreso=None) -> str:
    """Devuelve la transcripción en Markdown. `progreso`, si se indica, recibe un valor entre 0 y 1."""
    inicio = time.time()
    generador, info = modelo.transcribe(str(ruta), language=idioma, vad_filter=True, beam_size=5)
    segmentos = []
    for seg in generador:
        segmentos.append(seg)
        if progreso and info.duration:
            progreso(min(seg.end / info.duration, 1.0))
    duracion_proceso = time.time() - inicio

    lineas = [
        f"# Transcripción: {ruta.stem}",
        "",
        f"- **Archivo:** `{ruta.name}`",
        f"- **Duración:** {formatear_tiempo(info.duration)}",
        f"- **Idioma detectado:** {info.language} ({info.language_probability:.0%})",
        f"- **Fecha de transcripción:** {datetime.now():%Y-%m-%d %H:%M}",
        f"- **Tiempo de proceso:** {duracion_proceso:.1f} s",
        "",
        "---",
        "",
    ]

    if not segmentos:
        lineas.append("_No se detectó voz en el audio._")
    for parrafo in agrupar_parrafos(segmentos):
        texto = " ".join(s.text.strip() for s in parrafo)
        if con_tiempos:
            texto = f"**[{formatear_tiempo(parrafo[0].start)}]** {texto}"
        lineas += [texto, ""]

    return "\n".join(lineas).rstrip() + "\n"


def recolectar_audios(entradas: list[str]) -> list[Path]:
    audios = []
    for entrada in entradas:
        ruta = Path(entrada).expanduser()
        if ruta.is_dir():
            audios += sorted(p for p in ruta.iterdir() if p.suffix.lower() in EXTENSIONES)
        elif ruta.is_file():
            audios.append(ruta)
        else:
            print(f"Aviso: no existe '{entrada}', se omite.", file=sys.stderr)
    return audios


def main():
    parser = argparse.ArgumentParser(description="Transcribe audios a archivos .md")
    parser.add_argument("entradas", nargs="+", help="Archivos de audio o carpetas que los contengan")
    parser.add_argument("-o", "--salida", help="Carpeta de salida (por defecto, junto a cada audio)")
    parser.add_argument("-m", "--modelo", default="small",
                        help="Modelo de Whisper: tiny, base, small, medium, large-v3, turbo (por defecto: small)")
    parser.add_argument("-i", "--idioma", default=None,
                        help="Código de idioma, por ejemplo 'es' (por defecto: detección automática)")
    parser.add_argument("--sin-tiempos", action="store_true", help="No incluir marcas de tiempo")
    parser.add_argument("--pdf", action="store_true", help="Generar también un .pdf a partir del .md")
    parser.add_argument("-d", "--dispositivo", default="cpu", choices=["cpu", "cuda"],
                        help="cpu (por defecto) o cuda para GPU NVIDIA con CUDA 12 y cuDNN 9 instalados")
    args = parser.parse_args()

    audios = recolectar_audios(args.entradas)
    if not audios:
        sys.exit("No se encontraron audios para transcribir.")

    print(f"Cargando modelo '{args.modelo}'...")
    tipo_computo = "float16" if args.dispositivo == "cuda" else "int8"
    modelo = WhisperModel(args.modelo, device=args.dispositivo, compute_type=tipo_computo)

    for audio in audios:
        destino = Path(args.salida).expanduser() if args.salida else audio.parent
        destino.mkdir(parents=True, exist_ok=True)
        archivo_md = destino / f"{audio.stem}.md"
        print(f"Transcribiendo {audio.name}...")
        archivo_md.write_text(transcribir(modelo, audio, args.idioma, not args.sin_tiempos), encoding="utf-8")
        print(f"  -> {archivo_md}")
        if args.pdf:
            print(f"  -> {md_a_pdf(archivo_md)}")


if __name__ == "__main__":
    main()
