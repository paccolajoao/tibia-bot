"""API REST do portal — perfis, config e regiões via TestClient (offline, DB temporário)."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from bot.nucleo.estado_execucao import ControladorExecucao
from bot.painel.servidor import criar_app
from bot.telemetria.barramento import BarramentoEventos


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """App com o banco SQLite apontando para um arquivo temporário isolado."""
    monkeypatch.setattr("bot.persistencia.banco.CAMINHO_BANCO", tmp_path / "bot.db")
    app = criar_app(BarramentoEventos(), ControladorExecucao())
    with TestClient(app) as c:
        yield c


def test_perfis_seed_inicial(client):
    r = client.get("/api/perfis")
    assert r.status_code == 200
    perfis = r.json()
    assert len(perfis) == 1 and perfis[0]["ativo"]


def test_get_e_put_config(client):
    cfg = client.get("/api/config").json()
    cfg["cura"]["hp_critico"] = 22.0
    r = client.put("/api/config", json=cfg)
    assert r.status_code == 200
    assert client.get("/api/config").json()["cura"]["hp_critico"] == 22.0


def test_put_config_invalido_rejeitado(client):
    cfg = client.get("/api/config").json()
    cfg["cura"]["hp_critico"] = "não-é-número"
    assert client.put("/api/config", json=cfg).status_code == 422


def test_criar_ativar_e_excluir_perfil(client):
    novo = client.post("/api/perfis", json={"nome": "Knight"}).json()
    assert client.post(f"/api/perfis/{novo['id']}/ativar").json()["ativo"]
    assert client.delete(f"/api/perfis/{novo['id']}").status_code == 204


def test_nome_duplicado_conflito(client):
    client.post("/api/perfis", json={"nome": "Dup"})
    assert client.post("/api/perfis", json={"nome": "Dup"}).status_code == 409


def test_put_regioes(client):
    r = client.put("/api/regioes", json={"hp": [10, 20, 110, 40]})
    assert r.status_code == 200
    assert client.get("/api/config").json()["regioes"]["hp"] == [10, 20, 110, 40]


def test_export_importar_yaml(client):
    texto = client.get("/api/config/export").text
    assert "cura" in texto
    novo = client.post("/api/config/importar", json={"nome": "Importado", "yaml": texto})
    assert novo.status_code == 201


def test_meta(client):
    meta = client.get("/api/meta").json()
    assert "obs" in meta["backends_captura"]
    assert meta["perfil_ativo"]["ativo"]
