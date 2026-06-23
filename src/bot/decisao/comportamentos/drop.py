"""Drop — arrasta itens cadastrados da backpack para um tile do chão.

A DETECÇÃO dos itens (template matching) e a conversão dos pontos para coords
absolutas são feitas pelo loop (que captura a região do inventário todo tick e já
aplica o mapeamento do OBS). Aqui só decidimos arrastar o 1º item encontrado para o
ponto de drop, respeitando uma cadência (`intervalo_s`).

A ação é um ARRASTAR(ponto_item -> ponto_drop). Itens empilháveis abrem a janela
"Move how many?" do Tibia — o loop aperta Enter depois (se `confirmar_quantidade`).
Prioridade baixa: cura/alvo/saque vêm antes.
"""

from __future__ import annotations

from bot.configuracao import DropConfig
from bot.contexto import Contexto
from bot.decisao.tipos import Decisao, TipoAcao


class Drop:
    nome = "drop"

    def __init__(self, drop: DropConfig):
        self.cfg = drop
        self.prioridade = drop.prioridade
        self._proximo = 0.0  # ts do próximo drop permitido

    def avaliar(self, contexto: Contexto) -> Decisao | None:
        if not self.cfg.ativo:
            return None
        itens = contexto.itens_inventario
        destino = contexto.ponto_drop
        if not itens or destino is None:
            return None

        ts = contexto.ts
        if ts < self._proximo:
            return None
        self._proximo = ts + self.cfg.intervalo_s

        item = itens[0]  # mais confiante primeiro (detectar_itens já ordena)
        return Decisao(
            self.nome,
            TipoAcao.ARRASTAR,
            tecla=None,
            motivo=f"dropar '{item.nome}' (match {item.score:.2f}) -> chão",
            prioridade=self.prioridade,
            dados={"recurso": "drop", "item": item.nome, "confirmar": self.cfg.confirmar_quantidade},
            ponto=item.ponto,
            ponto_destino=destino,
        )
