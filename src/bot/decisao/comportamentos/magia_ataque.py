"""MagiaAtaque — aperta UMA hotkey de ataque enquanto há criatura em combate.

A *rotação* de magias (ex.: exori -> exori gran -> exori mas) é montada no PRÓPRIO
Tibia naquela hotkey; o bot só a aciona periodicamente. Respeita um **piso de mana**
(`mana_minima`) para não esvaziar a mana necessária para a cura. Prioridade abaixo de
cura/saque/alvo: ataca nos intervalos, sem atropelar sobrevivência/loot/targeting.

O espaçamento entre casts é o cooldown da chave `magia_ataque` (= `intervalo_s`),
registrado pelo `executar.py` no GerenciadorCooldown.
"""

from __future__ import annotations

from bot.configuracao import MagiaAtaqueConfig
from bot.contexto import Contexto
from bot.decisao.tipos import Decisao, TipoAcao

CHAVE_COOLDOWN = "magia_ataque"


class MagiaAtaque:
    nome = "magia_ataque"

    def __init__(self, cfg: MagiaAtaqueConfig):
        self.cfg = cfg
        self.prioridade = cfg.prioridade

    def avaliar(self, contexto: Contexto) -> Decisao | None:
        if not self.cfg.ativo:
            return None

        # só em combate (há criatura na battle list)
        cr = contexto.criaturas
        if cr is None or cr.n_criaturas <= 0:
            return None

        # piso de mana: preserva mana p/ cura (só barra se a leitura for confiável)
        mana = contexto.mana
        if (
            mana is not None
            and mana.confianca >= self.cfg.confianca_minima
            and mana.percentual < self.cfg.mana_minima
        ):
            return None

        return Decisao(
            self.nome,
            TipoAcao.PRESSIONAR_TECLA,
            tecla=self.cfg.tecla,
            motivo=f"combate -> magia de ataque ({self.cfg.tecla.upper()})",
            prioridade=self.prioridade,
            dados={"recurso": "magia_ataque"},
            chave_cooldown=CHAVE_COOLDOWN,
        )
