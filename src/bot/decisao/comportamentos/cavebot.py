"""Cavebot — navegação por waypoints (clique no minimapa).

Caminha a hunt clicando pontos gravados no minimapa em sequência: o PRÓPRIO Tibia
faz o pathfinding de cada trecho. A "chegada" num waypoint `ir` é detectada quando o
minimapa PARA DE ROLAR (o loop expõe `minimap_movendo` em `estado_comportamentos`) —
sem precisar ler a posição mundial do player. A rota repete em loop circular.

Subida/descida de andar são waypoints `andar_em`/`usar`/`tecla`. Quando marcados com
`troca_andar=True`, o cavebot **valida a troca**: uma troca de andar substitui o
minimapa inteiro → um pico grande em `minimap_score`. Sem o pico dentro do timeout, ele
re-tenta a ação `tentativas_troca` vezes e, no pior caso, segue (não trava).

Como tarefa de movimento, **cede ao combate** — mas com um *watchdog*: se há criaturas e
nenhuma morte por `combate_timeout_s` (bicho inalcançável), volta a andar em vez de ceder
para sempre. Prioridade baixa por garantia.

Coordenadas dos waypoints estão em coords de FRAME/canvas; a flag `dados['transformar']`
faz o loop aplicar o mapeamento OBS->desktop no clique em runtime (ver loop_bot.py).

A transição "cliquei e estou esperando" só acontece quando a ação REALMENTE executa: o
loop carimba `cavebot_acao_ts` após executar uma ação do cavebot (como faz com o alvo).
"""

from __future__ import annotations

from bot.configuracao import CavebotConfig, Waypoint
from bot.contexto import Contexto
from bot.decisao.tipos import Decisao, TipoAcao

CHAVE_COOLDOWN = "cavebot"
CHAVE_ACAO_TS = "cavebot_acao_ts"        # carimbado pelo loop após executar nossa ação
CHAVE_MINIMAP_MOVENDO = "minimap_movendo"
CHAVE_MINIMAP_SCORE = "minimap_score"    # diff médio do minimapa (pico = troca de andar)
CHAVE_MORTE = "saque_morte_ts"           # ts da última morte (queda na battle list)


