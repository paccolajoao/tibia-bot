"""Alvo — targeting: clica na battle list para atacar uma criatura.

Política: só ataca quando há criatura presente E nenhuma já sendo atacada
(`alvo_atual`). Ignora leituras de confiança baixa (evita clicar por causa de uma
leitura suja). Prioridade abaixo de `auto_cura` => sobreviver vem antes de atacar.

A ação é um CLICK nas coords absolutas da 1ª entrada (preenchidas pelo loop em
`ctx.criaturas.ponto_clique`).
"""

from __future__ import annotations

from bot.configuracao import AlvoConfig
from bot.contexto import Contexto
from bot.decisao.tipos import Decisao, TipoAcao

CHAVE_COOLDOWN = "atacar"


class Alvo:
    nome = "alvo"

    def __init__(self, alvo: AlvoConfig, confianca_minima: float | None = None):
        self.cfg = alvo
        self.prioridade = alvo.prioridade
        self.confianca_minima = (
            confianca_minima if confianca_minima is not None else alvo.confianca_minima
        )
        self.recompromisso_s = alvo.recompromisso_s

    def avaliar(self, contexto: Contexto) -> Decisao | None:
        c = contexto.criaturas
        if c is None or c.confianca < self.confianca_minima:
            return None
        if c.n_criaturas <= 0:
            return None
        if c.ponto_clique is None:
            return None
        if c.alvo_atual:
            return None  # o client mostra alvo ativo (realce vermelho): não troca

        # Um clique já fixa o alvo no Tibia e o char auto-ataca até a morte. Então,
        # depois de engajar, NÃO re-clicamos (evita ficar trocando de bicho): só
        # voltamos a atacar quando uma criatura morre (precisa de novo alvo) ou após
        # `recompromisso_s` — rede de segurança caso o clique não tenha pego o alvo.
        estado = contexto.estado_comportamentos
        engajado_ts = estado.get("alvo_engajado_ts")
        if engajado_ts is not None:
            morte_ts = estado.get("saque_morte_ts", 0.0)
            matou_desde = morte_ts > engajado_ts
            if not matou_desde and (contexto.ts - engajado_ts) < self.recompromisso_s:
                return None  # ainda engajado: deixa o alvo atual ser morto

        return Decisao(
            self.nome,
            TipoAcao.CLICAR,
            tecla=None,
            motivo=f"{c.n_criaturas} criatura(s) na lista, sem alvo -> atacar a 1ª",
            prioridade=self.prioridade,
            dados={"recurso": "alvo", "n": c.n_criaturas},
            ponto=c.ponto_clique,
            chave_cooldown=CHAVE_COOLDOWN,
        )
