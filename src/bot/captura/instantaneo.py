"""Captura de **um único frame** para a calibração no navegador.

Reaproveita a fábrica de capturadores (mesmo auto-fallback DXGI→WGC→mss e os
backends obs/tibia_arquivo) em vez de duplicar a cadeia ad-hoc do `calibrar.py`.
Abre o capturador, pega um frame, fecha. Roda fora da thread do bot — não toca o
`Contexto`.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from bot.captura.fabrica import criar_capturador


@dataclass
class FrameCalibracao:
    """Frame para calibração + o offset absoluto que ele representa.

    `origem_x/origem_y` é o canto superior-esquerdo (em coords que o bot usa) do
    frame: desktop absoluto para backends de tela; (0,0) para OBS (coords de canvas).
    Somar esse offset à posição do retângulo desenhado dá a região a salvar.
    """

    imagem: np.ndarray  # BGR HxWx3
    largura: int
    altura: int
    origem_x: int
    origem_y: int
    backend: str


def _empacotar(frame, backend: str, emitir) -> FrameCalibracao | None:
    """Valida um frame cru e empacota num FrameCalibracao (None se preto/vazio)."""
    if frame is None or frame.imagem is None or frame.imagem.size == 0:
        return None

    img = frame.imagem
    if float(img.mean()) < 15:  # mesmo limiar do calibrar.py: conteúdo de jogo vs. preto
        emitir("Frame de calibração veio quase preto (WDA/cena OBS?).", "alerta")
        return None

    h, w = img.shape[:2]
    origem_x, origem_y = (frame.regiao[0], frame.regiao[1]) if frame.regiao else (0, 0)
    return FrameCalibracao(
        imagem=img, largura=w, altura=h, origem_x=origem_x, origem_y=origem_y, backend=backend
    )


def frame_de_capturador(cap, log=None) -> FrameCalibracao | None:
    """Pega um frame de um capturador JÁ EM EXECUÇÃO (sem abrir/fechar device).

    Usado quando o bot está rodando: abrir um 2º handle do mesmo device (sobretudo
    a OBS Virtual Camera, que o DirectShow não compartilha) faz o `read()` da thread
    do bot estourar e derrubar a captura. Reaproveitar o último frame evita o conflito.
    """
    emitir = log or (lambda *_a, **_k: None)
    frame = cap.capturar(None)
    return _empacotar(frame, getattr(cap, "nome_backend", "?"), emitir)


def capturar_frame_calibracao(cfg, log=None) -> FrameCalibracao | None:
    """Captura um frame conforme o backend configurado. Retorna None se vier preto/sem frame.

    Abre um capturador NOVO — use só quando o bot não está rodando. Com o bot ativo,
    prefira `frame_de_capturador(loop.cap)` para não abrir um 2º handle do device.
    """
    emitir = log or (lambda *_a, **_k: None)
    cap = criar_capturador(
        cfg.captura.backend,
        cfg.captura.monitor,
        emitir,
        tibia_screenshots=cfg.captura.tibia_screenshots,
        hotkey_screenshot=cfg.captura.hotkey_screenshot,
        fps_alvo=cfg.captura.fps_alvo,
        obs_device_index=cfg.captura.obs_device_index,
        obs_device_nome=cfg.captura.obs_device_nome,
        obs_largura=cfg.captura.obs_largura,
        obs_altura=cfg.captura.obs_altura,
    )
    try:
        frame = cap.capturar(None)
    finally:
        try:
            cap.parar()
        except Exception:
            pass

    return _empacotar(frame, cap.nome_backend, emitir)


def codificar_jpeg(imagem: np.ndarray, qualidade: int = 80) -> bytes:
    """Codifica um BGR ndarray em JPEG. Levanta se falhar."""
    ok, buf = cv2.imencode(".jpg", imagem, [int(cv2.IMWRITE_JPEG_QUALITY), qualidade])
    if not ok:
        raise RuntimeError("Falha ao codificar JPEG")
    return buf.tobytes()
