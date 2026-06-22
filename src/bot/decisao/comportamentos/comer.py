"""Comer — auto-comer por tempo.

O Tibia não expõe um sinal de "fome" legível por pixel, então comemos numa cadência
fixa: a cada `intervalo_s`, aperta a hotkey de comida. Auto-temporizado via
`contexto.ts` (não usa o cooldown compartilhado, p/ não inundar o log com NENHUMA de
cooldown). Prioridade baixa: cura/ataque/saque sempre vêm antes no tick.

O Tibia ignora comer quando o personagem está cheio, então apertar a mais é inócuo.
"""

from __future__ import annotations

from bot.configuracao import ComerConfig
from bot.contexto import Contexto
from bot.decisao.tipos import Decisao, TipoAcao


class Comer:
    nome = "comer"

    def __init__(self, comer: ComerConfig):
        self.cfg = comer
        self.prioridade = comer.prioridade
        self._proxima = 0.0  # próximo ts em que pode comer (0 => come no 1º tick)

    def avaliar(self, contexto: Contexto) -> Decisao | None:
        if not self.cfg.ativo:
            return None
        ts = contexto.ts
        if ts < self._proxima:
            return None
        self._proxima = ts + self.cfg.intervalo_s
        return Decisao(
            self.nome,
            TipoAcao.PRESSIONAR_TECLA,
            self.cfg.tecla,
            f"comer (a cada {self.cfg.intervalo_s:.0f}s) -> {self.cfg.tecla.upper()}",
            self.prioridade,
            {"recurso": "comida"},
        )
