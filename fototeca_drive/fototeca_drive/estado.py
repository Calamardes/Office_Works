"""Estado local: caché de hashes y lista de lo ya subido, para poder reanudar."""

from __future__ import annotations

import json
import os
from pathlib import Path

DIR_APP = Path(os.environ.get("FOTOTECA_DRIVE_HOME", Path.home() / ".fototeca_drive"))


class Estado:
    """Guarda en disco:
    - hashes: ruta -> [tamaño, mtime, md5] para no recalcular el MD5 en cada corrida.
    - subidos: md5 -> id del archivo en Drive.
    """

    def __init__(self, ruta: Path | None = None):
        self.ruta = ruta or DIR_APP / "estado.json"
        self.hashes: dict[str, list] = {}
        self.subidos: dict[str, str] = {}
        if self.ruta.exists():
            try:
                datos = json.loads(self.ruta.read_text(encoding="utf-8"))
                self.hashes = datos.get("hashes", {})
                self.subidos = datos.get("subidos", {})
            except (OSError, ValueError):
                pass

    def md5_en_cache(self, ruta: Path, tamano: int, mtime: float) -> str | None:
        reg = self.hashes.get(str(ruta))
        if reg and reg[0] == tamano and abs(reg[1] - mtime) < 1e-3:
            return reg[2]
        return None

    def guardar_md5(self, ruta: Path, tamano: int, mtime: float, md5: str) -> None:
        self.hashes[str(ruta)] = [tamano, mtime, md5]

    def guardar(self) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps({"hashes": self.hashes, "subidos": self.subidos}), encoding="utf-8")
        os.replace(tmp, self.ruta)
