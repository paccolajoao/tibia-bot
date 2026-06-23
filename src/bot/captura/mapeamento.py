"""Mapeamento canvas (OBS) → coords absolutas do desktop.

Com o backend OBS, as regiões calibradas e o ponto de clique do targeting ficam em
coords do CANVAS do OBS (o frame da Virtual Camera), não do desktop. Para clicar de
fato na criatura, convertemos canvas→desktop com uma transformação afim:

    dx = client.left + (x - box.left) * client.largura / box.largura
    dy = client.top  + (y - box.top)  * client.altura  / box.altura

onde:
  - `box`    = retângulo (em coords de canvas) que a área do jogo ocupa no canvas
               (None = canvas inteiro, válido no setup recomendado 1:1).
  - `client` = retângulo cliente VIVO da janela do Tibia no desktop, lido em runtime
               (assim o mapeamento acompanha a janela se ela for movida).

No setup recomendado (canvas 1:1 com a janela), `box` cobre o canvas inteiro e as
escalas viram ~1, então o mapeamento é praticamente um offset puro.
"""

from __future__ import annotations

from bot.captura.base import Regiao


def obter_client_rect(titulo_contains: str = "Tibia") -> Regiao | None:
    """Retorna (left, top, right, bottom) da ÁREA CLIENTE da janela do Tibia no desktop.

    Usa win32 (GetClientRect + ClientToScreen). Devolve None se não achar a janela
    ou se o pywin32 não estiver disponível.
    """
    try:
        import win32gui
    except Exception:
        return None

    alvo = titulo_contains.lower()
    achados: list[int] = []

    def _cb(h, _):
        if win32gui.IsWindowVisible(h) and alvo in (win32gui.GetWindowText(h) or "").lower():
            achados.append(h)
        return True

    try:
        win32gui.EnumWindows(_cb, None)
        if not achados:
            return None
        hwnd = achados[0]
        # GetClientRect dá (0,0,w,h); ClientToScreen leva ao desktop
        _, _, cw, ch = win32gui.GetClientRect(hwnd)
        if cw <= 0 or ch <= 0:
            return None
        esq, topo = win32gui.ClientToScreen(hwnd, (0, 0))
        return (esq, topo, esq + cw, topo + ch)
    except Exception:
        return None


def mapear_canvas_para_desktop(
    x: int,
    y: int,
    client_rect: Regiao,
    box: Regiao | None,
    canvas_wh: tuple[int, int] | None = None,
) -> tuple[int, int]:
    """Converte um ponto (x, y) do canvas do OBS para coords absolutas do desktop.

    `box` em coords de canvas (None = usa `canvas_wh`, ou seja, o canvas inteiro).
    """
    if box is None:
        bl, bt = 0, 0
        bw = canvas_wh[0] if canvas_wh else 1
        bh = canvas_wh[1] if canvas_wh else 1
    else:
        bl, bt, br, bb = box
        bw = max(1, br - bl)
        bh = max(1, bb - bt)

    cl, ct, cr, cb = client_rect
    cw = cr - cl
    ch = cb - ct
    dx = cl + (x - bl) * cw / bw
    dy = ct + (y - bt) * ch / bh
    return (int(round(dx)), int(round(dy)))
