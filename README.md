# 🤖 Bot Tibia — Pixel-Bot + Dashboard de Observabilidade

Bot de Tibia em Python que **lê a tela** (visão computacional), **decide** e **simula
input** — sem injeção de memória/pacotes. Vem com um **dashboard web ao vivo** para você
ver *o que o bot está fazendo e pensando*: HP/Mana, log de raciocínio, preview anotado e
estatísticas.

**Funcionalidades atuais:**
- ✅ **Auto-heal** — cura forte/leve e poção de mana por threshold de HP/Mana.
- ✅ **Auto-comer** — aperta a hotkey de comida por tempo.
- ✅ **Targeting** — detecta criaturas na *battle list* e **clica** para atacar (só quando não há alvo).
- ✅ **Auto-loot** — dispara o **Quick Loot do Tibia** (hotkey) quando uma criatura morre.
- ✅ **Dashboard web ao vivo** — HP/Mana, detecção (criaturas/alvo), decisão atual, log de
  raciocínio, preview anotado e estatísticas (curas, ataques, refeições, saques).

Fundação pronta para extensão: captura, visão, decisão (comportamentos por prioridade),
input (teclado **+ mouse**), telemetria e segurança. Próximas features (cavebot, bestiário)
já têm o ponto de extensão — veja o [Roadmap](#roadmap).

> ⚠️ **Aviso.** Automatizar o cliente **oficial** do Tibia viola os Termos de Serviço da
> CipSoft e há **BattlEye** (anti-cheat kernel-level). Esta abordagem é *pixel-only, processo
> externo, sem injeção* — mais difícil de detectar, **mas não invisível**: o risco de ban é
> seu. Recomendações prudentes: use **conta de teste/descartável** e, idealmente, valide em
> um **OT Server** que você controla. Este projeto não tenta burlar anti-cheat.

---

## Requisitos

- **Windows** (usa SendInput, foco de janela, DXGI).
- **Python 3.12 ou 3.13** — qualquer um serve. A captura escolhe sozinha o melhor backend
  disponível: **DXGI/bettercam** (só 3.12) → **WGC/Windows Graphics Capture** (roda no 3.13 e
  **captura DX11/DX12/OpenGL**) → **mss** (GDI puro, último recurso). O `mss` **não** lê
  surfaces de GPU (cliente em DX12 vem preto), por isso no 3.13 o **WGC** é quem resolve.
- **Rodar o terminal como Administrador** (hotkeys globais F11/F12 e para o SendInput chegar
  no cliente Tibia, que costuma rodar elevado).

## Instalação

```powershell
# na raiz do projeto (c:\dev\bot-tibia)
py -3.13 -m venv .venv          # ou: py -3.12 -m venv .venv (se tiver o 3.12)
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> **O Python 3.12 é OPCIONAL.** Se você só tem o 3.13, use `py -3.13` e ignore o 3.12 — o
> bot roda igual via `mss`. Se rodar `py -3.12` sem ter o 3.12 instalado, o Windows mostra
> **`No suitable Python runtime found`** — não é erro do projeto, é só o 3.12 ausente. A
> única coisa que o 3.12 acrescenta é o `bettercam` (captura DXGI ~240 FPS), **desnecessário
> para auto-heal/targeting/loot**. Para tê-lo depois: `winget install Python.Python.3.12`,
> recrie a venv com `py -3.12 -m venv .venv` e reinstale os requirements.

Para desenvolver/testar, use `requirements-dev.txt` (inclui pytest).

**Portal web (frontend).** Toda a configuração e calibração agora são feitas pelo **portal**
(React + Tailwind + shadcn). Ele precisa ser buildado uma vez (requer **Node 18+**):

```powershell
cd portal
npm install
npm run build        # gera portal/dist (servido pelo executar.py)
cd ..
```

O `executar.py` serve o `portal/dist` automaticamente em `http://127.0.0.1:8000`. Se você
ainda **não** buildou, o servidor cai no painel legado (somente leitura). Para desenvolver o
frontend com hot-reload: `npm run dev` (porta 5173, com proxy de `/api` e `/ws` para a 8000).

## Uso — passo a passo

**1) Bindar as hotkeys NO Tibia** (uma vez). As teclas do bot precisam existir no cliente:

