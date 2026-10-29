"""Aplicación de escritorio para transcribir audios a Markdown y PDF."""

import os
import sys

# En la aplicación empaquetada sin consola, stdout/stderr son None y cualquier print
# (o las barras de progreso de las descargas) haría fallar el programa.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

import queue
import subprocess
import threading
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

from faster_whisper import WhisperModel
from faster_whisper.utils import download_model

from md_a_pdf import md_a_pdf
from transcribir import EXTENSIONES, transcribir

MODELOS = {
    "Rápido (base)": "base",
    "Equilibrado (small)": "small",
    "Preciso (medium)": "medium",
    "Muy preciso (turbo)": "turbo",
}
IDIOMAS = {
    "Detectar automáticamente": None,
    "Español": "es",
    "Inglés": "en",
    "Portugués": "pt",
    "Francés": "fr",
    "Italiano": "it",
    "Alemán": "de",
}


def abrir_en_explorador(ruta: Path):
    if sys.platform == "win32":
        os.startfile(ruta)
    elif sys.platform == "darwin":
        subprocess.run(["open", ruta])
    else:
        subprocess.run(["xdg-open", ruta])


class Aplicacion(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transcriptor de audios")
        self.minsize(560, 520)
        self.audios: list[Path] = []
        self.carpeta_salida: Path | None = None
        self.ultima_carpeta: Path | None = None
        self.mensajes: queue.Queue = queue.Queue()
        self.modelos_cargados: dict[str, WhisperModel] = {}

        self._construir_interfaz()
        self.after(100, self._procesar_mensajes)

    # ---------- Interfaz ----------

    def _construir_interfaz(self):
        raiz = ttk.Frame(self, padding=16)
        raiz.pack(fill="both", expand=True)
        raiz.columnconfigure(0, weight=1)

        # Lista de audios
        marco_audios = ttk.LabelFrame(raiz, text="Audios (arrastra aquí archivos o carpetas)", padding=8)
        marco_audios.grid(row=0, column=0, sticky="nsew")
        raiz.rowconfigure(0, weight=1)
        marco_audios.columnconfigure(0, weight=1)
        marco_audios.rowconfigure(0, weight=1)

        self.lista = tk.Listbox(marco_audios, height=8, selectmode="extended", activestyle="none")
        self.lista.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.color_lista = self.lista.cget("background")
        self.lista.drop_target_register(DND_FILES)
        self.lista.dnd_bind("<<DropEnter>>", self._arrastre_entra)
        self.lista.dnd_bind("<<DropLeave>>", self._arrastre_sale)
        self.lista.dnd_bind("<<Drop>>", self._soltar_audios)
        ttk.Button(marco_audios, text="Agregar audios…", command=self._agregar_audios).grid(
            row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Button(marco_audios, text="Quitar seleccionados", command=self._quitar_audios).grid(
            row=1, column=1, sticky="e", pady=(8, 0), padx=(8, 0))
        ttk.Button(marco_audios, text="Vaciar", command=self._vaciar_audios).grid(
            row=1, column=2, sticky="e", pady=(8, 0), padx=(8, 0))

        # Opciones
        marco_opciones = ttk.LabelFrame(raiz, text="Opciones", padding=8)
        marco_opciones.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        marco_opciones.columnconfigure(1, weight=1)

        ttk.Label(marco_opciones, text="Calidad:").grid(row=0, column=0, sticky="w")
        self.modelo = tk.StringVar(value="Equilibrado (small)")
        ttk.Combobox(marco_opciones, textvariable=self.modelo, values=list(MODELOS),
                     state="readonly").grid(row=0, column=1, sticky="ew", padx=(8, 0))

        ttk.Label(marco_opciones, text="Idioma:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.idioma = tk.StringVar(value="Español")
        ttk.Combobox(marco_opciones, textvariable=self.idioma, values=list(IDIOMAS),
                     state="readonly").grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))

        ttk.Label(marco_opciones, text="Guardar en:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        fila_salida = ttk.Frame(marco_opciones)
        fila_salida.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))
        fila_salida.columnconfigure(0, weight=1)
        self.texto_salida = tk.StringVar(value="La misma carpeta de cada audio")
        ttk.Label(fila_salida, textvariable=self.texto_salida).grid(row=0, column=0, sticky="w")
        ttk.Button(fila_salida, text="Cambiar…", command=self._elegir_salida).grid(row=0, column=1)

        self.generar_pdf = tk.BooleanVar(value=True)
        self.con_tiempos = tk.BooleanVar(value=True)
        ttk.Checkbutton(marco_opciones, text="Generar también PDF", variable=self.generar_pdf).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Checkbutton(marco_opciones, text="Incluir marcas de tiempo", variable=self.con_tiempos).grid(
            row=4, column=0, columnspan=2, sticky="w")

        # Progreso y acciones
        marco_progreso = ttk.Frame(raiz)
        marco_progreso.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        marco_progreso.columnconfigure(0, weight=1)

        self.estado = tk.StringVar(value="Arrastra uno o más audios a la lista para comenzar.")
        ttk.Label(marco_progreso, textvariable=self.estado, wraplength=520).grid(
            row=0, column=0, columnspan=2, sticky="w")
        self.barra = ttk.Progressbar(marco_progreso, maximum=1.0)
        self.barra.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        self.boton_abrir = ttk.Button(marco_progreso, text="Abrir carpeta", state="disabled",
                                      command=lambda: abrir_en_explorador(self.ultima_carpeta))
        self.boton_abrir.grid(row=2, column=0, sticky="w", pady=(12, 0))
        self.boton_transcribir = ttk.Button(marco_progreso, text="Transcribir", command=self._iniciar)
        self.boton_transcribir.grid(row=2, column=1, sticky="e", pady=(12, 0))

    def _agregar_audios(self):
        tipos = " ".join(f"*{ext}" for ext in sorted(EXTENSIONES))
        rutas = filedialog.askopenfilenames(
            title="Selecciona los audios",
            filetypes=[("Audios", tipos), ("Todos los archivos", "*.*")])
        self._sumar_audios(map(Path, rutas))

    def _sumar_audios(self, rutas):
        for ruta in rutas:
            if ruta not in self.audios:
                self.audios.append(ruta)
                self.lista.insert("end", ruta.name)

    def _arrastre_entra(self, evento):
        self.lista.configure(background="#dbeafe")
        return evento.action

    def _arrastre_sale(self, evento):
        self.lista.configure(background=self.color_lista)
        return evento.action

    def _soltar_audios(self, evento):
        self.lista.configure(background=self.color_lista)
        rutas = []
        for ruta in map(Path, self.tk.splitlist(evento.data)):
            if ruta.is_dir():
                rutas += sorted(p for p in ruta.iterdir() if p.suffix.lower() in EXTENSIONES)
            elif ruta.suffix.lower() in EXTENSIONES:
                rutas.append(ruta)
        if rutas:
            self._sumar_audios(rutas)
        else:
            self.estado.set("Los archivos soltados no son audios compatibles.")
        return evento.action

    def _quitar_audios(self):
        for indice in reversed(self.lista.curselection()):
            self.lista.delete(indice)
            del self.audios[indice]

    def _vaciar_audios(self):
        self.lista.delete(0, "end")
        self.audios.clear()

    def _elegir_salida(self):
        carpeta = filedialog.askdirectory(title="Carpeta donde guardar las transcripciones")
        if carpeta:
            self.carpeta_salida = Path(carpeta)
            self.texto_salida.set(str(self.carpeta_salida))

    # ---------- Transcripción en segundo plano ----------

    def _iniciar(self):
        if not self.audios:
            messagebox.showinfo("Transcriptor de audios", "Primero agrega al menos un audio.")
            return
        self.boton_transcribir.configure(state="disabled")
        self.boton_abrir.configure(state="disabled")
        self.barra["value"] = 0
        opciones = {
            "audios": list(self.audios),
            "modelo": MODELOS[self.modelo.get()],
            "idioma": IDIOMAS[self.idioma.get()],
            "pdf": self.generar_pdf.get(),
            "tiempos": self.con_tiempos.get(),
            "salida": self.carpeta_salida,
        }
        threading.Thread(target=self._trabajar, args=(opciones,), daemon=True).start()

    def _trabajar(self, op):
        enviar = self.mensajes.put
        try:
            modelo = self.modelos_cargados.get(op["modelo"])
            if modelo is None:
                try:
                    download_model(op["modelo"], local_files_only=True)
                    enviar(("estado", "Cargando el modelo…"))
                except Exception:
                    enviar(("estado", "Descargando el modelo de reconocimiento de voz. "
                                      "Solo ocurre la primera vez y puede tardar varios minutos…"))
                modelo = WhisperModel(op["modelo"], device="cpu", compute_type="int8")
                self.modelos_cargados[op["modelo"]] = modelo

            total = len(op["audios"])
            for n, audio in enumerate(op["audios"]):
                destino = op["salida"] or audio.parent
                destino.mkdir(parents=True, exist_ok=True)
                enviar(("estado", f"Transcribiendo {audio.name} ({n + 1} de {total})…"))

                def progreso(fraccion, n=n):
                    enviar(("progreso", (n + fraccion) / total))

                archivo_md = destino / f"{audio.stem}.md"
                archivo_md.write_text(
                    transcribir(modelo, audio, op["idioma"], op["tiempos"], progreso), encoding="utf-8")
                if op["pdf"]:
                    md_a_pdf(archivo_md)
                self.ultima_carpeta = destino
                enviar(("progreso", (n + 1) / total))

            enviar(("fin", f"Listo: {total} audio{'s' if total > 1 else ''} transcrito{'s' if total > 1 else ''}."))
        except Exception as error:
            traceback.print_exc()
            enviar(("error", str(error)))

    def _procesar_mensajes(self):
        try:
            while True:
                tipo, valor = self.mensajes.get_nowait()
                if tipo == "estado":
                    self.estado.set(valor)
                elif tipo == "progreso":
                    self.barra["value"] = valor
                elif tipo == "fin":
                    self.estado.set(valor)
                    self.boton_transcribir.configure(state="normal")
                    self.boton_abrir.configure(state="normal")
                elif tipo == "error":
                    self.estado.set("Ocurrió un error.")
                    self.boton_transcribir.configure(state="normal")
                    if self.ultima_carpeta:
                        self.boton_abrir.configure(state="normal")
                    messagebox.showerror("Transcriptor de audios", f"No se pudo completar la transcripción:\n\n{valor}")
        except queue.Empty:
            pass
        self.after(100, self._procesar_mensajes)


if __name__ == "__main__":
    Aplicacion().mainloop()
