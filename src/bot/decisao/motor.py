"""Motor de decisão: avalia comportamentos por prioridade e aplica cooldown.

- Itera comportamentos por prioridade desc; a PRIMEIRA decisão não-nula vence o
  tick (uma ação por tick => timing humano, sem tempestade de hotkeys).
- Se a tecla escolhida está em cooldown, devolve uma decisão NENHUMA cujo motivo
  explica isso (o painel mostra "queria curar, mas está em cooldown").
- O loop chama `confirmar_acao()` DEPOIS de executar, para registrar o cooldown.
"""

from __future__ import annotations

from collections.abc import Iterable

from bot.contexto import Contexto
from bot.decisao.comportamentos.base import ComportamentoBase
from bot.decisao.cooldown import GerenciadorCooldown
from bot.decisao.tipos import Decisao, TipoAcao


class MotorDecisao:
    def __init__(self, comportamentos: Iterable[ComportamentoBase], cooldown: GerenciadorCooldown):
        self._comportamentos = sorted(comportamentos, key=lambda c: c.prioridade, reverse=True)
        self._cooldown = cooldown

    def decidir(self, contexto: Contexto, agora: float) -> Decisao:
        for comp in self._comportamentos:
            dec = comp.avaliar(contexto)
            if dec is None or dec.acao == TipoAcao.NENHUMA:
                continue
            chave = dec.chave_cd
            if chave is not None and not self._cooldown.pode_disparar(chave, agora):
                restante = self._cooldown.restante(chave, agora)
                return Decisao(
                    dec.comportamento,
                    TipoAcao.NENHUMA,
                    dec.tecla,
                    f"{dec.motivo} [em cooldown, {restante:.1f}s]",
                    dec.prioridade,
                    dec.dados,
                    dec.ponto,
                    dec.chave_cooldown,
                )
            return dec
        return Decisao.nenhuma()

    def confirmar_acao(self, decisao: Decisao, agora: float) -> None:
        if decisao.acao in (TipoAcao.PRESSIONAR_TECLA, TipoAcao.CLICAR) and decisao.chave_cd:
            self._cooldown.registrar(decisao.chave_cd, agora)
