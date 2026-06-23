"""CRUD de **perfis** de configuração no SQLite.

Cada perfil guarda um `Config` inteiro serializado em JSON (`dados_json`). Optou-se
por um blob JSON em vez de normalizar cada campo em colunas porque o `Config` é uma
árvore pydantic aninhada que cresce com frequência — um blob valida via pydantic na
leitura e dispensa migração de esquema a cada campo novo. Exatamente um perfil tem
`ativo = 1`; é dele que o bot lê no boot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from bot.configuracao import Config, carregar_config, config_de_dict, config_para_dict
from bot.persistencia.banco import conectar, criar_esquema

NOME_PERFIL_PADRAO = "Padrão"


@dataclass(frozen=True)
class Perfil:
    """Um perfil de configuração persistido."""

    id: int
    nome: str
    config: Config
    ativo: bool
    criado_em: str
    atualizado_em: str


def _agora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _linha_para_perfil(linha) -> Perfil:
    return Perfil(
        id=linha["id"],
        nome=linha["nome"],
        config=config_de_dict(json.loads(linha["dados_json"])),
        ativo=bool(linha["ativo"]),
        criado_em=linha["criado_em"],
        atualizado_em=linha["atualizado_em"],
    )


def garantir_inicializado(caminho: Path | None = None) -> None:
    """Cria o esquema e, se não houver perfis, semeia o "Padrão" a partir do YAML.

    Migração transparente: na 1ª execução copia o `config.yaml` (ou o exemplo, ou os
    defaults) existente para dentro do banco, marcando-o como ativo.
    """
    with conectar(caminho) as conn:
        criar_esquema(conn)
        (n,) = conn.execute("SELECT COUNT(*) FROM perfis").fetchone()
        if n == 0:
            agora = _agora()
            conn.execute(
                "INSERT INTO perfis (nome, dados_json, ativo, criado_em, atualizado_em) "
                "VALUES (?, ?, 1, ?, ?)",
                (NOME_PERFIL_PADRAO, json.dumps(config_para_dict(carregar_config())), agora, agora),
            )
            conn.commit()


def listar_perfis(caminho: Path | None = None) -> list[Perfil]:
    """Todos os perfis, do mais antigo ao mais novo."""
    with conectar(caminho) as conn:
        linhas = conn.execute("SELECT * FROM perfis ORDER BY id").fetchall()
    return [_linha_para_perfil(linha) for linha in linhas]


def obter_perfil(id_perfil: int, caminho: Path | None = None) -> Perfil:
    """Um perfil por id. Levanta `KeyError` se não existir."""
    with conectar(caminho) as conn:
        linha = conn.execute("SELECT * FROM perfis WHERE id = ?", (id_perfil,)).fetchone()
    if linha is None:
        raise KeyError(f"Perfil {id_perfil} não encontrado")
    return _linha_para_perfil(linha)


def obter_ativo(caminho: Path | None = None) -> Perfil:
    """O perfil ativo. Inicializa o banco se preciso."""
    garantir_inicializado(caminho)
    with conectar(caminho) as conn:
        linha = conn.execute("SELECT * FROM perfis WHERE ativo = 1 ORDER BY id LIMIT 1").fetchone()
        if linha is None:  # estado defensivo: nenhum ativo — promove o primeiro
            linha = conn.execute("SELECT * FROM perfis ORDER BY id LIMIT 1").fetchone()
            if linha is not None:
                conn.execute("UPDATE perfis SET ativo = 1 WHERE id = ?", (linha["id"],))
                conn.commit()
    if linha is None:
        raise RuntimeError("Banco sem perfis após inicialização")
    return _linha_para_perfil(linha)


def carregar_config_ativa(caminho: Path | None = None) -> Config:
    """Atalho: o `Config` do perfil ativo (o que o bot consome no boot)."""
    return obter_ativo(caminho).config


def criar_perfil(
    nome: str, config: Config | None = None, *, ativar_novo: bool = False, caminho: Path | None = None
) -> Perfil:
    """Cria um perfil. `config=None` usa os defaults. `nome` deve ser único."""
    garantir_inicializado(caminho)
    nome = nome.strip()
    if not nome:
        raise ValueError("Nome do perfil não pode ser vazio")
    config = config or Config()
    agora = _agora()
    with conectar(caminho) as conn:
        if ativar_novo:
            conn.execute("UPDATE perfis SET ativo = 0")
        cur = conn.execute(
            "INSERT INTO perfis (nome, dados_json, ativo, criado_em, atualizado_em) "
            "VALUES (?, ?, ?, ?, ?)",
            (nome, json.dumps(config_para_dict(config)), 1 if ativar_novo else 0, agora, agora),
        )
        conn.commit()
        novo_id = cur.lastrowid
    return obter_perfil(novo_id, caminho)


def atualizar_config(id_perfil: int, config: Config, caminho: Path | None = None) -> Perfil:
    """Substitui o `Config` de um perfil. Levanta `KeyError` se não existir."""
    with conectar(caminho) as conn:
        cur = conn.execute(
            "UPDATE perfis SET dados_json = ?, atualizado_em = ? WHERE id = ?",
            (json.dumps(config_para_dict(config)), _agora(), id_perfil),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise KeyError(f"Perfil {id_perfil} não encontrado")
    return obter_perfil(id_perfil, caminho)


def salvar_config_ativa(config: Config, caminho: Path | None = None) -> Perfil:
    """Grava o `Config` no perfil ativo (usado pela calibração CLI e pela API)."""
    return atualizar_config(obter_ativo(caminho).id, config, caminho)


def renomear(id_perfil: int, nome: str, caminho: Path | None = None) -> Perfil:
    """Renomeia um perfil. `nome` deve ser único e não-vazio."""
    nome = nome.strip()
    if not nome:
        raise ValueError("Nome do perfil não pode ser vazio")
    with conectar(caminho) as conn:
        cur = conn.execute(
            "UPDATE perfis SET nome = ?, atualizado_em = ? WHERE id = ?",
            (nome, _agora(), id_perfil),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise KeyError(f"Perfil {id_perfil} não encontrado")
    return obter_perfil(id_perfil, caminho)


def ativar(id_perfil: int, caminho: Path | None = None) -> Perfil:
    """Torna `id_perfil` o ativo (e zera os demais)."""
    with conectar(caminho) as conn:
        existe = conn.execute("SELECT 1 FROM perfis WHERE id = ?", (id_perfil,)).fetchone()
        if existe is None:
            raise KeyError(f"Perfil {id_perfil} não encontrado")
        conn.execute("UPDATE perfis SET ativo = 0")
        conn.execute("UPDATE perfis SET ativo = 1 WHERE id = ?", (id_perfil,))
        conn.commit()
    return obter_perfil(id_perfil, caminho)


def duplicar(id_perfil: int, novo_nome: str, caminho: Path | None = None) -> Perfil:
    """Cria um novo perfil com a mesma config de `id_perfil`."""
    origem = obter_perfil(id_perfil, caminho)
    return criar_perfil(novo_nome, origem.config, caminho=caminho)


def excluir(id_perfil: int, caminho: Path | None = None) -> None:
    """Remove um perfil. Recusa apagar o último; se era o ativo, promove outro."""
    with conectar(caminho) as conn:
        (total,) = conn.execute("SELECT COUNT(*) FROM perfis").fetchone()
        if total <= 1:
            raise ValueError("Não é possível excluir o único perfil restante")
        linha = conn.execute("SELECT ativo FROM perfis WHERE id = ?", (id_perfil,)).fetchone()
        if linha is None:
            raise KeyError(f"Perfil {id_perfil} não encontrado")
        era_ativo = bool(linha["ativo"])
        conn.execute("DELETE FROM perfis WHERE id = ?", (id_perfil,))
        if era_ativo:
            outro = conn.execute("SELECT id FROM perfis ORDER BY id LIMIT 1").fetchone()
            conn.execute("UPDATE perfis SET ativo = 1 WHERE id = ?", (outro["id"],))
        conn.commit()
