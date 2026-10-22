"""PERSONA 3 - CONTRATO: guardar y recuperar ecos."""
from datetime import date
from memoria.db import conectar
from memoria.repeticion import proxima_fecha


def guardar_eco(tema: str, resumen: str) -> None:
    con = conectar()
    con.execute("INSERT INTO ecos (tema, resumen, proximo_repaso) VALUES (?,?,?)",
                (tema, resumen, proxima_fecha(0)))
    con.commit()


def ecos_pendientes() -> list[dict]:
    con = conectar()
    filas = con.execute(
        "SELECT id, tema, resumen FROM ecos WHERE proximo_repaso <= ?",
        (date.today().isoformat(),)).fetchall()
    return [{"id": f[0], "tema": f[1], "resumen": f[2]} for f in filas]
