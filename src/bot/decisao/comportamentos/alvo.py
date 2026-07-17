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

**Watchdog "sem dano"** (`sem_dano_timeout_s`, mirror do watchdog de combate do
Cavebot): quando o alvo atual fica esse tempo sem perder vida nem morrer — mesmo
sendo reatacado a cada recompromisso_s — é sinal de alvo inalcançável/imune. Isso
NÃO muda qual criatura é atacada nem a cadência de cliques (recompromisso_s já cobre
isso); só anexa um aviso estático ao `motivo`, pra aparecer 1x no log do painel
(dedupe por string exata em loop_bot.py) sem spamar a cada tick.
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
        # watchdog "sem dano" (ver docstring do módulo)
        self._engajado_desde = 0.0
        self._ultimo_dano_visto = 0.0
        self._ultima_morte_vista = 0.0

    def avaliar(self, contexto: Contexto) -> Decisao | None:
        c = contexto.criaturas
        if c is None or c.confianca < self.confianca_minima:
            return None
        if c.n_criaturas <= 0:
            self._engajado_desde = 0.0  # fora de combate: zera o relógio do watchdog
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

        sufixo = ""
        if self._sem_dano_ha_muito(contexto.ts, estado):
            sufixo = (
                f" [sem dano há mais de {self.cfg.sem_dano_timeout_s:.0f}s"
                " — alvo pode estar inalcançável]"
            )

        if usar_tecla:
            return Decisao(
                self.nome,
                TipoAcao.PRESSIONAR_TECLA,
                tecla=self.cfg.tecla,
                motivo=f"{c.n_criaturas} criatura(s) na lista, sem alvo -> atacar ({self.cfg.tecla}){sufixo}",
                prioridade=self.prioridade,
                dados={"recurso": "alvo", "n": c.n_criaturas},
                chave_cooldown=CHAVE_COOLDOWN,
            )
        return Decisao(
            self.nome,
            TipoAcao.CLICAR,
            tecla=None,
            motivo=f"{c.n_criaturas} criatura(s) na lista, sem alvo -> atacar a 1ª{sufixo}",
            prioridade=self.prioridade,
            dados={"recurso": "alvo", "n": c.n_criaturas},
            ponto=c.ponto_clique,
            chave_cooldown=CHAVE_COOLDOWN,
        )

    def _sem_dano_ha_muito(self, ts: float, estado: dict) -> bool:
        """True = engajado há `sem_dano_timeout_s` sem sinal de dano nem morte no
        alvo atual — provável alvo inalcançável/imune. Só sinaliza (ver docstring do
        módulo); mirror do watchdog de combate do Cavebot (`_deve_ceder_combate`).

        O relógio só reseta em PROGRESSO real (`alvo_dano_ts`/`saque_morte_ts`
        avançando) — nunca por `alvo_engajado_ts` sozinho, que avança a cada
        recompromisso_s mesmo travado (senão o timeout nunca dispararia).
        """
        if self.cfg.sem_dano_timeout_s <= 0:
            return False
        dano_ts = estado.get("alvo_dano_ts", 0.0)
        morte_ts = estado.get("saque_morte_ts", 0.0)
        if self._engajado_desde == 0.0:
            self._engajado_desde = ts
            self._ultimo_dano_visto = dano_ts
            self._ultima_morte_vista = morte_ts
        if dano_ts > self._ultimo_dano_visto or morte_ts > self._ultima_morte_vista:
            self._ultimo_dano_visto = dano_ts
            self._ultima_morte_vista = morte_ts
            self._engajado_desde = ts
        return (ts - self._engajado_desde) >= self.cfg.sem_dano_timeout_s
