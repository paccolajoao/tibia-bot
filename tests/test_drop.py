"""Comportamento Drop — emite ARRASTAR para o tile de drop, respeitando cadência."""

from __future__ import annotations

from bot.configuracao import Config, DropConfig, ItemDrop
from bot.contexto import Contexto
from bot.decisao.comportamentos.drop import Drop
from bot.decisao.tipos import TipoAcao
from bot.visao.inventario import ItemDetectado


def _ctx(com_item=True, com_destino=True) -> Contexto:
    ctx = Contexto(config=Config())
    ctx.ts = 100.0
    if com_item:
        ctx.itens_inventario = [ItemDetectado("rune", (500, 300), 0.95)]
    if com_destino:
        ctx.ponto_drop = (800, 600)
    return ctx


def _drop(**kw) -> Drop:
    cfg = DropConfig(ativo=True, itens=[ItemDrop(nome="rune", template_b64="x")], **kw)
    return Drop(cfg)


def test_arrasta_item_para_destino():
    d = _drop()
    dec = d.avaliar(_ctx())
    assert dec is not None
    assert dec.acao == TipoAcao.ARRASTAR
    assert dec.ponto == (500, 300)
    assert dec.ponto_destino == (800, 600)
    assert dec.dados["confirmar"] is True


def test_inativo_nao_age():
    cfg = DropConfig(ativo=False, itens=[ItemDrop(nome="rune", template_b64="x")])
    assert Drop(cfg).avaliar(_ctx()) is None


def test_sem_item_ou_destino_nao_age():
    d = _drop()
    assert d.avaliar(_ctx(com_item=False)) is None
    assert _drop().avaliar(_ctx(com_destino=False)) is None


def test_respeita_intervalo_entre_drops():
    d = _drop(intervalo_s=1.0)
    ctx = _ctx()
    assert d.avaliar(ctx) is not None  # 1º drop em t=100
    assert d.avaliar(ctx) is None      # mesmo ts: ainda no intervalo
    ctx.ts = 101.5
    assert d.avaliar(ctx) is not None  # passou o intervalo


def test_confirmar_quantidade_desligado():
    d = _drop(confirmar_quantidade=False)
    dec = d.avaliar(_ctx())
    assert dec.dados["confirmar"] is False
