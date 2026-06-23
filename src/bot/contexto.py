"""Contexto: estado central compartilhado de um tick.

Inspirado no `context` centralizado do PyTibia. É de propriedade EXCLUSIVA da
thread do bot — o dashboard nunca o toca, só vê snapshots imutáveis (telemetria).
Essa regra de posse é o que mantém o modelo de threads simples.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bot.captura.base import Frame
from bot.configuracao import Config
from bot.telemetria.estatisticas import Estatisticas
from bot.visao.inventario import ItemDetectado
from bot.visao.tipos import DeteccaoCriaturas, LeituraBarra


@dataclass
class Contexto:
    config: Config
    frame_atual: Frame | None = None
    hp: LeituraBarra | None = None
    mana: LeituraBarra | None = None
    criaturas: DeteccaoCriaturas | None = None
    # itens do inventário detectados no tick (ponto JÁ em coords absolutas do desktop)
    itens_inventario: list[ItemDetectado] = field(default_factory=list)
    ponto_drop: tuple[int, int] | None = None  # destino do drop (coords absolutas)
    tick: int = 0
    ts: float = 0.0
    fps: float = 0.0
    janela_focada: bool = True
    estatisticas: Estatisticas = field(default_factory=Estatisticas)
    # espaço de rascunho namespaced para comportamentos futuros (targeting/loot/cavebot)
    estado_comportamentos: dict[str, Any] = field(default_factory=dict)