| Ação | Tecla padrão (config) | O que bindar no Tibia |
|---|---|---|
| Cura forte / leve | `f5` / `f6` | spell/runa de cura forte e leve |
| Poção de mana | `f1` | usar poção de mana |
| Comida | `f7` | usar comida (auto-comer) |
| Quick Loot | `f4` | **Quick Loot** (saque do corpo) — e configure suas *loot lists* |

> O **auto-loot usa o Quick Loot do Tibia**: a filtragem de itens (o que ignorar) é
> configurada **nas loot lists do próprio cliente**, não no painel.

**2) Tibia oficial (BattlEye)? Configure o OBS primeiro.** Se a calibração vier **preta**, o
cliente está bloqueando a captura (`WDA_EXCLUDEFROMCAPTURE`) — siga o
[passo a passo do OBS](#captura-via-obs-tibia-oficial--wda_excludefromcapture) e volte para a
calibração. Em OT Server / cliente sem BattlEye, pule este passo (deixe `backend: auto`).

**3) Executar** (de preferência num terminal **Administrador**):

```powershell
.\.venv\Scripts\python.exe executar.py
```

Abra o **portal**: **http://127.0.0.1:8000**. Mesmo **sem calibração** o portal sobe — é por
ele que você configura e calibra. (O log de inicialização diz quais módulos ficaram ativos;
targeting/auto-loot só ligam se a battle list foi calibrada.)

**4) Calibrar pelo portal** (uma vez, ou quando mudar o layout do cliente). Na aba
**Calibração**: clique **Capturar frame**, **arraste um retângulo** sobre a barra de HP,
depois a de Mana e, opcional, a **battle list** (habilita targeting/auto-loot). Clique
**Salvar regiões** e **reinicie** o `executar.py` para aplicar.

> Prefere linha de comando? O `calibrar.py` ainda existe e grava no mesmo perfil ativo
> (`.\.venv\Scripts\python.exe calibrar.py`).

> **Aplicar mudanças exige reiniciar o bot.** Config e calibração são salvas no perfil ativo
> (SQLite) e passam a valer no próximo `executar.py`.

### Controles e segurança
- **F11** — pausa/retoma. **F12** — pânico (para o input na hora).
- **Auto-pause ao perder o foco** da janela do Tibia (volta sozinho quando você foca de novo).
- Botões **Pausar/Retomar/Parar** também no painel.

## Configuração — pelo portal (perfis em SQLite)

A configuração agora é **gerenciada pelo portal** e persistida em **SQLite** (`config/bot.db`),
não mais editando YAML à mão. Cada **perfil** guarda um conjunto completo de config (ex.: um
por personagem/caçada); a aba **Perfis** cria, ativa, duplica, renomeia e faz **import/export
YAML**. Na 1ª execução, o `config.yaml` existente (ou `config.exemplo.yaml`) é migrado para um
perfil "Padrão" automaticamente. A aba **Configurações** tem formulários validados para todas
as seções abaixo:

| Seção | Campo | O que faz |
|---|---|---|
| `cura` | `hp_critico` / `hp_baixo` | HP% que dispara cura forte / leve |
| `cura` | `mana_baixa` | Mana% que dispara poção de mana |
| `cura` | `tecla_*` | hotkeys no jogo (ex.: `f5`, `f6`, `f1`) |
| `cura` | `cooldown_s` | intervalo mínimo por tecla (anti-spam) |
| `alvo` | `tecla` n/a — usa **clique** | targeting clica na battle list; `confianca_minima`, `cooldown_s.atacar` |
| `comer` | `tecla` / `intervalo_s` | hotkey de comida e de quantos em quantos segundos comer |
| `saque` | `tecla` / `janela_s` | hotkey de Quick Loot e por quanto tempo tentar após um kill |
| `visao` | `confianca_minima` | abaixo disso, ignora a leitura (não cura errado) |
| `captura` | `backend` | `auto` \| `bettercam` \| `wgc` \| `mss` \| `obs` \| `tibia_arquivo` |
| `captura` | `fps_alvo` | ticks/seg do loop |
| `seguranca` | `titulo_janela_contains` | título p/ detectar foco (`Tibia`) |

