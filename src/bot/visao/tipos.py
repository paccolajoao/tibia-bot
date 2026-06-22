"""Tipos da camada de visão."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DeteccaoCriaturas:
    """Resultado da leitura da battle list.

    `centro_primeira` está em COORDS DA IMAGEM (saída pura da visão). O loop o
    converte para coords absolutas do desktop e preenche `ponto_clique`, que é o
    que o comportamento de alvo usa para clicar.
    `confianca` baixa indica leitura suspeita (ex.: tooltip cobrindo a lista) — o
    comportamento a usa para ignorar a leitura em vez de clicar errado.
    """

    n_criaturas: int
    alvo_atual: bool  # já existe uma criatura sendo atacada (entrada destacada)
    confianca: float  # 0.0 .. 1.0
    centro_primeira: tuple[int, int] | None = None  # coords da imagem
    ponto_clique: tuple[int, int] | None = None  # coords absolutas (preenchido pelo loop)


@dataclass
class LeituraBarra:
    """Resultado da leitura de uma barra (HP ou Mana).

    `confianca` baixa indica leitura suspeita (ex.: tooltip cobrindo a barra) —
    o motor de decisão a usa para ignorar leituras ruins em vez de agir errado.
    """

    percentual: float  # 0.0 .. 100.0
    amostras_total: int
    amostras_preenchidas: int
    confianca: float  # 0.0 .. 1.0

    def __str__(self) -> str:
        return f"{self.percentual:.0f}%"
