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

    media = float(img.mean())
    # Limiar de média: apenas taskbar ~4, jogo real (mesmo dungeon escuro) > 15
    if media < 15:
        print("\n*** CAPTURA INÚTIL — conteúdo do jogo não está visível (média muito baixa). ***")
        print("O Tibia provavelmente usa WDA_EXCLUDEFROMCAPTURE (proteção de tela).")
        print("Use 'backend: tibia_arquivo' no config.yaml + hotkey_screenshot configurada.")
        print("Abra o PNG salvo acima para confirmar.")
        return False
    return True


def _capturar_via_obs(indice: int, nome_device: str) -> np.ndarray | None:
    """Captura um frame do canvas via OBS Virtual Camera (whitelisted pelo BattlEye)."""
    try:
        from bot.captura.obs_virtualcam import CapturadorOBS

        cap = CapturadorOBS(indice=indice, nome_device=nome_device)
        cap.iniciar()
        frame = cap.capturar(None)
        cap.parar()
        if frame is None:
            print("[cap] OBS: nenhum frame recebido.")
            return None
        img = frame.imagem
        media = float(img.mean())
        print(f"[cap] OBS: {img.shape[1]}x{img.shape[0]}  média={media:.1f}  max={float(img.max()):.0f}")
        if media > 15:
            return img
        print("[cap] OBS: frame quase preto — a cena do OBS está mostrando o Tibia?")
    except Exception as e:
        print(f"[cap] OBS falhou: {e}")
        print("       Abra o OBS, monte a cena do Tibia e clique em 'Start Virtual Camera'.")
    return None


def _capturar_screenshot(
    monitor_idx: int = 0,
    hotkey_screenshot: str = "ctrl+p",
    pasta_screenshots: str = "",
    backend: str = "auto",
    obs_device_index: int = 0,
    obs_device_nome: str = "OBS Virtual Camera",
) -> np.ndarray | None:
    """Tenta capturar a tela por vários métodos em ordem crescente de complexidade.

    Com backend=obs, captura primeiro pela OBS Virtual Camera (única saída para o
    Tibia oficial com WDA_EXCLUDEFROMCAPTURE). mss/PIL/WGC funcionam quando o Tibia
    NÃO usa WDA; tibia_arquivo é o fallback por hotkey de screenshot.
    """
    def _util(arr: np.ndarray, nome: str) -> np.ndarray | None:
        """Retorna arr se a média indicar conteúdo real de jogo (> 15); loga e retorna None senão."""
        media = float(arr.mean())
        print(f"[cap] {nome}: {arr.shape[1]}x{arr.shape[0]}  média={media:.1f}  max={float(arr.max()):.0f}")
        if media > 15:
            return arr
        print(f"[cap] {nome}: média muito baixa — jogo bloqueado (WDA_EXCLUDEFROMCAPTURE?) — próximo método…")
        return None

    # 0. OBS Virtual Camera (preferido com backend=obs)
    if backend == "obs":
        resultado = _capturar_via_obs(obs_device_index, obs_device_nome)
        if resultado is not None:
            return resultado
        print("[cap] OBS não retornou imagem útil — tentando métodos diretos…")

    # 1. mss (GDI via DWM)
    try:
        import mss as _mss

        with _mss.MSS() as sct:
            mon = sct.monitors[monitor_idx + 1]
            shot = sct.grab(mon)
            arr = np.ascontiguousarray(np.asarray(shot)[:, :, :3])
        resultado = _util(arr, "mss")
        if resultado is not None:
            return resultado
    except Exception as e:
        print(f"[cap] mss falhou: {e}")

    # 2. PIL ImageGrab (GDI alternativo)
    try:
        from PIL import ImageGrab

        pil = ImageGrab.grab(all_screens=False)
        arr = cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)
        resultado = _util(arr, "PIL")
        if resultado is not None:
            return resultado
    except Exception as e:
        print(f"[cap] PIL falhou: {e}")

    # 3. WGC
    try:
        from bot.captura.wgc import CapturadorWGC

        cap = CapturadorWGC(monitor=monitor_idx)
        cap.iniciar()
        frame = cap.capturar(None)
        cap.parar()
        if frame is not None:
            resultado = _util(frame.imagem, "WGC")
            if resultado is not None:
                return resultado
    except Exception as e:
        print(f"[cap] WGC falhou: {e}")

    # 4. PrintWindow(PW_RENDERFULLCONTENT) — pede à janela que se renderize num DC próprio
    #    Captura o CLIENTE INTEIRO (HUD, barras, battle list) mesmo com WDA ativo em alguns setups
    resultado = _capturar_print_window()
    if resultado is not None:
        return resultado

    # 5. Screenshot interno do Tibia (WDA_EXCLUDEFROMCAPTURE ativo) — só captura viewport
    print("\n[cap] Todos os métodos diretos retornaram preto.")
    print("[cap] Tibia usa proteção WDA_EXCLUDEFROMCAPTURE — usando hotkey de screenshot interno.")
    return _capturar_via_tibia_arquivo(hotkey_screenshot, pasta_screenshots)


