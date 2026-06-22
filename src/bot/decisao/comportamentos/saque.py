"""Saque — auto-loot via Quick Loot do Tibia.

Quando uma criatura morre (sai da battle list), aperta a hotkey de Quick Loot do
Tibia, que faz o jogo encontrar o corpo e pegar o loot conforme as loot lists
configuradas NO Tibia.

A DETECÇÃO da morte é feita pelo loop (que vê todo tick e já computa `ctx.criaturas`)
e exposta em `ctx.estado_comportamentos["saque_morte_ts"]`. Isso é necessário porque o
motor faz curto-circuito no 1º comportamento que age — `Saque.avaliar` não roda em
todo tick, então ele não pode contar criaturas por conta própria de forma confiável.

Aqui só gerenciamos a CADÊNCIA dos presses: após uma morte, aperta a hotkey algumas
vezes dentro de `janela_s` (robusto ao tempo de o corpo ficar acessível).
Prioridade abaixo de `alvo` (ataca antes de saquear) e acima de `comer`.

Limitação: sem cavebot/movimento, o Quick Loot só pega se o personagem estiver
adjacente ao corpo (comum em melee). A filtragem de itens vive nas loot lists do Tibia.
"""

from __future__ import annotations

from bot.configuracao import SaqueConfig
from bot.contexto import Contexto
from bot.decisao.tipos import Decisao, TipoAcao

CHAVE_MORTE = "saque_morte_ts"


class Saque:
    nome = "saque"

    def __init__(self, saque: SaqueConfig):
        self.cfg = saque
        self.prioridade = saque.prioridade
        self._morte_vista = 0.0  # último morte_ts já processado
        self._proximo_press = 0.0  # ts do próximo press dentro da janela

    def avaliar(self, contexto: Contexto) -> Decisao | None:
        if not self.cfg.ativo:
            return None
        morte_ts = contexto.estado_comportamentos.get(CHAVE_MORTE)
        if morte_ts is None:
            return None

        ts = contexto.ts
        if morte_ts != self._morte_vista:
            self._morte_vista = morte_ts  # nova morte -> pode apertar já
            self._proximo_press = ts

        if ts > morte_ts + self.cfg.janela_s:
            return None  # janela de saque expirou
        if ts < self._proximo_press:
            return None  # ainda no intervalo entre presses

        self._proximo_press = ts + self.cfg.intervalo_press_s
        return Decisao(
            self.nome,
            TipoAcao.PRESSIONAR_TECLA,
            self.cfg.tecla,
            f"criatura morreu -> Quick Loot ({self.cfg.tecla.upper()})",
            self.prioridade,
            {"recurso": "saque"},
        )