`alvo` e `saque` só entram em ação quando a **battle list** está calibrada. `comer`/`saque`
têm um campo `ativo` para ligar/desligar.

## Como funciona

```
  THREAD DO BOT (síncrona)                         ASYNCIO (uvicorn / FastAPI)
  captura (mss/dxgi)                               ┌───────────────────────────┐
   -> visão (HP/Mana %)        queue.Queue         │ ponte: drena a fila e faz  │
   -> decisão (motor+cooldown) ───(limitada)──────►│ broadcast por WebSocket    │──► navegador
   -> input (pydirectinput)    descarta-mais-antigo└───────────────────────────┘    (dashboard)
   -> publica telemetria             ▲  controle painel->bot (pausar/parar)
                                      └──────────── canal separado (Lock+Event)
```

- **Visão:** lê o % de cada barra amostrando pixels e classificando preenchido vs vazio por
  **HSV (brilho+saturação)** — funciona com HP mudando de cor e mana azul. Também detecta
  **criaturas na battle list** (mini HP-bars) e se há **alvo atual**. Leitura "suja" (tooltip
  cobrindo) gera **confiança baixa** e é ignorada.
- **Decisão:** comportamentos por **prioridade** (cura 100 > alvo 80 > saque 60 > comer 10);
  o primeiro que quer agir vence o tick (uma ação por tick), com **cooldown** por hotkey.
  Ações: **pressionar tecla** (cura/comer/saque) ou **clicar** (atacar na battle list).
- **Telemetria:** a fila é **best-effort** (descarta o mais antigo se cheia) — o loop do bot
  **nunca trava** por causa do painel.

### Estrutura
```
executar.py / calibrar.py        # entrypoints
src/bot/
  captura/    base · dxgi · wgc · mss_fallback · obs_virtualcam · mapeamento · tibia_arquivo · instantaneo · fabrica
  visao/      barra_recursos · lista_batalha · anotador · tipos
  decisao/    motor · cooldown · comportamentos/(auto_cura, alvo, comer, saque, usar_mana)
  telemetria/ eventos · barramento · estatisticas
  entrada/    teclado_directinput · atrasos · simulada
  nucleo/     loop_bot · estado_execucao · seguranca
  persistencia/ banco · repo_perfis        # SQLite: perfis + config (fonte única)
  painel/     servidor · api · ponte · web/(painel legado)
  ferramentas/seletor_regiao
portal/                          # frontend: Vite + React + TS + Tailwind + shadcn
  src/        pages/(Dashboard, Configuracoes, Perfis, Calibracao) · components/ui · hooks · lib
tests/                           # testes offline (não precisam do jogo)
```

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Cobrem visão — barras e battle list — (contra imagens sintéticas), motor/cooldown, os
comportamentos (cura, alvo, comer, saque), barramento, a ponte assíncrona, o **painel web**
(serve o HTML + streaming WebSocket via TestClient) e testes de integração do loop com
captura/entrada falsas — tudo **sem o jogo aberto**.

## Roadmap

Cada feature nova = uma classe que implementa `ComportamentoBase` registrada no motor com uma
prioridade (a cura fica em ~100, então sempre vence). Ex.: criar
`src/bot/decisao/comportamentos/cavebot.py` com `nome`, `prioridade` e `avaliar(contexto)`,
e adicioná-la à lista do `MotorDecisao` em `executar.py` — como já foi feito para
`alvo`, `comer` e `saque`.

