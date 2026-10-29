# Configuración de PyInstaller. Generar con:  uv run pyinstaller transcriptor.spec
# - Windows: dist/Transcriptor.exe (un único archivo)
# - macOS:   dist/Transcriptor.app

import os
import sys

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for paquete in ("faster_whisper", "ctranslate2", "onnxruntime", "av", "tokenizers", "fpdf", "tkinterdnd2"):
    d, b, h = collect_all(paquete)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["app.py"],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    excludes=["matplotlib", "IPython", "pytest"],
)
pyz = PYZ(a.pure)

if sys.platform == "win32":
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas,
        name="Transcriptor",
        console=False,
        upx=False,
    )
else:
    exe = EXE(pyz, a.scripts, exclude_binaries=True, name="Transcriptor", console=False, upx=False)
    coll = COLLECT(exe, a.binaries, a.datas, name="Transcriptor", upx=False)
    app = BUNDLE(
        coll,
        name="Transcriptor.app",
        bundle_identifier="com.mediahuella.transcriptor",
        info_plist={"NSHighResolutionCapable": True, "CFBundleShortVersionString": os.environ.get("APP_VERSION", "0.1.0")},
    )