class Cavebot:
    nome = "cavebot"

    def __init__(self, cfg: CavebotConfig):
        self.cfg = cfg
        self.prioridade = cfg.prioridade
        self._idx = 0
        self._aguardando = False        # ação já executou; aguardando concluir o trecho
        self._inicio_espera = 0.0       # ts em que começamos a aguardar
        self._acao_ts_visto = 0.0       # último cavebot_acao_ts já processado
        self._parado_count = 0          # ticks consecutivos de minimapa estático
        self._viu_movimento = False     # minimapa chegou a rolar neste trecho
        # validação de troca de andar
        self._trocou = False
        self._inicio_troca = 0.0        # ts em que a troca foi confirmada (p/ assentar)
        self._tentativas_restantes = cfg.tentativas_troca
        # watchdog de combate
        self._combate_inicio = 0.0
        self._ultima_morte_vista = 0.0

    def avaliar(self, contexto: Contexto) -> Decisao | None:
        if not self.cfg.ativo:
            return None
        wps = self.cfg.waypoints
        if not wps:
            return None

        ts = contexto.ts
        estado = contexto.estado_comportamentos

        # Cede ao combate — mas com watchdog: se o combate não progride (nenhuma morte
        # por combate_timeout_s), provavelmente é um bicho inalcançável -> volta a andar.
        cr = contexto.criaturas
        em_combate = cr is not None and cr.n_criaturas > 0
        if em_combate:
            if self._deve_ceder_combate(ts, estado):
                return None
            # combate travado: NÃO cede — segue p/ a navegação abaixo (o personagem se
            # afasta nos intervalos do Alvo e o bicho some da battle list, destravando).
        else:
            self._combate_inicio = 0.0  # fora de combate: zera o relógio

        wp = wps[self._idx % len(wps)]

        # A nossa última ação foi confirmada como executada pelo loop?
        acao_ts = estado.get(CHAVE_ACAO_TS, 0.0)
        if acao_ts > self._acao_ts_visto:
            self._acao_ts_visto = acao_ts
            self._iniciar_espera(ts)

        if wp.tipo == "esperar":
            # waypoint de pausa pura: não emite ação, só aguarda dwell_s.
            if not self._aguardando:
                self._iniciar_espera(ts)
            if ts - self._inicio_espera >= max(0.0, wp.dwell_s):
                self._avancar()
            return None

        if self._aguardando:
            return self._verificar_conclusao(wp, ts, estado)

        # trecho novo: emite a ação do waypoint atual
        return self._emitir(wp)

    # ------------------------------------------------------------------ interno
    def _deve_ceder_combate(self, ts: float, estado: dict) -> bool:
        """True = cede a vez ao combate; False = combate travado, segue navegando."""
        morte_ts = estado.get(CHAVE_MORTE, 0.0)
        if self._combate_inicio == 0.0:
            self._combate_inicio = ts
            self._ultima_morte_vista = morte_ts
        if morte_ts > self._ultima_morte_vista:
            # progresso (matou algo): reinicia o relógio do combate
            self._ultima_morte_vista = morte_ts
            self._combate_inicio = ts
        if self.cfg.combate_timeout_s <= 0:
            return True  # 0 = nunca desiste
        return (ts - self._combate_inicio) < self.cfg.combate_timeout_s

    def _iniciar_espera(self, ts: float) -> None:
        self._aguardando = True
        self._inicio_espera = ts
        self._parado_count = 0
        self._viu_movimento = False
        self._trocou = False

    def _verificar_conclusao(self, wp: Waypoint, ts: float, estado: dict) -> Decisao | None:
        timeout = (ts - self._inicio_espera) >= self.cfg.timeout_trecho_s

        if wp.troca_andar:
            return self._verificar_troca_andar(wp, ts, estado, timeout)

        if wp.tipo == "ir":
            # chegada = minimapa rolou e depois ficou estático por parado_ticks.
            if bool(estado.get(CHAVE_MINIMAP_MOVENDO, False)):
                self._viu_movimento = True
                self._parado_count = 0
            else:
                self._parado_count += 1
            chegou = self._viu_movimento and self._parado_count >= self.cfg.parado_ticks
            if chegou or timeout:
                self._avancar()
            return None

        # dwell simples (andar_em/usar/tecla sem troca_andar): aguarda assentar e segue.
        if ts - self._inicio_espera >= max(0.0, wp.dwell_s):
            self._avancar()
        return None

    def _verificar_troca_andar(
        self, wp: Waypoint, ts: float, estado: dict, timeout: bool
    ) -> Decisao | None:
        """Confirma a troca de andar pelo pico do minimapa; re-tenta/segue se falhar."""
        score = float(estado.get(CHAVE_MINIMAP_SCORE, 0.0))
        if not self._trocou and score >= self.cfg.limiar_troca_andar:
            self._trocou = True
            self._inicio_troca = ts  # confirmou: agora deixa assentar

        if self._trocou:
            if ts - self._inicio_troca >= max(0.0, wp.dwell_s):
                self._avancar()
            return None

        if timeout:
            self._tentativas_restantes -= 1
            if self._tentativas_restantes > 0:
                # re-tenta a ação: sai de "aguardando" p/ o _emitir rodar de novo
                self._aguardando = False
            else:
                # esgotou as tentativas: segue p/ não travar (best-effort)
                self._avancar()
        return None

    def _avancar(self) -> None:
        self._idx = (self._idx + 1) % len(self.cfg.waypoints)
        self._aguardando = False
        self._parado_count = 0
        self._viu_movimento = False
        self._trocou = False
        self._tentativas_restantes = self.cfg.tentativas_troca

    def _emitir(self, wp: Waypoint) -> Decisao | None:
        rotulo = wp.nome or f"#{self._idx}"
        sufixo = self._sufixo_tentativa(wp)
        base_dados = {"recurso": "cavebot", "tipo": wp.tipo, "idx": self._idx}

        if wp.tipo == "tecla":
            if not wp.tecla:
                self._avancar()  # waypoint inválido: pula
                return None
            return Decisao(
                self.nome,
                TipoAcao.PRESSIONAR_TECLA,
                tecla=wp.tecla,
                motivo=f"cavebot {rotulo}: tecla {wp.tecla}{sufixo}",
                prioridade=self.prioridade,
                dados=base_dados,
                chave_cooldown=CHAVE_COOLDOWN,
            )

        if wp.tipo == "usar":
            return Decisao(
                self.nome,
                TipoAcao.CLICAR_DIREITO,
                tecla=None,
                motivo=f"cavebot {rotulo}: usar (clique-direito){sufixo}",
                prioridade=self.prioridade,
                dados={**base_dados, "transformar": True},
                ponto=(wp.x, wp.y),
                chave_cooldown=CHAVE_COOLDOWN,
            )

        # "ir" (minimapa) e "andar_em" (tile do game-world) = clique esquerdo
        motivo = (
            f"cavebot {rotulo}: andar no minimapa"
            if wp.tipo == "ir"
            else f"cavebot {rotulo}: pisar no tile (troca de andar){sufixo}"
        )
        return Decisao(
            self.nome,
            TipoAcao.CLICAR,
            tecla=None,
            motivo=motivo,
            prioridade=self.prioridade,
            dados={**base_dados, "transformar": True},
            ponto=(wp.x, wp.y),
            chave_cooldown=CHAVE_COOLDOWN,
        )

    def _sufixo_tentativa(self, wp: Waypoint) -> str:
        """Mostra a tentativa no log quando estamos re-tentando uma troca de andar."""
        if not wp.troca_andar:
            return ""
        usada = self.cfg.tentativas_troca - self._tentativas_restantes
        if usada <= 0:
            return ""
        return f" [troca não confirmada, tentativa {usada + 1}/{self.cfg.tentativas_troca}]"
