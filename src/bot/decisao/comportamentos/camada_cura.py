"""Camadas de auto-cura (substitui o antigo AutoCura).

Uma instância de `CamadaCura` = uma regra "quando a barra X <= limiar, aperte a
tecla T". O sistema roda 4 camadas com prioridades distintas; o `MotorDecisao` faz
a cascata (uma ação por tick; camada bloqueada por cooldown CEDE à de prioridade
menor), o que empilha magia + poção em ticks adjacentes (~66ms a 15fps = mesmo
"turno" do Tibia).

Grupos de cooldown do Tibia modelados aqui:
- magia e poção são grupos diferentes -> podem sair no mesmo turno (chaves distintas);
- duas poções (vida + mana) compartilham `CHAVE_CD_POCAO` -> nunca no mesmo turno.

Camadas (prioridade desc):
- cura_forte  (magia emergência, HP <= hp_critico)     -> chave própria, cd longo
- pocao_vida  (poção de vida,    HP <= hp_pocao_vida)   -> CHAVE_CD_POCAO
- cura_leve   (magia básica,     HP <= hp_baixo)        -> chave própria
- pocao_mana  (poção de mana,    mana <= mana_baixa)    -> CHAVE_CD_POCAO (compartilhada)
                com trava: não bebe se HP confiável <= mana_hp_seguro (reserva o
                cooldown das poções p/ a vida).
"""

from __future__ import annotations

from bot.configuracao import CuraConfig
from bot.contexto import Contexto
from bot.decisao.tipos import Decisao, TipoAcao

# Chaves de cooldown (por GRUPO, não por tecla). Poção de vida e mana compartilham.
CHAVE_CD_CURA_FORTE = "cura_forte"
CHAVE_CD_CURA_LEVE = "cura_leve"
CHAVE_CD_POCAO = "grupo_pocao"

# Prioridades: todas acima de saque(85)/alvo(80)/magia(70) — sobreviver antes de atacar.
PRIO_CURA_FORTE = 106
PRIO_POCAO_VIDA = 104
PRIO_CURA_LEVE = 102
PRIO_POCAO_MANA = 100


class CamadaCura:
    """Uma camada de cura. Observa uma barra (`hp`|`mana`) e dispara <= limiar."""

    def __init__(
        self,
        *,
        nome: str,
        barra: str,  # "hp" | "mana": qual leitura observar
        limiar: float,  # dispara quando percentual <= limiar
        tecla: str,
        chave_cooldown: str,
        prioridade: int,
        confianca_minima: float,
        dados: dict,  # gravado na Decisao -> drive das estatísticas
        rotulo: str,  # texto humano do motivo ("cura forte", "poção de vida"...)
        hp_seguro: float | None = None,  # só p/ poção de mana: não bebe se HP <= isto
    ):
        self.nome = nome
        self.barra = barra
        self.limiar = limiar
        self.tecla = tecla
        self.chave_cooldown = chave_cooldown
        self.prioridade = prioridade
        self.confianca_minima = confianca_minima
        self._dados = dados
        self.rotulo = rotulo
        self.hp_seguro = hp_seguro

    def avaliar(self, contexto: Contexto) -> Decisao | None:
        leitura = contexto.hp if self.barra == "hp" else contexto.mana
        if leitura is None or leitura.confianca < self.confianca_minima:
            return None
        if leitura.percentual > self.limiar:
            return None

        # Trava de segurança de HP p/ a poção de mana: não gasta o cooldown
        # COMPARTILHADO das poções enquanto o HP confiável estiver baixo.
        if self.hp_seguro is not None:
            hp = contexto.hp
            if hp is not None and hp.confianca >= self.confianca_minima and hp.percentual <= self.hp_seguro:
                return None

        return Decisao(
            self.nome,
            TipoAcao.PRESSIONAR_TECLA,
            self.tecla,
            f"{self.barra.upper()} {leitura.percentual:.0f}% <= {self.limiar:.0f}%"
            f" -> {self.rotulo} ({self.tecla.upper()})",
            self.prioridade,
            dict(self._dados),  # cópia defensiva (a Decisao viaja pela telemetria)
            chave_cooldown=self.chave_cooldown,
        )


def montar_camadas_cura(cura: CuraConfig, confianca_minima: float) -> list[CamadaCura]:
    """Fonte ÚNICA das 4 camadas (usada por executar.py e pelos testes)."""
    return [
        CamadaCura(
            nome="cura_forte", barra="hp", limiar=cura.hp_critico,
            tecla=cura.tecla_cura_forte, chave_cooldown=CHAVE_CD_CURA_FORTE,
            prioridade=PRIO_CURA_FORTE, confianca_minima=confianca_minima,
            dados={"recurso": "hp", "nivel": "critico"}, rotulo="cura forte",
        ),
        CamadaCura(
            nome="pocao_vida", barra="hp", limiar=cura.hp_pocao_vida,
            tecla=cura.tecla_pocao_vida, chave_cooldown=CHAVE_CD_POCAO,
            prioridade=PRIO_POCAO_VIDA, confianca_minima=confianca_minima,
            dados={"recurso": "pocao_vida"}, rotulo="poção de vida",
        ),
        CamadaCura(
            nome="cura_leve", barra="hp", limiar=cura.hp_baixo,
            tecla=cura.tecla_cura_leve, chave_cooldown=CHAVE_CD_CURA_LEVE,
            prioridade=PRIO_CURA_LEVE, confianca_minima=confianca_minima,
            dados={"recurso": "hp", "nivel": "baixo"}, rotulo="cura leve",
        ),
        CamadaCura(
            nome="pocao_mana", barra="mana", limiar=cura.mana_baixa,
            tecla=cura.tecla_pocao_mana, chave_cooldown=CHAVE_CD_POCAO,
            prioridade=PRIO_POCAO_MANA, confianca_minima=confianca_minima,
            dados={"recurso": "mana"}, rotulo="poção de mana",
            hp_seguro=cura.mana_hp_seguro,
        ),
    ]


def cooldowns_cura(cura: CuraConfig) -> dict[str, float]:
    """Dict de cooldown por GRUPO (chaves = chave_cd das camadas)."""
    return {
        CHAVE_CD_CURA_FORTE: cura.cd_cura_forte,
        CHAVE_CD_CURA_LEVE: cura.cd_cura_leve,
        CHAVE_CD_POCAO: cura.cd_pocao,
    }
