"""PERSONA 3 - Base de datos SQLite."""
import sqlite3
import config


def conectar():
    con = sqlite3.connect(config.DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS ecos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tema TEXT, resumen TEXT,
        creado TEXT DEFAULT CURRENT_TIMESTAMP,
        proximo_repaso TEXT, nivel INTEGER DEFAULT 0)""")
    return con
