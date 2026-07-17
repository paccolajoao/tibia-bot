/*
 * entrada_hid.ino — firmware de referência do backend `entrada.backend: arduino`.
 *
 * Board: qualquer ATmega32u4 com USB nativo (Arduino Leonardo, Micro, Pro Micro...).
 * NÃO funciona na RoboCore BlackBoard V1.0 (ATmega328P + conversor USB-serial fixo,
 * sem USB nativo — não tem como virar teclado/mouse HID).
 *
 * Biblioteca necessária (Library Manager do Arduino IDE): "HID-Project" (NicoHood).
 *
 * Protocolo (ASCII, uma linha por comando, terminada em \n; ver
 * src/bot/entrada/teclado_arduino.py no bot):
 *   K <TECLA>                  pressiona e solta uma tecla (nome ou 1 caractere)
 *   M <hx> <hy>                move e clica esquerdo em (hx,hy), 0-32767 (HID absoluto)
 *   MR <hx> <hy>               move e clica direito em (hx,hy)
 *   D <hx1> <hy1> <hx2> <hy2>  arrasta: mouse down em (1), move até (2), mouse up
 *   MV <hx> <hy>               só move (sem clicar) — usado pelo teste da aba Arduino
 *   P                          ping (não toca em teclado/mouse) -> responde "PONG"
 * Resposta: "OK" ou "ERR <motivo>" (comando P responde "PONG" em vez de "OK"). Ao
 * ligar, imprime "READY" uma vez.
 *
 * As coordenadas já chegam escaladas para 0-32767 (o bot faz a escala, este firmware
 * fica burro — sem estado de resolução para manter sincronizado com o PC).
 *
 * IMPORTANTE (limitação do Windows, não deste firmware): o mouse absoluto via HID só
 * alcança o monitor PRIMÁRIO. Se o Tibia rodar num monitor secundário, os cliques vão
 * grudar/errar perto das bordas da tela primária.
 */

#include <HID-Project.h>

struct Tecla {
  const char *nome;
  KeyboardKeycode codigo;
};

// Nomes batem com o que o bot já usa em minúsculo nas hotkeys (ex.: cura.tecla_cura_forte
// = "f1") — o lado Python manda em MAIÚSCULO (tecla.upper()). Teclas de 1 caractere
// (dígitos, letras) não precisam estar na tabela: vão direto pro write() ASCII.
static const Tecla TABELA_TECLAS[] = {
  {"F1", KEY_F1}, {"F2", KEY_F2}, {"F3", KEY_F3}, {"F4", KEY_F4},
  {"F5", KEY_F5}, {"F6", KEY_F6}, {"F7", KEY_F7}, {"F8", KEY_F8},
  {"F9", KEY_F9}, {"F10", KEY_F10}, {"F11", KEY_F11}, {"F12", KEY_F12},
  {"ENTER", KEY_ENTER}, {"ESC", KEY_ESC}, {"SPACE", KEY_SPACE},
  {"TAB", KEY_TAB}, {"BACKSPACE", KEY_BACKSPACE},
  {"CTRL", KEY_LEFT_CTRL}, {"SHIFT", KEY_LEFT_SHIFT}, {"ALT", KEY_LEFT_ALT},
  {"UP", KEY_UP_ARROW}, {"DOWN", KEY_DOWN_ARROW},
  {"LEFT", KEY_LEFT_ARROW}, {"RIGHT", KEY_RIGHT_ARROW},
  // CAPSLOCK: usada só pelo teste da aba Arduino do portal (reversível, não digita
  // texto nem clica em nada — segura de disparar a partir do navegador).
  {"CAPSLOCK", KEY_CAPS_LOCK},
};
static const size_t NUM_TECLAS = sizeof(TABELA_TECLAS) / sizeof(TABELA_TECLAS[0]);

// Guarda de "mesma posição duas vezes" — a doc do HID-Project avisa que mover o
// AbsoluteMouse pra um ponto igual ao anterior pode não registrar no Windows. O Alvo
// do bot re-clica repetidamente o mesmo pixel da battle list, então isso é comum.
static int ultimoX = -1;
static int ultimoY = -1;

