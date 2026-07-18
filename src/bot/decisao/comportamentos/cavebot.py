"""Cavebot — navegação por waypoints (clique no minimapa).

Caminha a hunt clicando pontos no minimapa em sequência: o PRÓPRIO Tibia faz o
pathfinding de cada trecho. A rota repete em loop circular.

**Modo MARCA (recomendado)** — um waypoint `ir` com `marca` preenchida aponta para uma
MARCA nativa do Tibia (ícone cadastrado). O loop detecta o ícone no minimapa e publica
seu offset do centro (`cavebot_marca_offset`). A navegação é **CONTÍNUA**: a cada ciclo o
cavebot re-lê a posição VIVA da marca e **re-clica** em `centro+offset` (o motor gateia o
re-clique pelo `cooldown_s`), até a marca **convergir ao centro** (offset ≤ `marca_raio_centro`)
= CHEGADA → próxima marca. Como o alvo é sempre a posição ATUAL do ícone, deslocamento por
combate/obstáculo não gera clique obsoleto: matou o bicho no meio do caminho, o próximo clique
já sai para onde a marca está agora. Se a marca não for detectada por `timeout_trecho_s`, pula
(seguro: posição absoluta, o próximo trecho se auto-realinha).

**Modo OFFSET (legado)** — waypoint `ir` sem `marca`: `x`/`y` são offset relativo ao
centro do minimapa; a chegada é detectada quando o minimapa PARA DE ROLAR
(`minimap_movendo`). Frágil (pausa entre passos parece "chegada"); prefira o modo marca.

Subida/descida de andar são waypoints `andar_em`/`usar`/`tecla` com `troca_andar=True`: o
cavebot **valida a troca** por mudança PERSISTENTE do minimapa (`minimap_diff_ref` ≥
`limiar_troca_andar` + assentado), re-tenta `tentativas_troca` vezes e, no pior caso, segue.

Como tarefa de movimento, **cede ao combate** — mas com um *watchdog*: se há criaturas e
nenhuma morte por `combate_timeout_s` (bicho inalcançável), volta a andar. Prioridade baixa.

A flag `dados['relativo_centro']` faz o loop somar o centro do minimapa antes de clicar; a
flag `dados['transformar']` aplica o mapeamento OBS->desktop. A transição "cliquei e estou
esperando" só ocorre quando a ação REALMENTE executa: o loop carimba `cavebot_acao_ts`.
"""

from __future__ import annotations

from bot.configuracao import CavebotConfig, Waypoint
from bot.contexto import Contexto
from bot.decisao.tipos import Decisao, TipoAcao

