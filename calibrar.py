"""Calibração: marque as barras de HP e Mana e salve as regiões em config.yaml.

Uso:  python calibrar.py
"""

from __future__ import annotations

import pathlib
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from bot.configuracao import carregar_config, salvar_config  # noqa: E402
from bot.ferramentas.seletor_regiao import selecionar_regiao  # noqa: E402
from bot.visao.barra_recursos import ler_percentual_barra  # noqa: E402
from bot.visao.lista_batalha import detectar_criaturas  # noqa: E402


def _focar_tibia(titulo_contains: str) -> bool:
    """Tenta trazer a janela do Tibia para a frente (best-effort, via pygetwindow)."""
    try:
        import pygetwindow as gw

        alvos = [w for w in gw.getAllWindows() if titulo_contains.lower() in (w.title or "").lower()]
        for w in alvos:
            try:
                if getattr(w, "isMinimized", False):
                    w.restore()
                w.activate()
                return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _aguardar_jogo_na_frente(titulo_contains: str, segundos: int = 4) -> None:
    """Foca o Tibia e dá uma contagem para a janela aparecer antes de capturar."""
    print("\n>>> Deixe o TIBIA em JANELA / SEM BORDAS (NÃO tela cheia exclusiva, NÃO minimizado).")
    if _focar_tibia(titulo_contains):
        print(">>> Tibia trazido para a frente.")
    else:
        print(">>> Não consegui focar o Tibia — CLIQUE na janela dele AGORA.")
    print(">>> Capturando em:", end=" ", flush=True)
    for i in range(segundos, 0, -1):
        print(f"{i}...", end=" ", flush=True)
        time.sleep(1)
    print("já!")


def _salvar_e_diagnosticar(img) -> bool:
    """Salva o print capturado e detecta captura preta (tela cheia exclusiva).

    Retorna False (e explica como resolver) se a captura veio essencialmente preta.
    """
    saida = pathlib.Path(__file__).parent / "dados" / "capturas"
    saida.mkdir(parents=True, exist_ok=True)
    caminho = saida / "calibracao_screenshot.png"
    cv2.imwrite(str(caminho), img)

    altura, largura = img.shape[:2]
    brilho_max = float(img.max())
    print(f"\n[diag] captura {largura}x{altura}  | brilho max={brilho_max:.0f}  média={float(img.mean()):.1f}")
    print(f"[diag] print salvo em: {caminho}  (abra para ver o que o bot capturou)")

    if brilho_max < 12:  # tudo preto
        print("\n*** A CAPTURA VEIO PRETA — o jogo não estava VISÍVEL na tela. ***")
        print("O bot fotografa o monitor; se o Tibia não está pintado nele, vem preto. Cheque:")
        print("  1. O Tibia NÃO pode estar minimizado nem atrás do terminal — deixe-o VISÍVEL.")
        print("  2. Use JANELA / SEM BORDAS (Options -> Graphics -> 'Full screen mode' OFF).")
        print("     Tela cheia EXCLUSIVA fica preta para qualquer captura (até WGC/DXGI).")
        print("  3. Tibia no monitor PRIMÁRIO (captura.monitor=0).")
        print("  4. Rode de novo: python calibrar.py — e na contagem, clique no Tibia.")
        print("Abra o PNG salvo acima para ver exatamente o que foi capturado.")
        return False
    return True