void moverPara(int x, int y) {
  if (x == ultimoX && y == ultimoY) {
    int nx = x > 0 ? x - 1 : x + 1;
    AbsoluteMouse.moveTo(nx, y);  // nudge descartável p/ "sujar" a posição anterior
  }
  AbsoluteMouse.moveTo(x, y);
  ultimoX = x;
  ultimoY = y;
}

bool enviarTecla(const String &nome) {
  if (nome.length() == 1) {
    BootKeyboard.write((uint8_t)nome[0]);
    return true;
  }
  for (size_t i = 0; i < NUM_TECLAS; i++) {
    if (nome.equalsIgnoreCase(TABELA_TECLAS[i].nome)) {
      BootKeyboard.write(TABELA_TECLAS[i].codigo);
      return true;
    }
  }
  return false;
}

void cmdClicar(int x, int y, bool direito) {
  moverPara(x, y);
  AbsoluteMouse.click(direito ? MOUSE_RIGHT : MOUSE_LEFT);
}

void cmdMover(int x, int y) {
  moverPara(x, y);  // só move — usado pelo teste de mouse da aba Arduino (sem clicar)
}

void cmdArrastar(int x1, int y1, int x2, int y2) {
  moverPara(x1, y1);
  AbsoluteMouse.press(MOUSE_LEFT);
  moverPara(x2, y2);
  AbsoluteMouse.release(MOUSE_LEFT);
}

bool parseDoisNumeros(const String &s, int &a, int &b) {
  int sep = s.indexOf(' ');
  if (sep == -1) return false;
  a = s.substring(0, sep).toInt();
  b = s.substring(sep + 1).toInt();
  return true;
}

bool parseQuatroNumeros(const String &s, int &a, int &b, int &c, int &d) {
  int i1 = s.indexOf(' ');
  if (i1 == -1) return false;
  int i2 = s.indexOf(' ', i1 + 1);
  if (i2 == -1) return false;
  int i3 = s.indexOf(' ', i2 + 1);
  if (i3 == -1) return false;
  a = s.substring(0, i1).toInt();
  b = s.substring(i1 + 1, i2).toInt();
  c = s.substring(i2 + 1, i3).toInt();
  d = s.substring(i3 + 1).toInt();
  return true;
}

void processarComando(const String &linha) {
  int i1 = linha.indexOf(' ');
  String cmd = (i1 == -1) ? linha : linha.substring(0, i1);
  String resto = (i1 == -1) ? "" : linha.substring(i1 + 1);

  if (cmd == "P") {
    // ping: NÃO toca em teclado/mouse — só prova que o firmware está respondendo e
    // mede a latência do round-trip (usado pelo teste de conexão da aba Arduino).
    Serial.println("PONG");
    return;
  }

  if (cmd == "K") {
    if (enviarTecla(resto)) Serial.println("OK");
    else Serial.println("ERR tecla desconhecida");
    return;
  }

  if (cmd == "MV") {
    int x, y;
    if (!parseDoisNumeros(resto, x, y)) {
      Serial.println("ERR argumentos invalidos");
      return;
    }
    cmdMover(x, y);
    Serial.println("OK");
    return;
  }

  if (cmd == "M" || cmd == "MR") {
    int x, y;
    if (!parseDoisNumeros(resto, x, y)) {
      Serial.println("ERR argumentos invalidos");
      return;
    }
    cmdClicar(x, y, cmd == "MR");
    Serial.println("OK");
    return;
  }

  if (cmd == "D") {
    int x1, y1, x2, y2;
    if (!parseQuatroNumeros(resto, x1, y1, x2, y2)) {
      Serial.println("ERR argumentos invalidos");
      return;
    }
    cmdArrastar(x1, y1, x2, y2);
    Serial.println("OK");
    return;
  }

  Serial.println("ERR comando desconhecido");
}

void setup() {
  Serial.begin(115200);
  BootKeyboard.begin();
  AbsoluteMouse.begin();
  Serial.println("READY");
}

void loop() {
  if (Serial.available()) {
    String linha = Serial.readStringUntil('\n');
    linha.trim();
    if (linha.length() > 0) {
      processarComando(linha);
    }
  }
}
