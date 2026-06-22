"""Calibração: marque as barras de HP e Mana e salve as regiões em config.yaml.

Uso:  python calibrar.py
"""

from __future__ import annotations

import pathlib
import sys

import cv2

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from bot.captura.fabrica import criar_capturador  # noqa: E402
from bot.configuracao import carregar_config, salvar_config  # noqa: E402
from bot.ferramentas.seletor_regiao import selecionar_regiao  # noqa: E402
from bot.visao.barra_recursos import ler_percentual_barra  # noqa: E402
from bot.visao.lista_batalha import detectar_criaturas  # noqa: E402


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
        print("\n*** A CAPTURA VEIO PRETA — o bot não está enxergando o jogo. ***")
        print("Causa nº1: Tibia em TELA CHEIA EXCLUSIVA bloqueia a captura de tela.")
        print("Solução:")
        print("  1. No Tibia: Options -> Graphics -> DESLIGUE 'Full screen mode'")
        print("     (use JANELA, de preferência 'sem bordas'/borderless).")
        print("  2. Posicione/maximize a janela onde ela vai ficar.")
        print("  3. Rode de novo: python calibrar.py")
        print("Se mesmo em janela vier preto: confira se o Tibia está no monitor PRIMÁRIO")
        print("(captura.monitor=0) e veja o PNG salvo acima.")
        return False
    return True


def main() -> int:
    print("=== Calibração do Bot Tibia ===")
    print("1) Abra o Tibia e deixe as barras de HP e Mana visíveis.")
    print("2) Uma captura da tela vai abrir; arraste um retângulo sobre cada barra.\n")

    cfg = carregar_config()
    cap = criar_capturador(cfg.captura.backend, cfg.captura.monitor, lambda m: print("[cap]", m))
    frame = cap.capturar(None)  # tela cheia
    cap.parar()
    if frame is None:
        print("Falha ao capturar a tela.")
        return 1

    img = frame.imagem
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