CHAVE_COOLDOWN = "cavebot"
CHAVE_ACAO_TS = "cavebot_acao_ts"        # carimbado pelo loop após executar nossa ação
CHAVE_MINIMAP_MOVENDO = "minimap_movendo"
CHAVE_MINIMAP_SCORE = "minimap_score"    # diff médio entre frames consecutivos (rolagem)
CHAVE_MINIMAP_DIFF_REF = "minimap_diff_ref"  # diff vs. referência pré-ação (troca persistente)
CHAVE_MORTE = "saque_morte_ts"           # ts da última morte (queda na battle list)
# navegação por marca (loop <-> cavebot via estado_comportamentos)
CHAVE_MARCA_ALVO = "cavebot_marca_alvo"        # o cavebot pede: detecte ESTA marca
CHAVE_MARCA_OFFSET = "cavebot_marca_offset"    # o loop responde: offset (dx,dy) do centro | None
CHAVE_MARCA_OFFSET_DE = "cavebot_marca_offset_de"  # de qual marca é o offset (ignora stale)
CHAVE_MARCA_SCORE = "cavebot_marca_score"      # confiança do último match (0..1)
# status legível p/ o dashboard (o loop copia p/ o SnapshotEstado)
CHAVE_STATUS = "cavebot_status"


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
        # navegação por marca
        self._marca_vista = False       # já detectamos a marca deste trecho ao menos 1x
        self._marca_ultimo_dist2 = 10**9  # último |offset|² visto (p/ chegada ao perder a marca)
        self._marca_busca_inicio = 0.0  # ts do início da BUSCA (antes de clicar) — p/ timeout
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
        wp = wps[self._idx % len(wps)]

        # Cede ao combate — mas com watchdog: se o combate não progride (nenhuma morte
        # por combate_timeout_s), provavelmente é um bicho inalcançável -> volta a andar.
        cr = contexto.criaturas
        em_combate = cr is not None and cr.n_criaturas > 0
        if em_combate:
            if self._deve_ceder_combate(ts, estado):
                self._publicar_status(estado, "cedendo ao combate", wp)
                return None
            # combate travado: NÃO cede — segue p/ a navegação abaixo (o personagem se
            # afasta nos intervalos do Alvo e o bicho some da battle list, destravando).
        else:
            self._combate_inicio = 0.0  # fora de combate: zera o relógio

        # Navegação por MARCA: laço contínuo (re-detecta e re-clica a posição viva do
        # ícone). Não usa a maquinaria de _aguardando/cavebot_acao_ts abaixo.
        if self._eh_marca(wp):
            return self._navegar_marca(wp, ts, estado)
        estado[CHAVE_MARCA_ALVO] = None  # não é marca: para de pedir detecção ao loop

        # A nossa última ação foi confirmada como executada pelo loop?
        acao_ts = estado.get(CHAVE_ACAO_TS, 0.0)
        if acao_ts > self._acao_ts_visto:
            self._acao_ts_visto = acao_ts
            self._iniciar_espera(ts)

        if wp.tipo == "esperar":
            # waypoint de pausa pura: não emite ação, só aguarda dwell_s.
            self._publicar_status(estado, "esperando", wp)
            if not self._aguardando:
                self._iniciar_espera(ts)
            if ts - self._inicio_espera >= max(0.0, wp.dwell_s):
                self._avancar()
            return None

        self._publicar_status(estado, self._fase_offset(wp), wp)
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
        """Confirma a troca de andar por mudança PERSISTENTE do minimapa; re-tenta/segue se falhar.

        Uma troca real substitui o mapa inteiro e o deixa persistentemente diferente da
        referência pré-ação (`minimap_diff_ref`), depois assenta (`minimap_movendo=False`).
        Um pico transitório (respawn/teleporte/combate) volta a um mapa parecido -> diff_ref
        cai a ~0 e NÃO confirma, evitando avançar o waypoint no lugar errado.
        """
        diff_ref = float(estado.get(CHAVE_MINIMAP_DIFF_REF, 0.0))
        assentado = not bool(estado.get(CHAVE_MINIMAP_MOVENDO, False))
        if not self._trocou and diff_ref >= self.cfg.limiar_troca_andar and assentado:
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

    # ------------------------------------------------------------ navegação por marca
    def _eh_marca(self, wp: Waypoint) -> bool:
        """Waypoint de navegação por MARCA nativa: tipo 'ir' com uma marca cadastrada
        (e sem troca de andar, que tem sua própria validação)."""
        return wp.tipo == "ir" and bool(wp.marca) and not wp.troca_andar

    def _offset_marca(self, wp: Waypoint, estado: dict) -> tuple[int, int] | None:
        """Offset (dx,dy) da marca atual — só se a detecção do loop for para ESTA marca
        (ignora leitura stale de outra marca) e ela estiver visível."""
        if estado.get(CHAVE_MARCA_OFFSET_DE) != wp.marca:
            return None
        return estado.get(CHAVE_MARCA_OFFSET)

    def _navegar_marca(self, wp: Waypoint, ts: float, estado: dict) -> Decisao | None:
        """Laço CONTÍNUO de navegação por marca: a cada ciclo re-lê a posição viva do
        ícone no minimapa e re-clica nela (o motor gateia pelo `cooldown_s`), até a marca
        chegar ao centro. Re-detectar sempre torna o alvo imune a deslocamento (combate/
        obstáculo): não há posição de tela obsoleta.

        - detectada e no centro (|offset| ≤ raio) -> chegou -> próxima marca;
        - detectada e longe -> re-clica a posição VIVA;
        - não detectada perto do centro + minimapa assentado -> ficou sob o boneco = chegou;
        - não detectada por `timeout_trecho_s` -> pula (seguro: absoluta).
        """
        estado[CHAVE_MARCA_ALVO] = wp.marca  # pede ao loop p/ detectar ESTA marca
        offset = self._offset_marca(wp, estado)
        raio = self.cfg.marca_raio_centro

        if offset is not None:
            self._marca_busca_inicio = 0.0
            self._marca_vista = True
            dx, dy = offset
            self._marca_ultimo_dist2 = dx * dx + dy * dy
            if self._marca_ultimo_dist2 <= raio * raio:
                self._publicar_status(estado, "chegou na marca", wp)
                self._avancar()  # marca no centro = chegou
                return None
            self._publicar_status(estado, "andando até a marca", wp)
            return self._clique_marca(wp, offset)  # re-clica a posição viva

        # não detectada neste tick
        movendo = bool(estado.get(CHAVE_MINIMAP_MOVENDO, False))
        if self._marca_vista and not movendo and self._marca_ultimo_dist2 <= (2 * raio) ** 2:
            self._publicar_status(estado, "chegou na marca", wp)
            self._avancar()  # sumiu perto do centro e parou -> ficou sob o boneco = chegou
            return None
        if self._marca_busca_inicio == 0.0:
            self._marca_busca_inicio = ts
        self._publicar_status(estado, "procurando a marca (não detectada)", wp)
        if ts - self._marca_busca_inicio >= self.cfg.timeout_trecho_s:
            self._avancar()  # não achou a tempo -> pula (seguro: o próximo se realinha)
        return None

    def _clique_marca(self, wp: Waypoint, offset: tuple[int, int]) -> Decisao:
        """Decisão de clique na posição viva da marca (offset relativo ao centro)."""
        rotulo = wp.nome or f"#{self._idx}"
        return Decisao(
            self.nome,
            TipoAcao.CLICAR,
            tecla=None,
            motivo=f"cavebot {rotulo}: andar até a marca '{wp.marca}'",
            prioridade=self.prioridade,
            dados={
                "recurso": "cavebot",
                "tipo": wp.tipo,
                "idx": self._idx,
                "troca_andar": False,
                "transformar": True,
                "relativo_centro": True,
            },
            ponto=offset,
            chave_cooldown=CHAVE_COOLDOWN,
        )

    def _avancar(self) -> None:
        self._idx = (self._idx + 1) % len(self.cfg.waypoints)
        self._aguardando = False
        self._parado_count = 0
        self._viu_movimento = False
        self._trocou = False
        self._tentativas_restantes = self.cfg.tentativas_troca
        self._marca_vista = False
        self._marca_ultimo_dist2 = 10**9
        self._marca_busca_inicio = 0.0

    def _emitir(self, wp: Waypoint) -> Decisao | None:
        rotulo = wp.nome or f"#{self._idx}"
        sufixo = self._sufixo_tentativa(wp)
        dir_ = self._prefixo_direcao(wp)  # "subir "/"descer "/"" p/ o log
        base_dados = {
            "recurso": "cavebot",
            "tipo": wp.tipo,
            "idx": self._idx,
            "troca_andar": wp.troca_andar,  # o loop tira a referência pré-ação quando True
        }

        if wp.tipo == "tecla":
            if not wp.tecla:
                self._avancar()  # waypoint inválido: pula
                return None
            return Decisao(
                self.nome,
                TipoAcao.PRESSIONAR_TECLA,
                tecla=wp.tecla,
                motivo=f"cavebot {rotulo}: {dir_}tecla {wp.tecla}{sufixo}",
                prioridade=self.prioridade,
                dados=base_dados,
                chave_cooldown=CHAVE_COOLDOWN,
            )

        if wp.tipo == "usar":
            return Decisao(
                self.nome,
                TipoAcao.CLICAR_DIREITO,
                tecla=None,
                motivo=f"cavebot {rotulo}: {dir_}usar (clique-direito){sufixo}",
                prioridade=self.prioridade,
                dados={**base_dados, "transformar": True},
                ponto=(wp.x, wp.y),
                chave_cooldown=CHAVE_COOLDOWN,
            )

        # "ir" (minimapa) e "andar_em" (tile do game-world) = clique esquerdo
        if wp.tipo == "ir":
            # wp.x/wp.y são offset relativo ao centro do minimapa; o loop soma o centro.
            return Decisao(
                self.nome,
                TipoAcao.CLICAR,
                tecla=None,
                motivo=f"cavebot {rotulo}: andar no minimapa",
                prioridade=self.prioridade,
                dados={**base_dados, "transformar": True, "relativo_centro": True},
                ponto=(wp.x, wp.y),
                chave_cooldown=CHAVE_COOLDOWN,
            )
        return Decisao(
            self.nome,
            TipoAcao.CLICAR,
            tecla=None,
            motivo=f"cavebot {rotulo}: {dir_}pisar no tile (troca de andar){sufixo}",
            prioridade=self.prioridade,
            dados={**base_dados, "transformar": True},
            ponto=(wp.x, wp.y),
            chave_cooldown=CHAVE_COOLDOWN,
        )

    def _fase_offset(self, wp: Waypoint) -> str:
        """Rótulo de fase p/ o dashboard nos modos NÃO-marca."""
        if wp.troca_andar:
            return "troca de andar"
        return {
            "ir": "andando (offset)",
            "andar_em": "pisar no tile",
            "usar": "usar objeto",
            "tecla": "tecla",
        }.get(wp.tipo, wp.tipo)

    def _publicar_status(self, estado: dict, fase: str, wp: Waypoint) -> None:
        """Escreve um resumo legível do que o cavebot está fazendo p/ o dashboard.
        O loop copia `cavebot_status` para o SnapshotEstado (ver loop_bot._publicar_estado)."""
        marca = wp.marca if self._eh_marca(wp) else ""
        detectada = (
            bool(marca)
            and estado.get(CHAVE_MARCA_OFFSET_DE) == marca
            and estado.get(CHAVE_MARCA_OFFSET) is not None
        )
        offset = estado.get(CHAVE_MARCA_OFFSET) if detectada else None
        estado[CHAVE_STATUS] = {
            "idx": self._idx,
            "total": len(self.cfg.waypoints),
            "rotulo": wp.nome or f"#{self._idx}",
            "tipo": wp.tipo,
            "fase": fase,
            "marca": marca,
            "marca_detectada": detectada,
            "marca_score": round(float(estado.get(CHAVE_MARCA_SCORE, 0.0)), 3),
            "marca_offset": list(offset) if offset else None,
            "minimap_movendo": bool(estado.get(CHAVE_MINIMAP_MOVENDO, False)),
        }

    def _prefixo_direcao(self, wp: Waypoint) -> str:
        """Rótulo 'subir '/'descer ' p/ o log (organização da rota); '' se não definido."""
        if wp.direcao in ("subir", "descer"):
            return f"{wp.direcao} "
        return ""

    def _sufixo_tentativa(self, wp: Waypoint) -> str:
        """Mostra a tentativa no log quando estamos re-tentando uma troca de andar."""
        if not wp.troca_andar:
            return ""
        usada = self.cfg.tentativas_troca - self._tentativas_restantes
        if usada <= 0:
            return ""
        return f" [troca não confirmada, tentativa {usada + 1}/{self.cfg.tentativas_troca}]"
