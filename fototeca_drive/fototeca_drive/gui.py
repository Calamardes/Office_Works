"""Ventana sencilla para respaldar la fototeca en Google Drive."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .escaneo import fototeca_por_defecto
from .sincronizar import Opciones, respaldar

MODOS = {
    "Por año y mes (fecha de la foto)": "fecha",
    "Igual que mis carpetas": "original",
    "Todo en una sola carpeta": "plano",
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fototeca → Google Drive")
        self.geometry("760x560")
        self.minsize(560, 420)
        self.cola: queue.Queue = queue.Queue()
        self.detener = threading.Event()
        self.hilo: threading.Thread | None = None

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="Carpeta de fotos:").grid(row=0, column=0, sticky="w")
        self.origen = tk.StringVar(value=str(fototeca_por_defecto()))
        ttk.Entry(frm, textvariable=self.origen).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(frm, text="Elegir…", command=self.elegir).grid(row=0, column=2)

        ttk.Label(frm, text="Carpeta en Drive:").grid(row=1, column=0, sticky="w", pady=6)
        self.destino = tk.StringVar(value="Fototeca")
        ttk.Entry(frm, textvariable=self.destino).grid(row=1, column=1, sticky="ew", padx=6)

        ttk.Label(frm, text="Organizar:").grid(row=2, column=0, sticky="w")
        self.modo = tk.StringVar(value=next(iter(MODOS)))
        ttk.Combobox(frm, textvariable=self.modo, values=list(MODOS), state="readonly").grid(
            row=2, column=1, sticky="ew", padx=6
        )

        opciones = ttk.Frame(frm)
        opciones.grid(row=3, column=0, columnspan=3, sticky="w", pady=6)
        self.videos = tk.BooleanVar(value=False)
        self.simular = tk.BooleanVar(value=False)
        ttk.Checkbutton(opciones, text="Incluir videos", variable=self.videos).pack(side="left")
        ttk.Checkbutton(opciones, text="Solo simular (no sube nada)", variable=self.simular).pack(
            side="left", padx=16
        )

        botones = ttk.Frame(frm)
        botones.grid(row=4, column=0, columnspan=3, sticky="ew")
        self.btn_iniciar = ttk.Button(botones, text="Respaldar en Drive", command=self.iniciar)
        self.btn_iniciar.pack(side="left")
        self.btn_detener = ttk.Button(botones, text="Detener", command=self.parar, state="disabled")
        self.btn_detener.pack(side="left", padx=8)

        self.barra = ttk.Progressbar(frm, mode="determinate")
        self.barra.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(10, 2))
        self.lbl = ttk.Label(frm, text="")
        self.lbl.grid(row=6, column=0, columnspan=3, sticky="w")

        self.txt = tk.Text(frm, height=14, wrap="none")
        self.txt.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(6, 0))
        frm.rowconfigure(7, weight=1)

        self.after(100, self.atender_cola)
        self.protocol("WM_DELETE_WINDOW", self.cerrar)

    def elegir(self):
        d = filedialog.askdirectory(initialdir=self.origen.get() or str(Path.home()))
        if d:
            self.origen.set(d)

    def iniciar(self):
        origen = Path(self.origen.get()).expanduser()
        if not origen.is_dir():
            messagebox.showerror("Carpeta no válida", f"No existe la carpeta:\n{origen}")
            return
        op = Opciones(
            origen=origen,
            carpeta_drive=self.destino.get().strip() or "Fototeca",
            organizar=MODOS[self.modo.get()],
            incluir_videos=self.videos.get(),
            simulacion=self.simular.get(),
        )
        self.detener.clear()
        self.btn_iniciar.config(state="disabled")
        self.btn_detener.config(state="normal")
        self.txt.delete("1.0", "end")
        self.hilo = threading.Thread(target=self.trabajar, args=(op,), daemon=True)
        self.hilo.start()

    def trabajar(self, op: Opciones):
        log = lambda m: self.cola.put(("log", m))
        try:
            drive = None
            if not op.simulacion:
                from .drive import Drive, autenticar

                log("Conectando con Google Drive (se abrirá el navegador la primera vez)…")
                drive = Drive(autenticar())
            respaldar(op, drive=drive, log=log,
                      progreso=lambda h, t: self.cola.put(("prog", (h, t))),
                      detener=self.detener)
        except Exception as e:
            log(f"ERROR: {e}")
            self.cola.put(("error", str(e)))
        finally:
            self.cola.put(("fin", None))

    def atender_cola(self):
        try:
            while True:
                tipo, dato = self.cola.get_nowait()
                if tipo == "log":
                    self.txt.insert("end", dato + "\n")
                    self.txt.see("end")
                elif tipo == "prog":
                    hechos, total = dato
                    self.barra.config(maximum=max(total, 1), value=hechos)
                    self.lbl.config(text=f"{hechos} de {total} archivos revisados")
                elif tipo == "error":
                    messagebox.showerror("Error", dato)
                elif tipo == "fin":
                    self.btn_iniciar.config(state="normal")
                    self.btn_detener.config(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self.atender_cola)

    def parar(self):
        self.detener.set()
        self.btn_detener.config(state="disabled")

    def cerrar(self):
        if self.hilo and self.hilo.is_alive():
            if not messagebox.askyesno("Salir", "Hay un respaldo en curso. ¿Detenerlo y salir?"):
                return
            self.detener.set()
        self.destroy()


def main():
    App().mainloop()
