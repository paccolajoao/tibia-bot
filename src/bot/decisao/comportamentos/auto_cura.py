"""AutoCura — o comportamento do MVP.

Regras por prioridade: HP crítico -> cura forte; HP baixo -> cura leve; mana
baixa -> poção de mana. Ignora leituras com confiança abaixo do mínimo (evita
curar por causa de uma leitura suja).
"""

from __future__ import annotations

from bot.configuracao import CuraConfig
from bot.contexto import Contexto
from bot.decisao.tipos import Decisao, TipoAcao


class AutoCura:
    nome = "auto_cura"

    def __init__(self, cura: CuraConfig, confianca_minima: float, prioridade: int = 100):
        self.cura = cura
        self.confianca_minima = confianca_minima
        self.prioridade = prioridade

    def avaliar(self, contexto: Contexto) -> Decisao | None:
        c = self.cura
        hp = contexto.hp
        mana = contexto.mana

        if hp is not None and hp.confianca >= self.confianca_minima:
            if hp.percentual <= c.hp_critico:
                return self._decisao(
                    c.tecla_cura_forte,
                    f"HP {hp.percentual:.0f}% <= crítico {c.hp_critico:.0f}% -> cura forte ({c.tecla_cura_forte.upper()})",
                    {"recurso": "hp", "nivel": "critico", "hp": hp.percentual},
                )
            if hp.percentual <= c.hp_baixo:
                return self._decisao(
                    c.tecla_cura_leve,
                    f"HP {hp.percentual:.0f}% <= baixo {c.hp_baixo:.0f}% -> cura leve ({c.tecla_cura_leve.upper()})",
                    {"recurso": "hp", "nivel": "baixo", "hp": hp.percentual},
                )

        if mana is not None and mana.confianca >= self.confianca_minima:
            if mana.percentual <= c.mana_baixa:
                return self._decisao(
                    c.tecla_pocao_mana,
                    f"Mana {mana.percentual:.0f}% <= {c.mana_baixa:.0f}% -> poção de mana ({c.tecla_pocao_mana.upper()})",
                    {"recurso": "mana", "mana": mana.percentual},
                )

        return None

    def _decisao(self, tecla: str, motivo: str, dados: dict) -> Decisao:
        return Decisao(self.nome, TipoAcao.PRESSIONAR_TECLA, tecla, motivo, self.prioridade, dados)
