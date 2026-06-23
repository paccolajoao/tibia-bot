"""Conexão e esquema do banco SQLite local (`config/bot.db`).

Conexões são abertas **por operação** (curtas) em vez de um singleton: o bot roda
em duas threads (loop síncrono + asyncio do painel) e conexões SQLite não são
compartilháveis entre threads por padrão. Abrir/fechar por chamada é barato para
um app desktop single-user e elimina a classe inteira de bugs de concorrência.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from bot.configuracao import RAIZ_PROJETO

CAMINHO_BANCO = RAIZ_PROJETO / "config" / "bot.db"

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS perfis (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT    NOT NULL UNIQUE,
    dados_json   TEXT    NOT NULL,
    ativo        INTEGER NOT NULL DEFAULT 0,
    criado_em    TEXT    NOT NULL,
    atualizado_em TEXT   NOT NULL
);
"""


def conectar(caminho: Path | None = None) -> sqlite3.Connection:
    """Abre uma conexão com `row_factory` em `sqlite3.Row` (acesso por nome)."""
    caminho = caminho or CAMINHO_BANCO
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(caminho))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def criar_esquema(conn: sqlite3.Connection) -> None:
    """Cria as tabelas se ainda não existirem (idempotente)."""
    conn.executescript(_ESQUEMA)
    conn.commit()
