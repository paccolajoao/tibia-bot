"""Estatísticas acumuladas da sessão (mutadas só pela thread do bot)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Estatisticas:
    inicio_ts: float = field(default_factory=time.perf_counter)
    curas: int = 0  # curas de HP disparadas (forte + leve) — total
    curas_forte: int = 0  # subset: HP crítico -> cura forte
    curas_leve: int = 0  # subset: HP baixo -> cura leve
    pocoes_mana: int = 0  # poções de mana (HP/mana baixos)
    usos_mana: int = 0  # descargas de mana p/ treino de ML (comportamento usar_mana)
    ataques: int = 0  # cliques de alvo na battle list (targeting, não hits confirmados)
    refeicoes: int = 0  # presses de comida
    saques: int = 0  # presses de Quick Loot
    abates: int = 0  # quedas detectadas na contagem da battle list (aproxima kills)
    passos_cavebot: int = 0  # ações de navegação do cavebot executadas
    magias_ataque: int = 0  # casts da hotkey de magia de ataque (inputs enviados)
    _fps_ema: float = 0.0

    def registrar_acao(self, decisao) -> None:
        """Contabiliza uma ação executada, separando por `decisao.dados['recurso']`."""
        recurso = decisao.dados.get("recurso")
        if recurso == "mana":
            self.pocoes_mana += 1
        elif recurso == "mana_uso":
            self.usos_mana += 1
        elif recurso == "alvo":
            self.ataques += 1
        elif recurso == "comida":
            self.refeicoes += 1
        elif recurso == "saque":
            self.saques += 1
        elif recurso == "cavebot":
            self.passos_cavebot += 1
        elif recurso == "magia_ataque":
            self.magias_ataque += 1
        else:  # recurso == "hp" (cura de HP)
            self.curas += 1
            if decisao.dados.get("nivel") == "critico":
                self.curas_forte += 1
            else:
                self.curas_leve += 1

    def atualizar_fps(self, fps_instantaneo: float) -> None:
        alfa = 0.1
        if self._fps_ema <= 0.0:
            self._fps_ema = fps_instantaneo
        else:
            self._fps_ema = (1 - alfa) * self._fps_ema + alfa * fps_instantaneo

    @property
    def fps_medio(self) -> float:
        return self._fps_ema

    @property
    def uptime_s(self) -> float:
        return time.perf_counter() - self.inicio_ts
