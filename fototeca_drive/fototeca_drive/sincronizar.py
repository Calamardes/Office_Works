"""Motor de respaldo: compartido por la interfaz gráfica y la línea de comandos."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .escaneo import buscar_archivos, carpeta_destino, md5_archivo
from .estado import Estado


@dataclass
class Opciones:
    origen: Path
    carpeta_drive: str = "Fototeca"
    organizar: str = "fecha"  # "fecha" | "original" | "plano"
    incluir_videos: bool = False
    simulacion: bool = False  # True = no sube nada, solo muestra qué haría


@dataclass
class Resumen:
    total: int = 0
    subidos: int = 0
    omitidos: int = 0  # ya estaban en Drive (o duplicados locales)
    errores: list[str] = field(default_factory=list)
    bytes_subidos: int = 0


def respaldar(
    opciones: Opciones,
    drive=None,
    estado: Estado | None = None,
    log: Callable[[str], None] = print,
    progreso: Callable[[int, int], None] = lambda hechos, total: None,
    detener: threading.Event | None = None,
) -> Resumen:
    estado = estado or Estado()
    detener = detener or threading.Event()
    r = Resumen()

    log(f"Buscando archivos en {opciones.origen} ...")
    archivos = list(buscar_archivos(opciones.origen, opciones.incluir_videos))
    r.total = len(archivos)
    total_bytes = sum(a.tamano for a in archivos)
    log(f"Encontrados {r.total} archivos ({total_bytes / 1e9:.2f} GB).")
    if not archivos:
        return r

    raiz = None
    if drive is not None:
        log("Consultando lo que ya está en Drive ...")
        estado.subidos.update(drive.md5_existentes())
        raiz = drive.carpeta(opciones.carpeta_drive)

    vistos: set[str] = set()
    for i, a in enumerate(archivos, 1):
        if detener.is_set():
            log("Detenido por el usuario. Puedes continuar más tarde: lo ya subido no se repite.")
            break
        try:
            md5 = estado.md5_en_cache(a.ruta, a.tamano, a.mtime)
            if md5 is None:
                md5 = md5_archivo(a.ruta)
                estado.guardar_md5(a.ruta, a.tamano, a.mtime, md5)

            if md5 in estado.subidos or md5 in vistos:
                r.omitidos += 1
            else:
                destino = [opciones.carpeta_drive, *carpeta_destino(a, opciones.organizar)]
                if opciones.simulacion or drive is None:
                    log(f"[simulación] {a.relativa}  ->  {'/'.join(destino)}/")
                else:
                    carpeta_id = drive.ruta_carpetas(destino[1:], raiz)
                    estado.subidos[md5] = drive.subir(a.ruta, carpeta_id)
                    log(f"Subido: {a.relativa}  ->  {'/'.join(destino)}/")
                r.subidos += 1
                r.bytes_subidos += a.tamano
            vistos.add(md5)
        except Exception as e:  # un archivo con problemas no detiene el resto
            r.errores.append(f"{a.relativa}: {e}")
            log(f"ERROR en {a.relativa}: {e}")
        progreso(i, r.total)
        if i % 25 == 0:
            estado.guardar()

    estado.guardar()
    accion = "Se subirían" if (opciones.simulacion or drive is None) else "Subidos"
    log(
        f"\nListo. {accion}: {r.subidos} ({r.bytes_subidos / 1e9:.2f} GB) · "
        f"Ya estaban: {r.omitidos} · Errores: {len(r.errores)}"
    )
    return r
