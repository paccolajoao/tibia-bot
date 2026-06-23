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


def capturar_frame_calibracao(cfg, log=None) -> FrameCalibracao | None:
    """Captura um frame conforme o backend configurado. Retorna None se vier preto/sem frame."""
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

    if frame is None or frame.imagem is None or frame.imagem.size == 0:
        return None

    img = frame.imagem
    if float(img.mean()) < 15:  # mesmo limiar do calibrar.py: conteúdo de jogo vs. preto
        emitir("Frame de calibração veio quase preto (WDA/cena OBS?).", "alerta")
        return None

    h, w = img.shape[:2]
    origem_x, origem_y = (frame.regiao[0], frame.regiao[1]) if frame.regiao else (0, 0)
    return FrameCalibracao(
        imagem=img, largura=w, altura=h, origem_x=origem_x, origem_y=origem_y, backend=cap.nome_backend
    )


def codificar_jpeg(imagem: np.ndarray, qualidade: int = 80) -> bytes:
    """Codifica um BGR ndarray em JPEG. Levanta se falhar."""
    ok, buf = cv2.imencode(".jpg", imagem, [int(cv2.IMWRITE_JPEG_QUALITY), qualidade])
    if not ok:
        raise RuntimeError("Falha ao codificar JPEG")
    return buf.tobytes()
