"""Capturador via OBS Virtual Camera — saída para clientes com WDA_EXCLUDEFROMCAPTURE.

O Tibia oficial (BattlEye) usa `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)`,
que faz o compositor do Windows apagar a janela de TODO caminho de captura externo
(mss/GDI, WGC, DXGI, PrintWindow, PrintScreen → tudo vem preto). O OBS, porém, é
*whitelisted* pelo BattlEye: a fonte Game/Window Capture dele enxerga o jogo normal.

A ideia: o OBS compõe o jogo no canvas e expõe esse canvas como uma webcam virtual
("OBS Virtual Camera"). Aqui lemos esse device com `cv2.VideoCapture` e tratamos o
frame do canvas como se fosse a "tela". As regiões calibradas ficam em coords de
CANVAS (não desktop) — o crop é feito em software, igual aos outros backends. Para
clicar no alvo, o loop converte canvas→desktop via `bot.captura.mapeamento`.

Pré-requisitos no OBS: cena com Game/Window Capture do Tibia, "Hide cursor" ligado,
e **Start Virtual Camera**. Recomenda-se o canvas 1:1 com a área cliente do Tibia.

Modelo PULL: uma thread leitora roda `read()` continuamente e guarda o ÚLTIMO frame
sob lock. `cv2.VideoCapture` bufferiza frames; sem a thread, `capturar()` devolveria
quadros atrasados. `CAP_PROP_BUFFERSIZE=1` reduz a latência ainda mais.
"""

from __future__ import annotations

import threading
import time

import cv2
import numpy as np

from bot.captura.base import Frame, Regiao


def descobrir_indice_por_nome(nome_contains: str = "OBS Virtual Camera") -> int | None:
    """Tenta achar o índice do device cujo nome contém `nome_contains`.

    Usa `pygrabber` (DirectShow) se instalado; senão devolve None e o chamador
    cai no índice configurado. OpenCV não expõe nomes de device nativamente.
    """
    try:
        from pygrabber.dshow_graph import FilterGraph

        nomes = FilterGraph().get_input_devices()
        alvo = nome_contains.lower()
        for i, nome in enumerate(nomes):
            if alvo in (nome or "").lower():
                return i
    except Exception:
        pass
    return None


class CapturadorOBS:
    nome_backend = "obs"

    def __init__(
        self,
        indice: int = 0,
        nome_device: str = "OBS Virtual Camera",
        largura: int = 1920,
        altura: int = 1080,
        timeout_primeiro_frame_s: float = 5.0,
    ):
        self._indice = indice
        self._nome_device = nome_device
        self._largura = largura
        self._altura = altura
        self._timeout = timeout_primeiro_frame_s
        self._lock = threading.Lock()
        self._ultimo: np.ndarray | None = None
        self._cap: cv2.VideoCapture | None = None
        self._rodando = False
        self._thread: threading.Thread | None = None

    def iniciar(self) -> None:
        # Preferir o device por nome (índices mudam conforme webcams plugadas)
        idx = descobrir_indice_por_nome(self._nome_device)
        if idx is None:
            idx = self._indice
        self._indice = idx

        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError(
                f"Não abri o device de vídeo índice {idx}. "
                "Abra o OBS e clique em 'Start Virtual Camera'."
            )
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # DirectShow abre em 640x480 por padrão — sem isto a calibração fica borrada.
        # Pedimos a resolução desejada; o device entrega o tamanho suportado mais próximo.
        if self._largura and self._altura:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._largura)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._altura)
        self._cap = cap
        self._rodando = True
        self._thread = threading.Thread(target=self._loop_leitura, name="OBSReader", daemon=True)
        self._thread.start()

        # espera o 1º frame: a calibração captura 1x e falharia se viesse None
        prazo = time.perf_counter() + self._timeout
        while time.perf_counter() < prazo:
            with self._lock:
                if self._ultimo is not None:
                    return
            time.sleep(0.03)
        self.parar()
        raise RuntimeError(
            "OBS Virtual Camera não entregou frame. Confira se a Virtual Camera "
            "está iniciada no OBS e se a cena tem uma fonte de captura do Tibia."
        )

    def _loop_leitura(self) -> None:
        while self._rodando and self._cap is not None:
            ok, frame = self._cap.read()
            if not ok or frame is None:
                time.sleep(0.005)
                continue
            with self._lock:
                self._ultimo = frame  # já é BGR HxWx3

    def capturar(self, regiao: Regiao | None = None) -> Frame | None:
        with self._lock:
            img = self._ultimo
        if img is None:
            return None
        if regiao is not None:
            left, top, right, bottom = regiao
            img = img[top:bottom, left:right]
        return Frame(np.ascontiguousarray(img), time.perf_counter(), regiao)

    def parar(self) -> None:
        self._rodando = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
