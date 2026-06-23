"""UsarMana — descarga de mana para treino de ML.

Enquanto mana >= mana_alto, pressiona a tecla configurada (cura forte por padrão)
para gastar mana. Para quando mana < mana_alvo (histerese p/ não oscilar na borda).
Prioridade baixa: roda só quando AutoCura, Alvo e Saque não têm nada a fazer.
"""

from __future__ import annotations

from bot.configuracao import UsarManaConfig
from bot.contexto import Contexto
from bot.decisao.tipos import Decisao, TipoAcao

CHAVE_COOLDOWN = "usar_mana"

# Mana cheia quase nunca lê exatamente 100% (bordas anti-aliased + dígitos sobre a
# barra). Um perfil salvo com mana_alto=100 nunca dispararia; tratamos qualquer
# limiar >= 100 como este valor alcançável.
LIMIAR_CHEIO_INATINGIVEL = 97.0


class UsarMana:
    nome = "usar_mana"

    def __init__(self, cfg: UsarManaConfig):
        self.cfg = cfg
        self.prioridade = cfg.prioridade
        self._gastando = False

    def avaliar(self, contexto: Contexto) -> Decisao | None:
        mana = contexto.mana
        if mana is None or mana.confianca < self.cfg.confianca_minima:
            return None

        # Treino de ML é tarefa de OCIOSO: cede a vez ao combate. Se há criaturas na
        # battle list, não gasta o tick treinando mana (evita travar ataque/saque mesmo
        # que a prioridade esteja alta). Sem battle list calibrada, `criaturas` é None.
        criaturas = contexto.criaturas
        if criaturas is not None and criaturas.n_criaturas > 0:
            return None

        limiar = self.cfg.mana_alto if self.cfg.mana_alto < 100.0 else LIMIAR_CHEIO_INATINGIVEL
        pct = mana.percentual
        if pct >= limiar:
            self._gastando = True
        elif pct < self.cfg.mana_alvo:
            self._gastando = False

        if not self._gastando:
            return None

        return Decisao(
            self.nome,
            TipoAcao.PRESSIONAR_TECLA,
            tecla=self.cfg.tecla,
            motivo=(
                f"Mana {pct:.0f}% >= {limiar:.0f}%"
                f" -> usar mana ({self.cfg.tecla.upper()})"
            ),
            prioridade=self.prioridade,
            dados={"recurso": "mana_uso", "mana": pct},
            chave_cooldown=CHAVE_COOLDOWN,
        )