1. ✅ **Targeting** (`alvo.py`, ~80) — detecta criaturas na battle list e **clica** para
   atacar (só quando não há alvo atual). Habilita marcando a battle list em `calibrar.py`.
   A entrada já tem **mouse** (`clicar`) e o motor já entende a ação `CLICAR`.
2. ✅ **Auto-comer** (`comer.py`, ~10) — aperta a hotkey de comida por tempo (`intervalo_s`).
3. ✅ **Auto-loot** (`saque.py`, ~60) — dispara o **Quick Loot do Tibia** (hotkey) quando uma
   criatura morre (a contagem na battle list cai). A **filtragem de itens fica nas loot lists
   do próprio Tibia** — o painel mostra a contagem de saques, mas não gerencia o que ignorar.
   Limitação: sem cavebot, só pega corpos adjacentes (melee).
4. **Cavebot/waypoints** (`cavebot.py`, ~20) — pathfinding **A\*** (`tcod`) sobre grade lida
   do minimap. Parte mais complexa do projeto.
5. **Bestiário** — contagem de kills por criatura (depende de targeting).

Cross-cutting: OCR (`pytesseract`) para números absolutos de HP/Mana no painel; auto-loot
**bot-driven** (abrir corpo + template matching de sprites) para uma lista de ignorados
gerida no portal.

## Captura via OBS (Tibia oficial / WDA_EXCLUDEFROMCAPTURE)

O Tibia oficial (BattlEye) usa `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)`: o **compositor
do Windows** apaga a janela de TODO caminho de captura externo (mss, WGC, DXGI, PrintWindow,
PrintScreen → tudo preto). O **OBS é whitelisted pelo BattlEye**, então a captura dele enxerga o
jogo. Usamos a **OBS Virtual Camera** como fonte de frames (~30-60 FPS, ao vivo) — bem melhor que
o fallback lento `tibia_arquivo` (~3 FPS via hotkey de screenshot).

> ⚠️ Automatizar o Tibia oficial viola o ToS e pode resultar em ban pelo BattlEye. O caminho OBS
> não *adultera* o cliente, mas não torna a automação compatível com as regras. Use por sua conta.

### Passo a passo do OBS

**1. Instalar o OBS Studio**
- Baixe em <https://obsproject.com> e instale. Abra o OBS (não precisa de admin).
- Se aparecer o "Assistente de configuração automática", pode cancelar — vamos configurar à mão.

**2. Deixar o Tibia em janela**
- No Tibia: **Options → Graphics → Full screen mode: OFF** (janela ou sem bordas).
- Posicione a janela do Tibia onde for ficar durante o uso (a captura segue a janela em runtime,
  mas é mais simples deixá-la fixa).

**3. Casar a resolução do canvas com a janela do Tibia** *(passo que deixa o clique preciso)*
- No OBS: **Settings (Configurações) → Video (Vídeo)**.
- Em **Base (Canvas) Resolution**, coloque o **mesmo tamanho da janela do Tibia**
  (ex.: `1280x720`, `1600x900`, `1920x1080`). Em dúvida, use a resolução do seu monitor.
- **Output (Scaled) Resolution**: igual à Base. **FPS**: 30 ou 60. Aplique e feche.

**4. Adicionar a fonte de captura do Tibia**
- No painel **Sources (Fontes)**, clique em **+** → **Game Capture (Captura de Jogo)**
  → *Create new* → OK.
- Em **Mode (Modo)**, escolha **Capture specific window** e selecione o cliente do Tibia na lista.
  (Se o Game Capture vier preto, troque a fonte para **Window Capture (Captura de Janela)** com o
  método de captura **Windows 10 (1903 and up)** / **WGC** — também funciona com o Tibia.)
- **IMPORTANTE:** desmarque/oculte o cursor — em **Game Capture** desligue **Capture Cursor**
  (em Window Capture, **Cursor: OFF**). O cursor na captura confunde a leitura das barras.
