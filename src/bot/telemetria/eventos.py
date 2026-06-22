"""Schema de eventos de telemetria — a representação de "o que o bot está pensando".

Dois ângulos do "pensar", emitidos a cada tick relevante:
  - LinhaRaciocinio: texto legível por humano ("HP 32% <= crítico -> cura forte (F5)")
  - EventoDecisao:   objeto estruturado (comportamento, ação, tecla, motivo, dados)

Todos os eventos são imutáveis e têm `tipo` (discriminador) + `to_dict()` p/ enviar via WebSocket.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SnapshotEstado:
    """Heartbeat do estado atual — emitido todo tick (alimenta os medidores ao vivo)."""

    ts: float
    tick: int
    hp_pct: float | None
    mana_pct: float | None
    hp_confianca: float | None
    fps: float
    estado_execucao: str
    janela_focada: bool
    backend_captura: str
    tipo: str = "estado"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventoDecisao:
    """Decisão estruturada do tick."""

    ts: float
    tick: int
    comportamento: str
    acao: str
    tecla: str | None
    motivo: str
    dados: dict[str, Any] = field(default_factory=dict)
    tipo: str = "decisao"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LinhaRaciocinio:
    """Linha legível para o log "O que o bot está pensando"."""

    ts: float
    tick: int
    texto: str
    nivel: str = "info"  # info | acao | alerta
    tipo: str = "raciocinio"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventoDeteccao:
    """Leituras de visão deste tick (barras + criaturas da battle list)."""

    ts: float
    tick: int
    hp: dict[str, Any] | None
    mana: dict[str, Any] | None
    criaturas: dict[str, Any] | None = None
    tipo: str = "deteccao"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventoStats:
    """Agregados periódicos (~1 Hz)."""

    ts: float
    uptime_s: float
    curas: int
    pocoes_mana: int
    fps_medio: float
    ataques: int = 0
    refeicoes: int = 0
    saques: int = 0
    tipo: str = "stats"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventoQuadro:
    """Frame anotado (preview ao vivo), JPEG em base64. Emitido com throttle."""

    ts: float
    tick: int
    jpeg_base64: str
    tipo: str = "quadro"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
