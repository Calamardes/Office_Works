import os
from datetime import datetime
from pathlib import Path

from PIL import Image

from fototeca_drive.escaneo import buscar_archivos, carpeta_destino
from fototeca_drive.estado import Estado
from fototeca_drive.sincronizar import Opciones, respaldar


class DriveFalso:
    """Imita la clase Drive sin conectarse a internet."""

    def __init__(self, existentes=None):
        self.existentes = dict(existentes or {})
        self.subidas: list[tuple[str, str]] = []  # (nombre, ruta de carpeta)
        self._rutas = {"root": ""}

    def carpeta(self, nombre, padre="root"):
        ruta = f"{self._rutas[padre]}/{nombre}".lstrip("/")
        self._rutas[ruta] = ruta
        return ruta

    def ruta_carpetas(self, partes, raiz):
        actual = raiz
        for p in partes:
            actual = self.carpeta(p, actual)
        return actual

    def md5_existentes(self):
        return dict(self.existentes)

    def subir(self, ruta, carpeta_id):
        self.subidas.append((ruta.name, carpeta_id))
        return f"id-{len(self.subidas)}"


def crear_jpg(ruta: Path, color, fecha: str | None = None):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (8, 8), color)
    exif = Image.Exif()
    if fecha:
        exif.get_ifd(0x8769)[36867] = fecha
    img.save(ruta, exif=exif)


def preparar(tmp_path):
    fotos = tmp_path / "fotos"
    crear_jpg(fotos / "viaje" / "a.jpg", "red", "2023:07:14 10:00:00")
    crear_jpg(fotos / "b.jpg", "blue", "2024:01:02 08:30:00")
    crear_jpg(fotos / "viaje" / "copia_de_a.jpg", "red", "2023:07:14 10:00:00")  # duplicado exacto
    (fotos / "notas.txt").write_text("no es foto")
    (fotos / "video.mov").write_bytes(b"x" * 10)
    (fotos / ".oculta.jpg").write_bytes(b"x")
    return fotos


def test_busca_solo_imagenes(tmp_path):
    fotos = preparar(tmp_path)
    nombres = sorted(a.ruta.name for a in buscar_archivos(fotos))
    assert nombres == ["a.jpg", "b.jpg", "copia_de_a.jpg"]
    con_videos = sorted(a.ruta.name for a in buscar_archivos(fotos, incluir_videos=True))
    assert "video.mov" in con_videos


def test_carpeta_destino_por_fecha_exif(tmp_path):
    fotos = preparar(tmp_path)
    a = next(x for x in buscar_archivos(fotos) if x.ruta.name == "a.jpg")
    assert carpeta_destino(a, "fecha") == ["2023", "07-Julio"]
    assert carpeta_destino(a, "original") == ["viaje"]
    assert carpeta_destino(a, "plano") == []


def test_sin_exif_usa_fecha_del_archivo(tmp_path):
    ruta = tmp_path / "sin_exif.png"
    Image.new("RGB", (4, 4)).save(ruta)
    ts = datetime(2020, 11, 5).timestamp()
    os.utime(ruta, (ts, ts))
    a = next(buscar_archivos(tmp_path))
    assert carpeta_destino(a, "fecha") == ["2020", "11-Noviembre"]


def test_respaldo_sube_sin_duplicados_y_reanuda(tmp_path):
    fotos = preparar(tmp_path)
    estado_ruta = tmp_path / "estado.json"
    drive = DriveFalso()
    r = respaldar(Opciones(fotos), drive=drive, estado=Estado(estado_ruta), log=lambda m: None)
    assert r.total == 3 and r.subidos == 2 and r.omitidos == 1 and not r.errores
    assert sorted(drive.subidas) == [("a.jpg", "Fototeca/2023/07-Julio"), ("b.jpg", "Fototeca/2024/01-Enero")]

    # Segunda corrida: no debe volver a subir nada
    drive2 = DriveFalso()
    r2 = respaldar(Opciones(fotos), drive=drive2, estado=Estado(estado_ruta), log=lambda m: None)
    assert r2.subidos == 0 and r2.omitidos == 3 and drive2.subidas == []

    # Una foto nueva se sube sola
    crear_jpg(fotos / "nueva.jpg", "green")
    r3 = respaldar(Opciones(fotos), drive=drive2, estado=Estado(estado_ruta), log=lambda m: None)
    assert r3.subidos == 1 and [n for n, _ in drive2.subidas] == ["nueva.jpg"]


def test_no_repite_lo_que_ya_esta_en_drive(tmp_path):
    fotos = preparar(tmp_path)
    from fototeca_drive.escaneo import md5_archivo

    drive = DriveFalso(existentes={md5_archivo(fotos / "b.jpg"): "x"})
    r = respaldar(Opciones(fotos), drive=drive, estado=Estado(tmp_path / "e.json"), log=lambda m: None)
    assert [n for n, _ in drive.subidas] == ["a.jpg"]
    assert r.omitidos == 2


def test_simulacion_no_sube(tmp_path):
    fotos = preparar(tmp_path)
    mensajes = []
    r = respaldar(Opciones(fotos, simulacion=True, organizar="original"), drive=None,
                  estado=Estado(tmp_path / "e.json"), log=mensajes.append)
    assert r.subidos == 2
    assert any("viaje/a.jpg  ->  Fototeca/viaje/" in m for m in mensajes)
