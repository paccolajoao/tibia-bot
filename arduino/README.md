# Entrada via Arduino (HID de hardware)

Backend opcional/avançado (`entrada.backend: arduino`) que troca o `SendInput` do
Windows por um Arduino que emite teclado/mouse **HID de verdade** — o Windows não
distingue de hardware físico.

## Board necessário — **não é a BlackBoard**

A RoboCore BlackBoard V1.0 usa ATmega328P + um conversor USB-serial fixo (FT232RL ou
Silicon Labs) — é, na prática, um clone de Arduino Uno R3. Ela **não tem USB nativo**,
então nenhum firmware consegue fazê-la se apresentar ao Windows como teclado/mouse.

É preciso um board com **USB nativo**: ATmega32u4 — **Arduino Leonardo, Micro ou Pro
Micro** (qualquer um serve; Pro Micro é o mais barato/compacto). Nenhuma fiação
externa é necessária — board puro, um cabo USB.

## Gravando o firmware

1. Arduino IDE → **Sketch > Include Library > Manage Libraries...** → instale
   **"HID-Project"** (autor: NicoHood).
2. **Tools > Board** → selecione Arduino Leonardo/Micro/Pro Micro (conforme o seu).
3. Abra `entrada_hid.ino` (nesta pasta) e faça upload.
4. Ao conectar, o board expõe **duas interfaces USB ao mesmo tempo**, pela mesma
   porta física: uma porta serial (COM) — o canal de comandos — e um teclado/mouse
   HID genuíno (visíveis no Gerenciador de Dispositivos do Windows). Isso é esperado
   — é um único dispositivo USB composto, não dois cabos.

## Configurando e testando no portal

Aba **Configurações → Arduino** (dedicada — separada da aba Sistema):
- **Status**: checklist ao vivo (backend = Arduino? porta preenchida? porta detectada
  agora pelo sistema?).
- **Configuração**: backend (`Arduino (HID de hardware)`), porta COM (a lista de
  portas detectadas aparece como dica no campo), baud rate (`115200`, bate com o
  firmware), timeout de resposta, e a resolução da tela (deixe `0` para
  auto-detectar o monitor primário).
- **Teste rápido**: botão que usa a config **como está digitada** (não precisa salvar
  antes) e roda, em sequência: conectar, ping (round-trip, sem tocar em
  teclado/mouse), teclado (aperta **Caps Lock** — reversível, não digita texto nem
  clica em nada) e mouse-movimento (move o cursor pro centro da tela, sem clicar).
  Mostra a latência (ms) de cada etapa. Há também um teste **opcional** de clique
  real do mouse (desligado por padrão) — só ligue apontando um ponto vazio da tela,
  porque ele CLICA de verdade onde você mandar.
  > Se o bot já estiver rodando com o backend Arduino, pare-o antes de testar: só um
  > processo pode ter a porta serial aberta por vez.

Depois de validar pelo teste, clique em **Salvar** (grava no perfil ativo, no
SQLite) e reinicie o bot para aplicar.

## Limitações conhecidas

- **Monitor primário apenas.** O mouse absoluto via HID só alcança o monitor
  primário do Windows (restrição da própria pilha de driver HID, não deste
  firmware/bot). Se o Tibia rodar num monitor secundário, os cliques do Arduino vão
  errar/grudar perto das bordas da tela primária — mantenha o Tibia no monitor
  primário para usar este backend.
- **Sem combos de tecla.** O protocolo só cobre teclas simples (é tudo que o bot já
  usa — nenhuma hotkey do bot é um combo tipo `ctrl+x`).
- **Hotkeys globais (F11 pausar / F12 pânico) continuam exigindo Administrador**,
  independente do backend de entrada escolhido — isso é a lib `keyboard` (hotkey
  global), não tem relação com SendInput/Arduino.

## O que não pode ser testado sem o hardware

Este firmware foi escrito e revisado, mas não compilado/flashado nem testado num
board físico. Ao montar o seu:
1. Confira no Gerenciador de Dispositivos que aparecem um teclado e um mouse HID
   genuínos (não só uma porta COM).
2. Use o **Teste rápido** da aba Arduino do portal (acima) — ele já cobre
   conectividade, teclado e movimento do mouse sem risco. Se alguma etapa falhar, o
   detalhe do erro aparece ali mesmo.
3. Rode o teste opcional de **clique real** do mouse pelo menos uma vez, apontado
   pra um lugar vazio da tela, pra confirmar que o clique (não só o movimento)
   realmente registra no Windows.
4. Confirme fora do teste automático que cliques repetidos no MESMO pixel (ex.:
   re-atacar o mesmo alvo) continuam registrando — é o cenário que o "nudge" em
   `moverPara()` existe para cobrir; o teste rápido não repete o mesmo ponto duas
   vezes, então esse caso específico só aparece em uso real do bot.
