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

        usar_tecla = bool(self.cfg.tecla)
        if not usar_tecla and c.ponto_clique is None:
            return None
        if c.alvo_atual:
            # o client mostra alvo ativo (realce vermelho): não troca.
            # Limpa o engajamento: o ataque pegou. Assim, quando o alvo sumir
            # (morrer/fugir), o re-clique é IMEDIATO — sem esperar recompromisso_s
            # de um engajamento velho que ficaria preso travando o próximo alvo.
            contexto.estado_comportamentos.pop("alvo_engajado_ts", None)
            return None

        # Após engajar, NÃO re-ataca até: (a) criatura morrer ou (b) recompromisso_s
        # expirar (rede de segurança para tecla/clique que não pegou o alvo).
        estado = contexto.estado_comportamentos
        engajado_ts = estado.get("alvo_engajado_ts")
        if engajado_ts is not None:
            morte_ts = estado.get("saque_morte_ts", 0.0)
            matou_desde = morte_ts > engajado_ts
            if not matou_desde and (contexto.ts - engajado_ts) < self.recompromisso_s:
                return None

        if usar_tecla:
            return Decisao(
                self.nome,
                TipoAcao.PRESSIONAR_TECLA,
                tecla=self.cfg.tecla,
                motivo=f"{c.n_criaturas} criatura(s) na lista, sem alvo -> atacar ({self.cfg.tecla})",
                prioridade=self.prioridade,
                dados={"recurso": "alvo", "n": c.n_criaturas},
                chave_cooldown=CHAVE_COOLDOWN,
            )
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