- Clique **OK**.

**5. Encaixar a captura no canvas 1:1**
- Com a fonte selecionada na cena, clique nela com o botão direito → **Transform (Transformar) →
  Fit to screen (Ajustar à tela)** (atalho **Ctrl+F**). A imagem do Tibia deve preencher todo o
  canvas, sem barras pretas nas laterais. Se sobrar borda preta, revise o passo 3 (a resolução do
  canvas tem que bater com a da janela do Tibia).

**6. Ligar a câmera virtual**
- No canto inferior direito (**Controls**), clique em **Start Virtual Camera**
  (Iniciar Câmera Virtual). Deixe o OBS **aberto** enquanto usar o bot.

**7. Apontar o bot para o OBS**
- No `config/config.yaml`, seção `captura`: defina **`backend: obs`**.
- Opcional, mas recomendado: `pip install pygrabber` — assim o bot acha a câmera pelo nome
  (`obs_device_nome: OBS Virtual Camera`). Sem o pygrabber, ajuste `obs_device_index` (0, 1, 2…)
  até cair na câmera virtual (se tiver webcam física, o índice da virtual costuma ser o maior).
- **Resolução:** o DirectShow abre a câmera em **640x480** por padrão (fica borrado na
  calibração). O bot pede `obs_largura`/`obs_altura` (padrão **1920x1080**) — deixe esses valores
  **iguais à resolução de saída do OBS** (passo 3, *Output Resolution*) para o frame ficar nítido.

**8. Calibrar e rodar**
- `python calibrar.py` — agora o frame **não vem preto**; marque HP, mana e battle list. A
  calibração grava `mapeamento_obs` e confere se o canvas bate 1:1 com a janela (avisa se não).
- `python executar.py` — confira no painel HP/mana atualizando a ~15 FPS.

**Como o clique funciona com o OBS:** as regiões calibradas ficam em **coords do canvas do OBS**;
o clique de targeting é convertido para a tela em runtime lendo a **posição viva da janela do
Tibia** (mover a janela não exige recalibrar). Com `backend: obs`, o auto-fallback para `mss` fica
desativado (mss vem preto no Tibia). Se o canvas **não** ficou 1:1, o bot ainda aplica a escala —
mas o 1:1 deixa o clique mais exato.

## Troubleshooting

- **Tela PRETA na calibração / bot não enxerga o jogo** → captura voltando preta. Causas:
  1. **Tibia oficial com BattlEye** (`WDA_EXCLUDEFROMCAPTURE`) → mss/WGC/DXGI/PrintWindow vêm
     todos pretos. Use **`backend: obs`** (seção acima) — é a saída recomendada.
  2. **Cliente em DX12/OpenGL + backend `mss`** (GDI não lê GPU). No 3.13 o backend **WGC**
     resolve — confirme no log de inicialização "backend WGC ... ativo". Se aparecer "mss",
     instale a lib: `pip install windows-capture`, ou force `backend: wgc` no `config.yaml`.
  3. **Tela cheia EXCLUSIVA** derrota até WGC/DXGI (ignora o compositor do Windows). Em
     **Options → Graphics**, desligue **Full screen mode** e use **janela / sem bordas**.

  O `calibrar.py` salva o print em `dados/capturas/calibracao_screenshot.png` e avisa quando
  a captura vem preta — abra esse PNG para confirmar o que foi capturado.
- **Tecla não chega no jogo** → rode o terminal como **Administrador**; confirme o `backend`
  e as hotkeys do `config.yaml` iguais às do cliente.
- **Hotkeys F11/F12 não funcionam** → idem (admin).
- **`bettercam` não instala** → normal no Python 3.13; o bot usa `mss` (veja o log na inicialização).
- **% calibrado errado** → recalibre; em setup **multi-monitor**, mantenha o Tibia no monitor
  primário (coords começam em 0,0). Ajuste `visao.hp.v_min/s_min` se a barra tiver cor atípica.
