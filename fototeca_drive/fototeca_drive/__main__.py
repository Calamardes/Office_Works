"""Uso:
    python -m fototeca_drive                 # abre la ventana
    python -m fototeca_drive --consola ...   # modo línea de comandos (ver --help)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .escaneo import fototeca_por_defecto


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="fototeca_drive", description="Respalda tu fototeca en Google Drive.")
    p.add_argument("--consola", action="store_true", help="usar la línea de comandos en vez de la ventana")
    p.add_argument("--origen", type=Path, default=None, help="carpeta con las fotos (por defecto, tu fototeca)")
    p.add_argument("--destino", default="Fototeca", help="nombre de la carpeta en Drive (por defecto: Fototeca)")
    p.add_argument("--organizar", choices=["fecha", "original", "plano"], default="fecha",
                   help="fecha = Año/Mes, original = mismas carpetas, plano = todo junto")
    p.add_argument("--videos", action="store_true", help="incluir también videos")
    p.add_argument("--simular", action="store_true", help="no sube nada, solo muestra qué haría")
    p.add_argument("--credenciales", type=Path, default=None, help="ruta a credentials.json")
    a = p.parse_args(argv)

    if not a.consola:
        try:
            from .gui import main as gui_main
        except ImportError:
            print("No hay interfaz gráfica disponible (falta tkinter); usando modo consola.\n")
        else:
            gui_main()
            return 0

    from .sincronizar import Opciones, respaldar

    origen = (a.origen or fototeca_por_defecto()).expanduser()
    if not origen.is_dir():
        print(f"No existe la carpeta: {origen}", file=sys.stderr)
        return 2

    drive = None
    if not a.simular:
        from .drive import Drive, autenticar

        print("Conectando con Google Drive (se abrirá el navegador la primera vez)…")
        drive = Drive(autenticar(a.credenciales))

    def progreso(hechos: int, total: int) -> None:
        if hechos % 50 == 0 or hechos == total:
            print(f"  … {hechos}/{total} revisados")

    op = Opciones(origen, a.destino, a.organizar, a.videos, a.simular)
    try:
        r = respaldar(op, drive=drive, progreso=progreso)
    except KeyboardInterrupt:
        print("\nInterrumpido. Vuelve a ejecutar para continuar donde quedó.")
        return 130
    return 1 if r.errores else 0


if __name__ == "__main__":
    sys.exit(main())
