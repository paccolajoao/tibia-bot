"""Testes do EstabilizadorBarra — OFFLINE, só estado + aritmética."""

from __future__ import annotations

from bot.visao.estabilizador import EstabilizadorBarra
from bot.visao.tipos import LeituraBarra


def _leitura(pct, conf=1.0):
    return LeituraBarra(pct, conf)


def test_leitura_normal_passa_intacta():
    est = EstabilizadorBarra(confianca_minima=0.6)
    out = est.estabilizar(_leitura(70.0), 0.0)
    assert out.percentual == 70.0
    assert out.confianca == 1.0


def test_extremo_uniforme_sem_corroboracao_e_rejeitado():
    # Primeira leitura já é 0%/100% uniforme (confiança "limpa" 1.0 vinda da função pura):
    # sem frame anterior p/ corroborar e sem histórico bom, vira confiança 0.0.
    est = EstabilizadorBarra(confianca_minima=0.6)
    out = est.estabilizar(_leitura(0.0, conf=1.0), 0.0)
    assert out.confianca == 0.0


def test_extremo_uniforme_corroborado_e_aceito():
    # Dois frames seguidos lendo 100% -> aceito (barra realmente cheia).
    est = EstabilizadorBarra(confianca_minima=0.6)
    est.estabilizar(_leitura(100.0), 0.0)  # 1º frame: rejeitado (sem corroboração)
    out = est.estabilizar(_leitura(100.0), 0.066)  # 2º: corroborado
    assert out.percentual == 100.0
    assert out.confianca == 1.0


def test_salto_impossivel_para_extremo_segura_ultimo_bom():
    # Estabelece um valor bom (30%), depois um salto instantâneo para 100% (oclusão
    # clara) deve ser rejeitado e SEGURAR 30% -> o bot continua curando.
    est = EstabilizadorBarra(confianca_minima=0.6)
    est.estabilizar(_leitura(30.0), 0.0)
    out = est.estabilizar(_leitura(100.0), 0.05)
    assert out.percentual == 30.0
    assert out.confianca >= 0.6  # acionável (hold pessimista)


def test_hold_expira_apos_ttl():
    # Depois do TTL sem leitura boa, o hold expira e a leitura ruim vira confiança 0.0.
    est = EstabilizadorBarra(confianca_minima=0.6, ttl_s=0.4)
    est.estabilizar(_leitura(30.0), 0.0)  # último bom em t=0
    # leitura de baixa confiança bem depois do TTL
    out = est.estabilizar(_leitura(80.0, conf=0.1), 1.0)
    assert out.confianca == 0.0


def test_baixa_confianca_dentro_do_ttl_segura_ultimo_bom():
    # Starvation em burst: leitura suja (baixa confiança) logo após um valor bom ->
    # segura o último bom p/ a cura não ficar cega.
    est = EstabilizadorBarra(confianca_minima=0.6)
    est.estabilizar(_leitura(25.0), 0.0)
    out = est.estabilizar(_leitura(50.0, conf=0.2), 0.1)
    assert out.percentual == 25.0
    assert out.confianca >= 0.6
