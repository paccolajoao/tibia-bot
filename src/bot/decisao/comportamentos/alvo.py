"""Alvo — targeting: clica (ou aperta a tecla "Attack Closest") para atacar.

Política: ataca quando há criatura presente e o engajamento anterior já se resolveu
— ou seja, depois de engajar, deixa o auto-attack do Tibia trabalhar e só RE-ataca
quando (a) uma criatura morre (a contagem da battle list cai) ou (b) o
`recompromisso_s` expira (rede de segurança p/ clique/tecla que não pegou o alvo).
Ignora leituras de confiança baixa. Prioridade abaixo de `auto_cura` => sobreviver
vem antes de atacar.

**Não dependemos do `alvo_atual`** (realce vermelho) para decidir atacar: aquela
leitura confunde o realce do alvo com a barra de HP avermelhada de bichos feridos, e
um falso-positivo faria o bot PARAR de atacar (ficar só curando) com bichos na tela —
inclusive logo após matar um de vários, ou ao subir escada. O controle de não-spam
fica todo no par engajamento+morte/timeout, que se apoia em sinais confiáveis
(contagem de criaturas e queda dessa contagem).

A ação é um CLICK nas coords absolutas da 1ª entrada (preenchidas pelo loop em
`ctx.criaturas.ponto_clique`) ou um PRESSIONAR_TECLA quando `alvo.tecla` está definida.
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

        # Após engajar, NÃO re-ataca até: (a) uma criatura morrer (queda na contagem) ou
        # (b) recompromisso_s expirar (rede de segurança p/ tecla/clique que não pegou).
        # O loop carimba `alvo_engajado_ts` a cada ataque executado, então este estado
        # se renova sozinho — e a morte (saque_morte_ts) destrava o re-ataque na hora.
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
