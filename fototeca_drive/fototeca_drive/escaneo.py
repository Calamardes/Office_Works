"""Búsqueda de fotos/videos en la fototeca local y cálculo de su destino en Drive."""

from __future__ import annotations

import hashlib
import os
import platform
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

EXT_IMAGENES = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp",
    ".heic", ".heif", ".dng", ".cr2", ".cr3", ".nef", ".arw", ".orf", ".raf", ".rw2",
}
EXT_VIDEOS = {".mov", ".mp4", ".m4v", ".avi", ".3gp", ".mkv"}

MESES = [
    "01-Enero", "02-Febrero", "03-Marzo", "04-Abril", "05-Mayo", "06-Junio",
    "07-Julio", "08-Agosto", "09-Septiembre", "10-Octubre", "11-Noviembre", "12-Diciembre",
]


@dataclass
class Archivo:
    ruta: Path
    relativa: Path  # ruta relativa a la carpeta de origen
    tamano: int
    mtime: float


def fototeca_por_defecto() -> Path:
    """Devuelve la ubicación más probable de la fototeca según el sistema."""
    home = Path.home()
    if platform.system() == "Darwin":
        # Fototeca de la app Fotos de macOS: los originales viven en /originals
        # (o /Masters en bibliotecas antiguas).
        lib = home / "Pictures" / "Photos Library.photoslibrary"
        for sub in ("originals", "Masters"):
            if (lib / sub).is_dir():
                return lib / sub
    for nombre in ("Pictures", "Imágenes", "Imagenes"):
        if (home / nombre).is_dir():
            return home / nombre
    return home


def buscar_archivos(origen: Path, incluir_videos: bool = False) -> Iterator[Archivo]:
    """Recorre `origen` recursivamente y entrega las fotos (y videos si se pide)."""
    extensiones = EXT_IMAGENES | (EXT_VIDEOS if incluir_videos else set())
    for raiz, dirs, archivos in os.walk(origen):
        # Ignora carpetas ocultas y de sistema
        dirs[:] = sorted(d for d in dirs if not d.startswith((".", "@")))
        for nombre in sorted(archivos):
            if nombre.startswith("."):
                continue
            ruta = Path(raiz) / nombre
            if ruta.suffix.lower() not in extensiones:
                continue
            try:
                st = ruta.stat()
            except OSError:
                continue
            if st.st_size == 0:
                continue
            yield Archivo(ruta, ruta.relative_to(origen), st.st_size, st.st_mtime)


def md5_archivo(ruta: Path, bloque: int = 1024 * 1024) -> str:
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for trozo in iter(lambda: f.read(bloque), b""):
            h.update(trozo)
    return h.hexdigest()


def fecha_captura(ruta: Path, mtime: float) -> datetime:
    """Fecha en que se tomó la foto (EXIF). Si no hay EXIF, usa la fecha del archivo."""
    try:
        from PIL import Image

        try:  # soporte HEIC/HEIF si pillow-heif está instalado
            from pillow_heif import register_heif_opener

            register_heif_opener()
        except ImportError:
            pass

        with Image.open(ruta) as img:
            exif = img.getexif()
            # 36867 = DateTimeOriginal (sub-IFD Exif), 306 = DateTime
            valor = exif.get_ifd(0x8769).get(36867) or exif.get(306)
            if valor:
                return datetime.strptime(str(valor).strip()[:19], "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return datetime.fromtimestamp(mtime)


def carpeta_destino(archivo: Archivo, modo: str) -> list[str]:
    """Lista de subcarpetas (dentro de la carpeta raíz de Drive) donde va el archivo.

    modo:
      - "fecha":    Año/Mes según la fecha de captura (ej. ["2024", "07-Julio"])
      - "original": misma estructura de carpetas que en el origen
      - "plano":    todo en la carpeta raíz
    """
    if modo == "fecha":
        f = fecha_captura(archivo.ruta, archivo.mtime)
        return [str(f.year), MESES[f.month - 1]]
    if modo == "original":
        return list(archivo.relativa.parent.parts)
    return []