def _capturar_screenshot(monitor_idx: int = 0) -> np.ndarray | None:
    """Captura a tela inteira tentando mss (GDI/DWM) → PIL ImageGrab → WGC.

    Para janela DX11 visível, mss lê corretamente via DWM (GDI BitBlt).
    PIL ImageGrab é o segundo fallback (Pillow precisa estar instalado).
    WGC entra por último — em alguns setups DX11 Blt-model o WGC lê preto.
    """
    # 1. mss (GDI via DWM — funciona para windowed DX11 visível)
    try:
        import mss

        with mss.mss() as sct:
            mon = sct.monitors[monitor_idx + 1]  # 1-based; +1 converte 0-based
            shot = sct.grab(mon)
            arr = np.ascontiguousarray(np.asarray(shot)[:, :, :3])
        brilho = float(arr.max())
        print(f"[cap] mss: {arr.shape[1]}x{arr.shape[0]}  brilho max={brilho:.0f}")
        if brilho > 12:
            return arr
        print("[cap] mss retornou preto — tentando PIL…")
    except Exception as e:
        print(f"[cap] mss falhou: {e}")

    # 2. PIL ImageGrab (GDI alternativo)
    try:
        from PIL import ImageGrab

        pil = ImageGrab.grab(all_screens=False)
        arr = cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)
        brilho = float(arr.max())
        print(f"[cap] PIL: {arr.shape[1]}x{arr.shape[0]}  brilho max={brilho:.0f}")
        if brilho > 12:
            return arr
        print("[cap] PIL também retornou preto — tentando WGC…")
    except Exception as e:
        print(f"[cap] PIL falhou: {e}")

    # 3. WGC (último recurso)
    try:
        from bot.captura.wgc import CapturadorWGC

        cap = CapturadorWGC(monitor=monitor_idx)
        cap.iniciar()
        frame = cap.capturar(None)
        cap.parar()
        if frame is not None:
            arr = frame.imagem
            brilho = float(arr.max())
            print(f"[cap] WGC: {arr.shape[1]}x{arr.shape[0]}  brilho max={brilho:.0f}")
            if brilho > 12:
                return arr
            print("[cap] WGC também retornou preto.")
    except Exception as e:
        print(f"[cap] WGC falhou: {e}")

    return None


def main() -> int:
    print("=== Calibração do Bot Tibia ===")
    print("1) Abra o Tibia em MODO JANELA (Full Screen OFF) e deixe as barras visíveis.")
    print("2) Uma captura da tela vai abrir; arraste um retângulo sobre cada barra.\n")

    cfg = carregar_config()

    # o terminal está na frente agora; traz o Tibia pra frente e dá tempo de aparecer
    _aguardar_jogo_na_frente(cfg.seguranca.titulo_janela_contains)

    img = _capturar_screenshot(cfg.captura.monitor)
    if img is None:
        print("\n*** Todos os métodos retornaram preto. ***")
        print("Certifique-se de que o Tibia está em MODO JANELA e visível na tela.")
        return 1

    if not _salvar_e_diagnosticar(img):
        return 1

    reg_hp = selecionar_regiao(img, "Marque a BARRA DE VIDA (HP)")
    if reg_hp is None:
        print("Cancelado.")
        return 1
    reg_mana = selecionar_regiao(img, "Marque a BARRA DE MANA")
    if reg_mana is None:
        print("Cancelado.")
        return 1

    leitura_hp = ler_percentual_barra(img, reg_hp, cfg.visao.hp.v_min, cfg.visao.hp.s_min)
    leitura_mana = ler_percentual_barra(img, reg_mana, cfg.visao.mana.v_min, cfg.visao.mana.s_min)
    print(f"\nHP lido:   {leitura_hp.percentual:.0f}%  (confiança {leitura_hp.confianca:.2f})  região {reg_hp}")
    print(f"Mana lida: {leitura_mana.percentual:.0f}%  (confiança {leitura_mana.confianca:.2f})  região {reg_mana}")

    cfg.regioes.hp = reg_hp
    cfg.regioes.mana = reg_mana

    print("\n3) (Opcional) Marque a BATTLE LIST para habilitar targeting — ESC pula.")
    reg_battle = selecionar_regiao(img, "Marque a BATTLE LIST (ESC para pular)")
    if reg_battle is not None:
        det = detectar_criaturas(img, reg_battle, cfg.alvo.s_min, cfg.alvo.v_min)
        cfg.regioes.battle_list = reg_battle
        print(
            f"Battle list: {det.n_criaturas} criatura(s), alvo_atual={det.alvo_atual} "
            f"(confiança {det.confianca:.2f})  região {reg_battle}"
        )
    else:
        print("Battle list não marcada — targeting fica desligado.")

    salvar_config(cfg)

    print("\nCalibração salva em config/config.yaml.")
    print("Confira os valores acima — se baterem com a tela, rode:  python executar.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
