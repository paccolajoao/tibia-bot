"""Input de teclado e mouse via um Arduino HID dedicado (board ATmega32u4 — Leonardo/
Micro/Pro Micro — rodando `arduino/entrada_hid/entrada_hid.ino`).

NÃO é a BlackBoard: ela usa ATmega328P + um conversor USB-serial fixo (FT232RL ou
Silicon Labs), sem USB nativo — não existe firmware que a faça virar um teclado/mouse
HID. O board aqui precisa ter USB nativo (ATmega32u4/RP2040/SAMD).

Protocolo (ASCII, uma linha por comando, terminada em \n; resposta "OK"/"ERR ..."):
    K <TECLA>                pressiona e solta uma tecla
    M <hx> <hy>               move e clica (botão esquerdo) em coords absolutas escaladas
    MR <hx> <hy>              move e clica (botão direito)
    D <hx1> <hy1> <hx2> <hy2>  arrasta (mouse down -> move -> mouse up)
    MV <hx> <hy>              só move (sem clicar) — usado pelo diagnóstico da aba Arduino
    P                          ping (sem tocar em teclado/mouse) -> "PONG"; mede latência

As coordenadas de pixel são escaladas para o range 0-32767 do HID absoluto ANTES de
enviar (o firmware fica burro — sem estado de resolução para manter sincronizado). O
mouse absoluto via HID só alcança o monitor PRIMÁRIO do Windows (limitação da própria
pilha de driver HID); ver `ArduinoConfig.largura_tela`/`altura_tela`.

Cada ação é cercada pelo mesmo jitter humano pré/pós usado pelo backend SendInput
(`atraso_humano`), para os dois backends terem o mesmo comportamento de timing.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from bot.entrada.atrasos import atraso_humano

Logger = Callable[[str], None]


class EntradaArduinoErro(RuntimeError):
    """Falha de comunicação com o board (sem resposta, ACK de erro, etc.)."""


def _resolucao_primaria() -> tuple[int, int]:
    """Resolução do monitor PRIMÁRIO do Windows (é o único que o AbsoluteMouse alcança)."""
    import ctypes

    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)  # SM_CXSCREEN, SM_CYSCREEN


class EntradaArduino:
    def __init__(
        self,
        porta: str,
        baud_rate: int = 115200,
        timeout_s: float = 1.0,
        largura_tela: int = 0,
        altura_tela: int = 0,
        atraso_pre_ms: tuple[int, int] = (40, 90),
        atraso_pos_ms: tuple[int, int] = (30, 70),
        log: Logger | None = None,
        serial_obj=None,
    ):
        self._log = log or (lambda _msg: None)
        self._pre = atraso_pre_ms
        self._pos = atraso_pos_ms

        if serial_obj is not None:
            self._ser = serial_obj  # injeção p/ testes (fake serial)
        else:
            import serial

            self._ser = serial.Serial(porta, baud_rate, timeout=timeout_s)

        largura, altura = largura_tela, altura_tela
        if largura <= 0 or altura <= 0:
            largura, altura = _resolucao_primaria()
        self._largura = max(1, largura)
        self._altura = max(1, altura)

        self._aguardar_pronto()

    # ------------------------------------------------------------ protocolo
    def _aguardar_pronto(self) -> None:
        linha = self._ler_linha()
        if "READY" not in linha:
            raise EntradaArduinoErro(
                f"Arduino não respondeu READY ao conectar (recebido: {linha!r}). "
                "Confira se entrada_hid.ino foi gravado no board e se é o board "
                "certo (não a BlackBoard)."
            )
        self._log("Entrada Arduino: board pronto (READY recebido)")

    def _ler_linha(self) -> str:
        bruto = self._ser.readline()
        return bruto.decode("ascii", errors="replace").strip()

    def _enviar(self, comando: str) -> float:
        """Envia um comando e aguarda o ACK. Retorna a latência (ms) do round-trip —
        usado tanto internamente quanto pelo diagnóstico da aba Arduino do portal.
        """
        inicio = time.perf_counter()
        self._ser.write((comando + "\n").encode("ascii"))
        resposta = self._ler_linha()
        latencia_ms = (time.perf_counter() - inicio) * 1000.0
        if not resposta:
            raise EntradaArduinoErro(f"sem resposta do Arduino (comando: {comando!r})")
        if resposta.startswith("ERR"):
            raise EntradaArduinoErro(f"Arduino recusou o comando {comando!r}: {resposta}")
        return latencia_ms

    def _escalar(self, x: int, y: int) -> tuple[int, int]:
        hx = round(max(0, min(x, self._largura - 1)) * 32767 / max(1, self._largura - 1))
        hy = round(max(0, min(y, self._altura - 1)) * 32767 / max(1, self._altura - 1))
        return hx, hy

    # -------------------------------------------------------------- EntradaBase
    def pressionar_tecla(self, tecla: str) -> None:
        atraso_humano(self._pre)
        self._enviar(f"K {tecla.upper()}")
        atraso_humano(self._pos)

    def clicar(self, x: int, y: int) -> None:
        atraso_humano(self._pre)
        hx, hy = self._escalar(x, y)
        self._enviar(f"M {hx} {hy}")
        atraso_humano(self._pos)

    def clicar_direito(self, x: int, y: int) -> None:
        atraso_humano(self._pre)
        hx, hy = self._escalar(x, y)
        self._enviar(f"MR {hx} {hy}")
        atraso_humano(self._pos)

    def arrastar(self, x1: int, y1: int, x2: int, y2: int) -> None:
        atraso_humano(self._pre)
        hx1, hy1 = self._escalar(x1, y1)
        hx2, hy2 = self._escalar(x2, y2)
        self._enviar(f"D {hx1} {hy1} {hx2} {hy2}")
        atraso_humano(self._pos)

    # ---------------------------------------------------------- diagnóstico
    def ping(self) -> float:
        """Round-trip sem tocar em teclado/mouse. Retorna a latência em ms."""
        return self._enviar("P")

    def mover(self, x: int, y: int) -> float:
        """Só move o cursor (sem clicar) — seguro p/ o teste da aba Arduino."""
        hx, hy = self._escalar(x, y)
        return self._enviar(f"MV {hx} {hy}")

    def fechar(self) -> None:
        try:
            self._ser.close()
        except Exception:
            pass


def executar_diagnostico(
    porta: str,
    baud_rate: int = 115200,
    timeout_s: float = 1.0,
    largura_tela: int = 0,
    altura_tela: int = 0,
    testar_clique: bool = False,
    ponto_clique: tuple[int, int] | None = None,
    serial_obj=None,  # injeção p/ testes (fake serial) — ver EntradaArduino
) -> dict:
    """Roda uma bateria de testes contra o board e devolve um relatório (dict, JSON-safe).

    Abre uma conexão PRÓPRIA (fecha ao final) — independente da que o bot usa quando
    está rodando com `entrada.backend: arduino`. Se o bot já estiver rodando com essa
    porta, a etapa "conectar" falha (porta ocupada) — é o comportamento esperado, não
    um bug: só um processo pode abrir a mesma porta serial por vez.

    Etapas, em ordem — cada uma roda independente das outras (uma falha não aborta o
    resto, exceto se a conexão em si não abrir):
      conectar        -> abre a serial e aguarda o "READY" do firmware
      ping            -> round-trip "P"/"PONG", sem tocar em teclado/mouse
      teclado         -> aperta CAPS LOCK (reversível, não digita texto nem clica em nada)
      mouse_movimento -> move o cursor pro centro da tela (sem clicar)
      mouse_clique    -> (só se testar_clique=True) clica em `ponto_clique` de verdade
    """
    etapas: list[dict] = []
    inicio = time.perf_counter()
    try:
        ent = EntradaArduino(
            porta, baud_rate, timeout_s, largura_tela, altura_tela,
            atraso_pre_ms=(0, 0), atraso_pos_ms=(0, 0), serial_obj=serial_obj,
        )
    except Exception as e:
        etapas.append({
            "nome": "conectar", "ok": False, "latencia_ms": None,
            "detalhe": f"{e} — confira a porta, se o board está plugado e se "
                       "entrada_hid.ino foi gravado nele (não serve na BlackBoard). Se o "
                       "bot já estiver rodando com backend arduino, pare-o antes de testar "
                       "(só um processo pode abrir a porta por vez).",
        })
        return {"sucesso": False, "etapas": etapas, "largura_usada": 0, "altura_usada": 0}

    etapas.append({
        "nome": "conectar", "ok": True,
        "latencia_ms": round((time.perf_counter() - inicio) * 1000.0, 1), "detalhe": None,
    })

    def _rodar(nome: str, fn) -> None:
        try:
            ms = fn()
            etapas.append({"nome": nome, "ok": True, "latencia_ms": round(ms, 1), "detalhe": None})
        except Exception as e:
            etapas.append({"nome": nome, "ok": False, "latencia_ms": None, "detalhe": str(e)})

    _rodar("ping", ent.ping)
    _rodar("teclado", lambda: ent._enviar("K CAPSLOCK"))
    _rodar("mouse_movimento", lambda: ent.mover(ent._largura // 2, ent._altura // 2))

    if testar_clique:
        if ponto_clique is None:
            etapas.append({
                "nome": "mouse_clique", "ok": False, "latencia_ms": None,
                "detalhe": "coordenadas do clique não informadas",
            })
        else:
            _rodar("mouse_clique", lambda: ent._enviar(
                "M {} {}".format(*ent._escalar(*ponto_clique))
            ))

    largura_usada, altura_usada = ent._largura, ent._altura
    ent.fechar()

    return {
        "sucesso": all(e["ok"] for e in etapas),
        "etapas": etapas,
        "largura_usada": largura_usada,
        "altura_usada": altura_usada,
    }