def _capturar_print_window() -> np.ndarray | None:
    """Captura a janela do Tibia via PrintWindow(PW_RENDERFULLCONTENT).

    Diferente de mss/WGC (leem do compositor DWM), PrintWindow envia WM_PRINT
    diretamente para a janela. Com PW_RENDERFULLCONTENT pode capturar conteúdo
    DX11 mesmo com WDA_EXCLUDEFROMCAPTURE ativo, e captura o cliente INTEIRO
    (HUD, barras de HP/mana, battle list — não só o viewport do jogo).
    """
    try:
        import win32gui
        import win32ui
        from ctypes import windll

        # Encontra a janela do Tibia pela palavra no título
        hwnd_encontrado: list[int] = []

        def _cb(h, _):
            titulo = win32gui.GetWindowText(h)
            if "tibia" in titulo.lower() and win32gui.IsWindowVisible(h):
                hwnd_encontrado.append(h)
            return True

        win32gui.EnumWindows(_cb, None)
        if not hwnd_encontrado:
            print("[cap] PrintWindow: janela do Tibia não encontrada.")
            return None

        hwnd = hwnd_encontrado[0]
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        w, h = right - left, bottom - top
        if w <= 0 or h <= 0:
            return None

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bmp)

        PW_RENDERFULLCONTENT = 0x00000002
        ok = windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)

        info = bmp.GetInfo()
        bits = bmp.GetBitmapBits(True)

        win32gui.DeleteObject(bmp.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        if not ok:
            print("[cap] PrintWindow retornou 0 (não suportado).")
            return None

        arr = np.frombuffer(bits, dtype=np.uint8).reshape(info["bmHeight"], info["bmWidth"], 4)
        img = np.ascontiguousarray(arr[:, :, :3])  # BGRA → BGR (descarta alfa)

        media = float(img.mean())
        print(f"[cap] PrintWindow: {w}x{h}  média={media:.1f}  max={float(img.max()):.0f}")
        if media > 15:
            return img
        print("[cap] PrintWindow: imagem preta — WDA bloqueia este caminho também.")
    except Exception as e:
        print(f"[cap] PrintWindow falhou: {e}")
    return None


def _capturar_via_tibia_arquivo(hotkey: str, pasta_str: str) -> np.ndarray | None:
    """Envia a hotkey de screenshot do Tibia e aguarda o arquivo aparecer."""
    from bot.captura.tibia_arquivo import _arquivo_mais_novo, _hotkey_send, detectar_pasta_screenshots
    import pathlib

    pasta = pathlib.Path(pasta_str) if pasta_str else detectar_pasta_screenshots()
    if pasta is None or not pasta.is_dir():
        print(
            "\n*** Pasta de screenshots do Tibia não encontrada. ***\n"
            "  1. Tire uma screenshot no Tibia (Options > Interface > Screenshot hotkey).\n"
            "  2. Veja em qual pasta o arquivo PNG apareceu.\n"
            "  3. Configure no config.yaml:\n"
            "       captura:\n"
            "         backend: tibia_arquivo\n"
            "         tibia_screenshots: C:\\caminho\\para\\a\\pasta\n"
            f"        hotkey_screenshot: {hotkey}\n"
        )
        return None

    print(f"[cap] Pasta de screenshots: {pasta}")
    print(f"[cap] Focando Tibia e enviando hotkey '{hotkey}' em 2 segundos…")
    time.sleep(2.0)

    t_antes = time.time() - 0.5
    _hotkey_send(hotkey)
    print("[cap] Hotkey enviada. Aguardando arquivo (até 5 s)…")

    prazo = time.perf_counter() + 5.0
    while time.perf_counter() < prazo:
        time.sleep(0.1)
        arquivo = _arquivo_mais_novo(pasta, t_antes)
        if arquivo is None:
            continue
        time.sleep(0.05)
        try:
            img = cv2.imread(str(arquivo))
        except Exception:
            continue
        if img is None:
            continue
        brilho = float(img.max())
        print(f"[cap] Tibia screenshot: {img.shape[1]}x{img.shape[0]}  brilho max={brilho:.0f}")
        if brilho > 12:
            return img

    print(
        "\n*** Screenshot do Tibia não chegou. ***\n"
        f"  • Confira se a hotkey '{hotkey}' está correta (Options > Interface > Screenshot).\n"
        "  • O Tibia precisa estar em foco e com um personagem no mapa.\n"
        f"  • Pasta monitorada: {pasta}\n"
    )
    return None


def _configurar_mapeamento_obs_na_calibracao(cfg, img: np.ndarray) -> None:
    """Define o mapeamento canvas->desktop e valida o client rect vivo do Tibia.

    No setup recomendado (canvas do OBS 1:1 com a área cliente do Tibia), box=None
    (canvas inteiro) já basta — o clique é só um offset para a posição da janela.
    """
    from bot.captura.mapeamento import obter_client_rect

    cfg.captura.mapeamento_obs.box = None  # canvas inteiro (setup 1:1)
    h, w = img.shape[:2]
    rect = obter_client_rect(cfg.seguranca.titulo_janela_contains)
    if rect is None:
        print(
            "\n[mapa] AVISO: não achei a janela do Tibia para ler a posição na tela.\n"
            "       O clique de targeting precisa disso. Deixe o Tibia em janela e visível.\n"
        )
        return
    cw, ch = rect[2] - rect[0], rect[3] - rect[1]
    print(f"\n[mapa] Canvas do OBS: {w}x{h}  |  janela cliente do Tibia: {cw}x{ch} em {rect[:2]}")
    if abs(cw - w) > 4 or abs(ch - h) > 4:
        print(
            "[mapa] OBS: o canvas NÃO bate 1:1 com a janela do Tibia (haverá escala).\n"
            "       Recomendado: deixe a fonte preenchendo o canvas no tamanho da janela\n"
            "       para o clique ficar exato. Mesmo assim o mapeamento por escala é aplicado."
        )
    else:
        print("[mapa] OBS: canvas 1:1 com a janela — clique de targeting será preciso.")


def main() -> int:
    print("=== Calibração do Bot Tibia ===")
    print("1) Abra o Tibia em MODO JANELA (Full Screen OFF) e deixe as barras visíveis.")
    print("2) Uma captura da tela vai abrir; arraste um retângulo sobre cada barra.\n")

    cfg = carregar_config()

    # o terminal está na frente agora; traz o Tibia pra frente e dá tempo de aparecer
    _aguardar_jogo_na_frente(cfg.seguranca.titulo_janela_contains)

    if cfg.captura.backend == "obs":
        print(">>> Backend OBS: confirme que a OBS Virtual Camera está INICIADA e a cena mostra o Tibia.")

    img = _capturar_screenshot(
        cfg.captura.monitor,
        hotkey_screenshot=cfg.captura.hotkey_screenshot,
        pasta_screenshots=cfg.captura.tibia_screenshots,
        backend=cfg.captura.backend,
        obs_device_index=cfg.captura.obs_device_index,
        obs_device_nome=cfg.captura.obs_device_nome,
    )
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

    if cfg.captura.backend == "obs":
        _configurar_mapeamento_obs_na_calibracao(cfg, img)

    salvar_config(cfg)

    print("\nCalibração salva em config/config.yaml.")
    print("Confira os valores acima — se baterem com a tela, rode:  python executar.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
