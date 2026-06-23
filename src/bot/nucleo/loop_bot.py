"""LoopBot: o loop SÍNCRONO captura -> visão -> decisão -> input -> telemetria.

Roda na própria thread (dono do Contexto). Publica eventos no barramento; nunca
toca no event loop do FastAPI. Cadência estável via `fps_alvo`; o preview anotado
e as stats têm throttle próprio para não inundar o WebSocket.

`max_ticks` existe só para testes (roda N ticks e para).
"""

from __future__ import annotations

import base64
import threading
import time

import cv2

from bot.captura.base import Regiao
from bot.decisao.tipos import Decisao, TipoAcao
from bot.nucleo.estado_execucao import ControladorExecucao, EstadoExecucao
from bot.telemetria import eventos as ev
from bot.visao.anotador import desenhar_overlay
from bot.visao.barra_recursos import ler_percentual_barra
from bot.visao.lista_batalha import detectar_criaturas
from bot.visao.tipos import DeteccaoCriaturas, LeituraBarra


def _combinar_regioes(*regioes: Regiao) -> Regiao:
    ls = [r[0] for r in regioes]
    ts = [r[1] for r in regioes]
    rs = [r[2] for r in regioes]
    bs = [r[3] for r in regioes]
    return (min(ls), min(ts), max(rs), max(bs))


def _absoluto_para_imagem(regiao_abs: Regiao, frame_regiao: Regiao | None) -> Regiao:
    """Converte uma região absoluta do desktop para coords dentro do frame capturado."""
    if frame_regiao is None:
        return regiao_abs
    fl, ft, _, _ = frame_regiao
    left, top, right, bottom = regiao_abs
    return (left - fl, top - ft, right - fl, bottom - ft)


def _leitura_dict(leitura: LeituraBarra | None) -> dict | None:
    if leitura is None:
        return None
    return {"percentual": round(leitura.percentual, 1), "confianca": round(leitura.confianca, 2)}


def _criaturas_dict(det: DeteccaoCriaturas | None) -> dict | None:
    if det is None:
        return None
    return {
        "n": det.n_criaturas,
        "alvo_atual": det.alvo_atual,
        "confianca": round(det.confianca, 2),
    }


def _ampliar_se_pequeno(imagem, alvo_largura: int = 360):
    altura, largura = imagem.shape[:2]
    if largura >= alvo_largura:
        return imagem
    escala = alvo_largura / max(1, largura)
    return cv2.resize(
        imagem,
        (int(largura * escala), int(altura * escala)),
        interpolation=cv2.INTER_NEAREST,
    )


