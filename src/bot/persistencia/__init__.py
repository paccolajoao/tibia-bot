"""Persistência local em SQLite — fonte única de configuração do bot.

O `config.yaml` deixa de ser a fonte de verdade: agora cada **perfil** guarda um
`Config` completo (serializado em JSON) numa tabela SQLite (`config/bot.db`). O
YAML sobrevive apenas como semente inicial (migração transparente na 1ª execução)
e para import/export pelo portal.

Veja [banco.py](banco.py) para conexão/esquema e [repo_perfis.py](repo_perfis.py)
para o CRUD de perfis.
"""

from __future__ import annotations

from bot.persistencia.repo_perfis import (
    Perfil,
    ativar,
    atualizar_config,
    carregar_config_ativa,
    criar_perfil,
    duplicar,
    excluir,
    garantir_inicializado,
    listar_perfis,
    obter_ativo,
    obter_perfil,
    renomear,
    salvar_config_ativa,
)

__all__ = [
    "Perfil",
    "ativar",
    "atualizar_config",
    "carregar_config_ativa",
    "criar_perfil",
    "duplicar",
    "excluir",
    "garantir_inicializado",
    "listar_perfis",
    "obter_ativo",
    "obter_perfil",
    "renomear",
    "salvar_config_ativa",
]
