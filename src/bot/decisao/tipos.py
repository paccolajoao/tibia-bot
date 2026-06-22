"""Tipos do motor de decisão."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class TipoAcao(Enum):
    PRESSIONAR_TECLA = auto()
    CLICAR = auto()
    NENHUMA = auto()


@dataclass
class Decisao:
    comportamento: str
    acao: TipoAcao
    tecla: str | None
    motivo: str  # legível por humano -> vai direto pro log do painel
    prioridade: int = 0
    dados: dict[str, Any] = field(default_factory=dict)
    ponto: tuple[int, int] | None = None  # coords absolutas do desktop p/ CLICAR
    chave_cooldown: str | None = None  # chave de cooldown quando não há `tecla` (ex.: clique)

    @property
    def chave_cd(self) -> str | None:
        """Chave usada no cooldown: explícita, ou a própria tecla."""
        return self.chave_cooldown or self.tecla

    @staticmethod
    def nenhuma(comportamento: str = "-", motivo: str = "monitorando", prioridade: int = 0) -> Decisao:
        return Decisao(comportamento, TipoAcao.NENHUMA, None, motivo, prioridade)