class LoopBot(threading.Thread):
    def __init__(
        self,
        contexto,
        capturador,
        entrada,
        motor,
        controlador: ControladorExecucao,
        seguranca,
        barramento,
        max_ticks: int | None = None,
    ):
        super().__init__(name="LoopBot", daemon=True)
        self.ctx = contexto
        self.cap = capturador
        self.entrada = entrada
        self.motor = motor
        self.ctrl = controlador
        self.seg = seguranca
        self.bus = barramento
        self._max_ticks = max_ticks

        cfg = contexto.config
        self._reg_hp = tuple(cfg.regioes.hp)
        self._reg_mana = tuple(cfg.regioes.mana)
        self._regiao_combinada = _combinar_regioes(self._reg_hp, self._reg_mana)
        self._battle_ativo = cfg.regioes.battle_list_calibrado
        self._reg_battle = tuple(cfg.regioes.battle_list) if self._battle_ativo else None
        self._periodo = 1.0 / max(1.0, cfg.captura.fps_alvo)
        self._periodo_quadro = 1.0 / max(1.0, cfg.painel.fps_quadro)
        self._ultimo_motivo: str | None = None
        self._ultimo_quadro_ts = 0.0
        self._ultimo_stats_ts = 0.0
        # rastreio de mortes p/ o auto-loot (Saque lê via estado_comportamentos)
        self._saque_conf_min = cfg.saque.confianca_minima
        self._ultimo_n_criaturas: int | None = None
        # detecção de frames pretos (backend WGC retornando preto para DX11 Blt-model)
        self._ticks_sem_confianca = 0
        self._fallback_mss_feito = False
        # foco da janela do Tibia: gateia o INPUT (não a leitura). None = ainda não avaliado
        self._ultimo_foco: bool | None = None
        # backend OBS: regiões/clique ficam em coords de canvas -> mapear p/ desktop
        self._backend_nome = getattr(capturador, "nome_backend", cfg.captura.backend)
        self._transformar_clique = None
        self._client_rect_cache = None
        self._client_rect_ts = 0.0
        if self._backend_nome == "obs":
            self._configurar_mapeamento_obs(cfg)

    # -------------------------------------------------- mapeamento OBS->desktop
    def _configurar_mapeamento_obs(self, cfg) -> None:
        """Monta o callable que converte coords de canvas (OBS) em coords de desktop.

        Lê o canvas inteiro uma vez para saber suas dimensões (necessário quando
        box=None) e o título da janela do Tibia para achar o client rect ao vivo.
        """
        from bot.captura.mapeamento import mapear_canvas_para_desktop, obter_client_rect

        box = tuple(cfg.captura.mapeamento_obs.box) if cfg.captura.mapeamento_obs.box else None
        titulo = cfg.seguranca.titulo_janela_contains
        frame = self.cap.capturar(None)
        canvas_wh = None
        if frame is not None:
            h, w = frame.imagem.shape[:2]
            canvas_wh = (w, h)

        def _client_rect_vivo():
            agora = time.perf_counter()
            if self._client_rect_cache is not None and agora - self._client_rect_ts < 1.0:
                return self._client_rect_cache
            rect = obter_client_rect(titulo)
            if rect is not None:
                self._client_rect_cache = rect
                self._client_rect_ts = agora
            return rect or self._client_rect_cache

        def _transformar(x, y):
            rect = _client_rect_vivo()
            if rect is None:
                return (x, y)  # sem janela: melhor não deslocar do que chutar
            return mapear_canvas_para_desktop(x, y, rect, box, canvas_wh)

        self._transformar_clique = _transformar

    # ------------------------------------------------------------------ loop
    def run(self) -> None:
        self.ctrl.definir(EstadoExecucao.RODANDO)
        self.bus.publicar(ev.LinhaRaciocinio(time.perf_counter(), 0, "Bot iniciado", "info"))

        while self.ctrl.atual() != EstadoExecucao.PARADO:
            estado = self.ctrl.atual()

            if estado == EstadoExecucao.PANICO:
                self.bus.publicar(
                    ev.LinhaRaciocinio(time.perf_counter(), self.ctx.tick, "PÂNICO acionado — parando", "alerta")
                )
                self.ctrl.definir(EstadoExecucao.PARADO)
                break

            if estado == EstadoExecucao.PAUSADO:
                self._publicar_estado()
                self.ctrl.aguardar_se_pausado()
                continue

            t0 = time.perf_counter()
            self.ctx.ts = t0

            # Foco gateia só o INPUT, não a leitura: a captura via OBS funciona sem foco,
            # então seguimos lendo/publicando as barras; o SendInput (que só chega na janela
            # em foco) é suspenso quando o Tibia não está à frente. Sem auto-pause — assim o
            # painel mostra HP/Mana/criaturas ao vivo e o Pausar/Retomar manual não é revertido.
            self.ctx.janela_focada = self.seg.janela_focada()
            if self.ctx.janela_focada != self._ultimo_foco:
                self._ultimo_foco = self.ctx.janela_focada
                msg = (
                    "Janela do Tibia em foco — input ativo"
                    if self.ctx.janela_focada
                    else "Janela do Tibia sem foco — leitura ativa, input suspenso (foque o Tibia p/ agir)"
                )
                self.bus.publicar(ev.LinhaRaciocinio(t0, self.ctx.tick, msg, "info"))

            frame = self.cap.capturar(self._regiao_combinada)
            if frame is None:
                time.sleep(self._periodo)
                continue
            self.ctx.frame_atual = frame

            cfg = self.ctx.config
            reg_hp_img = _absoluto_para_imagem(self._reg_hp, frame.regiao)
            reg_mana_img = _absoluto_para_imagem(self._reg_mana, frame.regiao)
            self.ctx.hp = ler_percentual_barra(frame.imagem, reg_hp_img, cfg.visao.hp.v_min, cfg.visao.hp.s_min)
            self.ctx.mana = ler_percentual_barra(
                frame.imagem, reg_mana_img, cfg.visao.mana.v_min, cfg.visao.mana.s_min
            )

            self._verificar_frames_pretos(t0)

            self.ctx.criaturas = self._detectar_battle_list(cfg)
            self._rastrear_mortes(self.ctx.criaturas, t0)

            dec = self.motor.decidir(self.ctx, t0)
            executou = False
            if not self.ctx.janela_focada:
                pass  # sem foco: decide e exibe, mas não envia input (SendInput exige foco)
            elif dec.acao == TipoAcao.PRESSIONAR_TECLA and dec.tecla:
                self.entrada.pressionar_tecla(dec.tecla)
                executou = True
            elif dec.acao == TipoAcao.CLICAR and dec.ponto:
                self.entrada.clicar(*dec.ponto)
                executou = True
                if dec.dados.get("recurso") == "alvo":
                    self.bus.publicar(ev.LinhaRaciocinio(
                        t0, self.ctx.tick,
                        f"[alvo] clique em screen={dec.ponto}  battle_list={self._reg_battle}",
                        "info",
                    ))
            if executou:
                self.motor.confirmar_acao(dec, t0)
                self.ctx.estatisticas.registrar_acao(dec)
                if dec.dados.get("recurso") == "alvo":
                    # marca o engajamento: o Alvo não troca de bicho até morte/timeout
                    self.ctx.estado_comportamentos["alvo_engajado_ts"] = t0

            self._publicar_decisao(dec)
            self._publicar_deteccao()
            self._talvez_publicar_quadro(reg_hp_img, reg_mana_img, dec)

            dt = time.perf_counter() - t0
            self.ctx.estatisticas.atualizar_fps(1.0 / dt if dt > 0 else 0.0)
            self.ctx.fps = self.ctx.estatisticas.fps_medio
            self._publicar_estado()
            self._talvez_publicar_stats(t0)

            self.ctx.tick += 1
            if self._max_ticks is not None and self.ctx.tick >= self._max_ticks:
                self.ctrl.definir(EstadoExecucao.PARADO)
                break

            espera = self._periodo - (time.perf_counter() - t0)
            if espera > 0:
                time.sleep(espera)

        self._publicar_estado()
        try:
            self.cap.parar()
        except Exception:
            pass

    # -------------------------------------------------------- battle list
    def _detectar_battle_list(self, cfg) -> DeteccaoCriaturas | None:
        """Captura a região da battle list (se calibrada), detecta criaturas e
        converte o centro da 1ª entrada para coords absolutas (ponto de clique).
        """
        if not self._battle_ativo or self._reg_battle is None:
            return None
        frame_bl = self.cap.capturar(self._reg_battle)
        if frame_bl is None:
            return None
        reg_img = _absoluto_para_imagem(self._reg_battle, frame_bl.regiao)
        det = detectar_criaturas(
            frame_bl.imagem, reg_img, s_min=cfg.alvo.s_min, v_min=cfg.alvo.v_min
        )
        if det.centro_primeira is not None:
            left, top, _, _ = self._reg_battle
            cx, cy = det.centro_primeira
            px, py = left + cx, top + cy
            if self._transformar_clique is not None:
                px, py = self._transformar_clique(px, py)
            det.ponto_clique = (px, py)
        return det

    def _rastrear_mortes(self, det: DeteccaoCriaturas | None, ts: float) -> None:
        """Detecta morte (queda na contagem de criaturas) e carimba o ts no contexto.

        Roda em TODO tick (o motor faz curto-circuito, então o comportamento de saque
        não veria a queda por conta própria). Só considera leituras confiáveis para não
        carimbar uma morte falsa por leitura suja.
        """
        if det is None or det.confianca < self._saque_conf_min:
            return
        n = det.n_criaturas
        if self._ultimo_n_criaturas is not None and n < self._ultimo_n_criaturas:
            self.ctx.estado_comportamentos["saque_morte_ts"] = ts
        self._ultimo_n_criaturas = n

    def _verificar_frames_pretos(self, ts: float) -> None:
        """Detecta se o backend está retornando frames sem conteúdo útil.

        Se HP e mana ficarem com confiança zero por ~2 s consecutivos (30 ticks
        a 15 FPS), é sinal de que o backend não está capturando o Tibia — comum
        com WGC + DX11 Blt-model. Tenta trocar para mss automaticamente.
        """
        hp, mana = self.ctx.hp, self.ctx.mana
        sem_dados = (hp is None or hp.confianca < 0.05) and (mana is None or mana.confianca < 0.05)
        if sem_dados:
            self._ticks_sem_confianca += 1
        else:
            self._ticks_sem_confianca = 0
            return

        if self._ticks_sem_confianca != 30 or self._fallback_mss_feito:
            return

        # Com OBS, frame preto = Virtual Camera parada ou cena sem o Tibia. Trocar
        # para mss não ajuda (mss vem preto no Tibia oficial) — só avisa.
        if self._backend_nome == "obs":
            self._fallback_mss_feito = True  # avisa uma vez só
            self.bus.publicar(
                ev.LinhaRaciocinio(
                    ts,
                    self.ctx.tick,
                    "AVISO: 30 ticks sem dados com backend OBS. Confira se a Virtual "
                    "Camera está iniciada no OBS e se a cena mostra o Tibia.",
                    "alerta",
                )
            )
            return

        backend_atual = getattr(self.cap, "nome_backend", "?")
        self.bus.publicar(
            ev.LinhaRaciocinio(
                ts,
                self.ctx.tick,
                f"AVISO: {self._ticks_sem_confianca} ticks sem dados "
                f"(backend '{backend_atual}' não está capturando o Tibia). "
                "Trocando para mss (GDI/DWM — funciona para DX11 windowed)...",
                "alerta",
            )
        )
        try:
            from bot.captura.mss_fallback import CapturadorMSS

            novo = CapturadorMSS(monitor=self.ctx.config.captura.monitor)
            novo.iniciar()
            self.cap.parar()
            self.cap = novo
            self._fallback_mss_feito = True
            self.bus.publicar(
                ev.LinhaRaciocinio(ts, self.ctx.tick, "Backend trocado para mss — certifique-se de que o Tibia está visível.", "info")
            )
        except Exception as err:
            self._fallback_mss_feito = True  # não tenta de novo
            self.bus.publicar(
                ev.LinhaRaciocinio(ts, self.ctx.tick, f"Falha ao trocar para mss: {err} — altere 'backend: mss' no config.yaml", "alerta")
            )

    # ----------------------------------------------------------- telemetria
    def _publicar_estado(self) -> None:
        hp, mana = self.ctx.hp, self.ctx.mana
        self.bus.publicar(
            ev.SnapshotEstado(
                ts=self.ctx.ts or time.perf_counter(),
                tick=self.ctx.tick,
                hp_pct=round(hp.percentual, 1) if hp else None,
                mana_pct=round(mana.percentual, 1) if mana else None,
                hp_confianca=round(hp.confianca, 2) if hp else None,
                fps=round(self.ctx.fps, 1),
                estado_execucao=self.ctrl.atual().name,
                janela_focada=self.ctx.janela_focada,
                backend_captura=getattr(self.cap, "nome_backend", "?"),
            )
        )

    def _publicar_decisao(self, dec: Decisao) -> None:
        self.bus.publicar(
            ev.EventoDecisao(
                ts=self.ctx.ts,
                tick=self.ctx.tick,
                comportamento=dec.comportamento,
                acao=dec.acao.name,
                tecla=dec.tecla,
                motivo=dec.motivo,
                dados=dec.dados,
            )
        )
        # log de raciocínio com dedupe: só publica quando o motivo muda
        if dec.motivo != self._ultimo_motivo:
            self._ultimo_motivo = dec.motivo
            acoes = (TipoAcao.PRESSIONAR_TECLA, TipoAcao.CLICAR)
            nivel = "acao" if dec.acao in acoes else "info"
            self.bus.publicar(ev.LinhaRaciocinio(self.ctx.ts, self.ctx.tick, dec.motivo, nivel))

    def _publicar_deteccao(self) -> None:
        self.bus.publicar(
            ev.EventoDeteccao(
                ts=self.ctx.ts,
                tick=self.ctx.tick,
                hp=_leitura_dict(self.ctx.hp),
                mana=_leitura_dict(self.ctx.mana),
                criaturas=_criaturas_dict(self.ctx.criaturas),
            )
        )

    def _talvez_publicar_quadro(self, reg_hp_img: Regiao, reg_mana_img: Regiao, dec: Decisao) -> None:
        agora = time.perf_counter()
        if agora - self._ultimo_quadro_ts < self._periodo_quadro:
            return
        self._ultimo_quadro_ts = agora
        if self.ctx.frame_atual is None:
            return
        leituras = []
        if self.ctx.hp:
            leituras.append(("HP", reg_hp_img, self.ctx.hp))
        if self.ctx.mana:
            leituras.append(("MP", reg_mana_img, self.ctx.mana))
        anotado = desenhar_overlay(self.ctx.frame_atual.imagem, leituras, dec.motivo)
        anotado = _ampliar_se_pequeno(anotado)
        ok, buffer = cv2.imencode(".jpg", anotado, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ok:
            return
        b64 = base64.b64encode(buffer.tobytes()).decode("ascii")
        self.bus.publicar(ev.EventoQuadro(agora, self.ctx.tick, b64))

    def _talvez_publicar_stats(self, agora: float) -> None:
        if agora - self._ultimo_stats_ts < 1.0:
            return
        self._ultimo_stats_ts = agora
        e = self.ctx.estatisticas
        self.bus.publicar(
            ev.EventoStats(
                agora,
                round(e.uptime_s, 1),
                e.curas,
                e.pocoes_mana,
                round(e.fps_medio, 1),
                ataques=e.ataques,
                refeicoes=e.refeicoes,
                saques=e.saques,
            )
        )
