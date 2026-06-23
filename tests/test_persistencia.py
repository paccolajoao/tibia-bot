"""Persistência SQLite de perfis — CRUD, ativação e seed inicial (offline)."""

from __future__ import annotations

import sqlite3

import pytest

from bot.configuracao import Config
from bot.persistencia import repo_perfis as repo


@pytest.fixture()
def banco(tmp_path):
    """Caminho de um banco SQLite isolado por teste."""
    return tmp_path / "bot.db"


def test_seed_cria_perfil_padrao_ativo(banco):
    repo.garantir_inicializado(banco)
    perfis = repo.listar_perfis(banco)
    assert len(perfis) == 1
    assert perfis[0].nome == repo.NOME_PERFIL_PADRAO
    assert perfis[0].ativo
    assert isinstance(perfis[0].config, Config)


def test_seed_idempotente(banco):
    repo.garantir_inicializado(banco)
    repo.garantir_inicializado(banco)
    assert len(repo.listar_perfis(banco)) == 1


def test_salvar_config_ativa_persiste(banco):
    cfg = repo.carregar_config_ativa(banco)
    cfg.cura.hp_critico = 12.0
    repo.salvar_config_ativa(cfg, banco)
    assert repo.carregar_config_ativa(banco).cura.hp_critico == 12.0


def test_criar_e_ativar_troca_o_ativo(banco):
    repo.garantir_inicializado(banco)
    novo = repo.criar_perfil("Cavaleiro", Config(), caminho=banco)
    assert not novo.ativo
    repo.ativar(novo.id, banco)
    assert repo.obter_ativo(banco).id == novo.id
    # exatamente um ativo
    assert sum(1 for p in repo.listar_perfis(banco) if p.ativo) == 1


def test_nome_duplicado_falha(banco):
    repo.garantir_inicializado(banco)
    repo.criar_perfil("X", caminho=banco)
    with pytest.raises(sqlite3.IntegrityError):
        repo.criar_perfil("X", caminho=banco)


def test_duplicar_copia_config(banco):
    cfg = repo.carregar_config_ativa(banco)
    cfg.alvo.recompromisso_s = 9.0
    ativo = repo.obter_ativo(banco)
    repo.atualizar_config(ativo.id, cfg, banco)
    copia = repo.duplicar(ativo.id, "Cópia", banco)
    assert copia.config.alvo.recompromisso_s == 9.0
    assert copia.id != ativo.id


def test_excluir_ativo_promove_outro(banco):
    repo.garantir_inicializado(banco)
    ativo = repo.obter_ativo(banco)
    outro = repo.criar_perfil("Outro", caminho=banco)
    repo.excluir(ativo.id, banco)
    assert repo.obter_ativo(banco).id == outro.id


def test_excluir_ultimo_falha(banco):
    repo.garantir_inicializado(banco)
    ativo = repo.obter_ativo(banco)
    with pytest.raises(ValueError):
        repo.excluir(ativo.id, banco)
