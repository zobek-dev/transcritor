# Transcriptor de audios

Transcribe audios (`.ogg`, `.opus`, `.mp3`, `.m4a`, `.wav`, `.flac`, `.aac`, `.webm`, `.mp4`)
a Markdown y, opcionalmente, a PDF. Usa Whisper en local: el audio no se envía a ningún servicio.

No hace falta instalar ffmpeg.

## Instalación

Solo se necesita [uv](https://docs.astral.sh/uv/), que se encarga de instalar Python y las dependencias.

**macOS / Linux**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows** (en PowerShell)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Después de instalarlo, hay que cerrar y volver a abrir la terminal.

## Uso

Desde la carpeta del proyecto (los comandos son iguales en Windows, macOS y Linux):

```bash
# Solo el .md
uv run transcribir.py "mi audio.ogg"

# El .md y el .pdf
uv run transcribir.py "mi audio.ogg" --pdf

# Una carpeta entera, en español y con mejor calidad
uv run transcribir.py carpeta_audios --pdf -i es -m medium

# Convertir a PDF un .md que ya existe
uv run md_a_pdf.py "mi audio.md"
```

La primera ejecución descarga el modelo de Whisper (`small` pesa unos 480 MB; `medium`, unos 1,5 GB).

## Opciones

| Opción | Descripción |
| --- | --- |
| `-m`, `--modelo` | `tiny`, `base`, `small` (por defecto), `medium`, `large-v3`, `turbo`. Más grande = más preciso y más lento. |
| `-i`, `--idioma` | Código de idioma (`es`, `en`...). Por defecto se detecta solo. |
| `-o`, `--salida` | Carpeta de salida. Por defecto, junto a cada audio. |
| `--pdf` | Genera también el PDF. |
| `--sin-tiempos` | No incluye marcas de tiempo. |
| `-d`, `--dispositivo` | `cpu` (por defecto) o `cuda`. |

## Notas para Windows

- **GPU NVIDIA (opcional):** `-d cuda` es mucho más rápido, pero requiere CUDA 12 y cuDNN 9.
  Si aparece un error como `cublas64_12.dll not found`, hay que usar la CPU (opción por defecto) o instalar
  esas bibliotecas.
- **Aviso de symlinks al descargar el modelo:** es solo una advertencia de Hugging Face; el modelo se
  descarga igual. Para evitarla, se puede activar el "Modo de desarrollador" en la configuración de Windows.
- **Fuentes del PDF:** se usa Arial de `C:\Windows\Fonts`, que viene instalada por defecto.

## Instaladores (GitHub Actions)

El flujo `.github/workflows/instaladores.yml` genera:

- **Windows:** `Transcriptor-<versión>-windows-instalador.exe` (Inno Setup).
- **macOS:** `Transcriptor-<versión>-macos-arm64.dmg` (Apple Silicon) y `...-macos-intel.dmg`.

Para publicar una versión, se crea y sube una etiqueta; los instaladores quedan adjuntos a la release:

```bash
git tag v0.2.0
git push origin v0.2.0
```

También se puede ejecutar a mano desde la pestaña **Actions** (*Run workflow*); en ese caso los
instaladores quedan como artefactos de la ejecución, sin crear release.

Las aplicaciones no están firmadas: en macOS hay que abrirla la primera vez con clic derecho → **Abrir**,
y en Windows, en el aviso de SmartScreen, elegir **Más información → Ejecutar de todas formas**.
