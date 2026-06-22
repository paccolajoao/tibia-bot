"""Interface de comportamento — o ponto de extensão do bot.

Cada feature futura (targeting, looting, cavebot, bestiário) é só uma classe que
implementa `ComportamentoBase` e é registrada no motor com uma `prioridade`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bot.contexto import Contexto
from bot.decisao.tipos import Decisao


@runtime_checkable
class ComportamentoBase(Protocol):
    nome: str
    prioridade: int  # maior = avaliado primeiro

    def avaliar(self, contexto: Contexto) -> Decisao | None:
        """Retorna uma Decisao se quiser agir neste tick, ou None para passar a vez."""
        ...
