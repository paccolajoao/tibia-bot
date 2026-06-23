# 🤖 Bot Tibia — Pixel-Bot + Dashboard de Observabilidade

Bot de Tibia em Python que **lê a tela** (visão computacional), **decide** e **simula
input** — sem injeção de memória/pacotes. Vem com um **dashboard web ao vivo** para você
ver *o que o bot está fazendo e pensando*: HP/Mana, log de raciocínio, preview anotado e
estatísticas.

**Funcionalidades atuais:**
- ✅ **Auto-heal** — cura forte/leve e poção de mana por threshold de HP/Mana. Cada hotkey pode
  ser **magia OU poção** (o que você bindar no Tibia): ex. cura leve numa magia, cura forte numa pot.
- ✅ **Auto-comer** — aperta a hotkey de comida por tempo.
- ✅ **Targeting** — detecta criaturas na *battle list* e **clica** para atacar.
- ✅ **Auto-loot** — dispara o **Quick Loot do Tibia** (hotkey) quando uma criatura morre.
- ✅ **Magia de ataque** — em combate, aperta **uma** hotkey de ataque periodicamente (a *rotação*
  de magias — exori → exori gran → … — você monta nessa hotkey no próprio Tibia), com **piso de
  mana** para não esvaziar a mana da cura.
- ✅ **Cavebot (navegação por waypoints)** — caminha a hunt **clicando no minimapa** (o Tibia
  pathfinda cada trecho); a chegada é detectada quando o minimapa **para de rolar**. Rota em
  **loop**. Trata **subida/descida** (escadas/buracos/cordas) com **validação da troca de andar**
  e *watchdog* anti-travamento (se um bicho é inalcançável, volta a andar). Grave a rota clicando
  no portal.
- ✅ **Usar mana (treino de Magic Level)** — aperta uma tecla (ex.: cura forte) enquanto a mana
  está cheia, com histerese, para gastar mana e treinar ML.
- ✅ **Drop de loot** — cadastre itens no portal (recortando o ícone **ou enviando um PNG/GIF**) e o
  bot **arrasta** os que encontrar na backpack para um tile do chão calibrado (reconhecimento por
  imagem, **multi-escala** e com máscara de transparência).
- ✅ **Liga/desliga por feature** — aba **Recursos** no portal habilita/desabilita cada
  funcionalidade (útil p/ desligar o loot em conta premium, ou recursos ainda em teste).
- ✅ **À prova de travamento** — cada tick roda dentro de uma rede de segurança: qualquer exceção
  (visão/input/comportamento) é logada e o loop **segue** — uma falha pontual nunca derruba o bot.
- ✅ **Dashboard web ao vivo** — HP/Mana, detecção (criaturas/alvo), decisão atual, log de
  raciocínio, preview anotado e estatísticas (abates, alvos, curas forte/leve, poções e usos de
  mana, saques, refeições, passos do cavebot, magias de ataque) com taxas por minuto.

> As barras de HP/Mana são lidas por amostragem de pixels (HSV), robusta aos **números
> sobrepostos** na barra. A **mana** do Tibia esvazia da esquerda→direita: marque
> **"Mana enche da direita"** na aba *Visão* do portal (ligado por padrão em perfis novos).

Fundação pronta para extensão: captura, visão, decisão (comportamentos por prioridade),
input (teclado **+ mouse**, incl. clique-direito), telemetria e segurança. Veja o
[Roadmap](#roadmap) para o que vem a seguir (ex.: bestiário).

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
| Cura forte / leve | `f5` / `f6` | spell/runa/poção de cura forte e leve (pode ser magia OU pot) |
| Poção de mana | `f1` | usar poção de mana |
| Comida | `f7` | usar comida (auto-comer) |
| Quick Loot | `f4` | **Quick Loot** (saque do corpo) — e configure suas *loot lists* |
| Magia de ataque | `f7` | **uma** hotkey com a rotação de magias de ataque montada no Tibia |
| Usar mana (treino) | `f5` | spell que gaste mana (a de cura forte serve) |
| Cavebot — corda/pá (opcional) | a sua escolha | hotkey de corda/pá, p/ waypoints `tecla` que mudam de andar |

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
depois a de Mana e, opcional, a **battle list** (habilita targeting/auto-loot/magia de ataque),
o **Inventário** + **Tile de drop** (drop de loot) e o **Minimapa** (cavebot). Clique **Salvar
regiões** e **reinicie** o `executar.py` para aplicar.

> **Drop de loot:** depois de calibrar inventário + tile, ligue na aba **Recursos** (ou em
> **Configurações → Drop**) e **cadastre os itens** clicando em *Adicionar item* — recortando o
> ícone de um frame capturado **ou enviando um PNG/GIF** do item. O reconhecimento é multi-escala,
> então ícones de tamanho um pouco diferente ainda casam.

> **Cavebot:** calibre o **Minimapa**, ligue em **Recursos** e, em **Configurações → Cavebot**,
> **grave a rota** clicando em *Gravar waypoint*: tipo **Ir** (clique no minimapa) para andar, e
> **Pisar/Usar/Tecla** para escada/buraco/corda (marque *muda de andar* para o bot validar a troca
> de andar). Use ▲▼ para ordenar. A rota repete em loop.

> **Magia de ataque:** com a battle list calibrada, ligue em **Recursos** e ajuste a hotkey +
> piso de mana em **Configurações → Magia de ataque**.

> Prefere linha de comando? O `calibrar.py` ainda existe e grava no mesmo perfil ativo
> (`.\.venv\Scripts\python.exe calibrar.py`).

> **Aplicar mudanças exige reiniciar o bot.** Config e calibração são salvas no perfil ativo
> (SQLite) e passam a valer no próximo `executar.py`.

### Controles e segurança
- **F11** — pausa/retoma. **F12** — pânico (para o input na hora).
- **Foco gateia só o INPUT, não a leitura:** sem o Tibia em foco o bot continua **lendo** e
  mostrando HP/Mana no painel, mas **não envia teclas/cliques** (o SendInput só chega na janela em
  foco). Não há auto-pause — o Pausar/Retomar manual não é revertido.
- Botões **Pausar/Retomar/Parar** também no painel.

## Configuração — pelo portal (perfis em SQLite)

A configuração agora é **gerenciada pelo portal** e persistida em **SQLite** (`config/bot.db`),
não mais editando YAML à mão. Cada **perfil** guarda um conjunto completo de config (ex.: um
por personagem/caçada); a aba **Perfis** cria, ativa, duplica, renomeia e faz **import/export
YAML**. Na 1ª execução, o `config.yaml` existente (ou `config.exemplo.yaml`) é migrado para um
perfil "Padrão" automaticamente. A aba **Recursos** centraliza o liga/desliga de cada feature
(com avisos de dependência e selo "em teste"); as demais abas têm formulários validados para
todas as seções abaixo:

| Seção | Campo | O que faz |
|---|---|---|
| `cura` | `ativo` | liga/desliga a auto-cura |
| `cura` | `hp_critico` / `hp_baixo` | HP% que dispara cura forte / leve |
| `cura` | `mana_baixa` | Mana% que dispara poção de mana |
| `cura` | `tecla_*` | hotkeys no jogo (ex.: `f5`, `f6`, `f1`) |
| `cura` | `cooldown_s` | intervalo mínimo por tecla (anti-spam) |
| `alvo` | `ativo` | liga/desliga o targeting (também exige battle list calibrada) |
| `alvo` | `tecla` n/a — usa **clique** | targeting clica na battle list; `confianca_minima`, `cooldown_s.atacar` |
| `comer` | `ativo` / `tecla` / `intervalo_s` | hotkey de comida e de quantos em quantos segundos comer |
| `saque` | `ativo` / `tecla` / `janela_s` / `prioridade` | hotkey de Quick Loot, por quanto tempo tentar após um kill, e prioridade (default 85, acima do alvo) |
| `usar_mana` | `ativo` / `tecla` / `mana_alto` / `mana_alvo` | treino de ML: gasta mana com histerese. Mana cheia raramente lê 100% → use `mana_alto` ~95 |
| `drop` | `ativo` / `itens` / `threshold` | drop de loot: itens (com template) a arrastar p/ o chão e a confiança do reconhecimento |
| `magia_ataque` | `ativo` / `tecla` / `intervalo_s` / `mana_minima` | em combate, aperta 1 hotkey de ataque a cada `intervalo_s`; não ataca abaixo de `mana_minima`% |
| `cavebot` | `ativo` / `waypoints` / `cooldown_s` | navegação por waypoints no minimapa (rota em loop). Exige `regioes.minimap` |
| `cavebot` | `combate_timeout_s` | se há criatura mas nenhuma morte por este tempo (bicho inalcançável), volta a andar. `0` = nunca desiste |
| `cavebot` | `limiar_troca_andar` / `tentativas_troca` | validação de escada/buraco/corda: pico do minimapa que confirma a troca + nº de re-tentativas |
| `visao` | `confianca_minima` | abaixo disso, ignora a leitura (não cura errado) |
| `visao` | `hp.invertido` / `mana.invertido` | direção de preenchimento da barra (mana enche da direita) |
| `captura` | `backend` | `auto` \| `bettercam` \| `wgc` \| `mss` \| `obs` \| `tibia_arquivo` |
| `captura` | `fps_alvo` | ticks/seg do loop |
| `seguranca` | `titulo_janela_contains` | título p/ detectar foco (`Tibia`) |

Toda feature tem um campo `ativo` (incl. `cura`/`alvo`); a aba **Recursos** é o jeito prático de
ligar/desligar. `alvo`, `saque` e `magia_ataque` só entram em ação quando a **battle list** está
calibrada. O **drop** exige `regioes.inventario` e `regioes.drop_tile` calibrados (na aba
*Calibração*) e ao menos um item cadastrado. O **cavebot** exige `regioes.minimap` calibrado e ao
menos um waypoint gravado.

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

- **Visão:** lê o % de cada barra classificando por **coluna** (toda a altura) em
  **HSV (brilho+saturação)** — funciona com HP mudando de cor, mana azul, é robusta aos
  **números sobre a barra** e respeita a **direção** (`invertido`, p/ a mana). Também detecta
  **criaturas na battle list** (mini HP-bars), se há **alvo atual**, e **itens no inventário**
  (template matching **multi-escala**, com máscara de transparência) p/ o drop. Leitura "suja"
  (tooltip cobrindo) gera **confiança baixa** e é ignorada.
- **Decisão:** comportamentos por **prioridade** (cura 100 > saque 85 > alvo 80 > magia_ataque 70 >
  drop 50 > cavebot 20 > usar_mana 15 > comer 10); o primeiro que quer agir vence o tick (uma ação
  por tick), com **cooldown** por hotkey. Cada comportamento tem um `ativo` (liga/desliga na aba
  *Recursos*). Ações: **pressionar tecla** (cura/comer/saque/usar_mana/magia_ataque), **clicar**
  (atacar na battle list, andar no minimapa), **clicar-direito** (usar escada/alavanca no cavebot)
  ou **arrastar** (drop de item p/ o chão). `cavebot` e `usar_mana` são tarefas de ocioso: **cedem
  ao combate**.
- **Telemetria:** a fila é **best-effort** (descarta o mais antigo se cheia) — o loop do bot
  **nunca trava** por causa do painel.
- **À prova de falhas:** todo o trabalho do tick roda dentro de um `try/except` — uma exceção em
  visão/input/comportamento é logada (com throttle) e o loop **segue** para o próximo tick, sem
  derrubar a thread do bot.

### Estrutura
```
executar.py / calibrar.py        # entrypoints
src/bot/
  captura/    base · dxgi · wgc · mss_fallback · obs_virtualcam · mapeamento · tibia_arquivo · instantaneo · fabrica
  visao/      barra_recursos · lista_batalha · inventario · minimap · anotador · tipos
  decisao/    motor · cooldown · comportamentos/(auto_cura, alvo, comer, saque, drop, usar_mana, magia_ataque, cavebot)
  telemetria/ eventos · barramento · estatisticas
  entrada/    teclado_directinput · atrasos · simulada
  nucleo/     loop_bot · estado_execucao · seguranca
  persistencia/ banco · repo_perfis        # SQLite: perfis + config (fonte única)
  painel/     servidor · api · ponte · web/(painel legado)
  ferramentas/seletor_regiao
portal/                          # frontend: Vite + React + TS + Tailwind + shadcn
  src/        pages/(Dashboard, Configuracoes, Perfis, Calibracao) · components/(ui, DropItens, Waypoints) · hooks · lib
tests/                           # testes offline (não precisam do jogo)
```

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Cobrem visão — barras, battle list, **inventário** (template matching multi-escala + máscara de
alfa) e **minimapa** (detecção de movimento) contra imagens sintéticas —, motor/cooldown, os
comportamentos (cura, alvo, comer, saque, **usar mana**, **magia de ataque**, **cavebot** — incl.
watchdog de combate e validação de troca de andar), barramento, a ponte assíncrona, o **painel
web** (serve o HTML + streaming WebSocket via TestClient) e testes de integração do loop com
captura/entrada falsas — **incluindo a rede de segurança** (uma exceção a cada tick não derruba o
loop). Tudo **sem o jogo aberto**.

## Roadmap

Cada feature nova = uma classe que implementa `ComportamentoBase` registrada no motor com uma
prioridade (a cura fica em ~100, então sempre vence). Ex.: criar
`src/bot/decisao/comportamentos/minha_feature.py` com `nome`, `prioridade` e `avaliar(contexto)`,
e adicioná-la à lista do `MotorDecisao` em `executar.py` — como já foi feito para todos os
comportamentos abaixo.

1. ✅ **Targeting** (`alvo.py`, ~80) — detecta criaturas na battle list e **clica** para atacar.
   Habilita marcando a battle list na aba *Calibração*. A entrada tem **mouse** e o motor entende
   a ação `CLICAR`.
2. ✅ **Auto-comer** (`comer.py`, ~10) — aperta a hotkey de comida por tempo (`intervalo_s`).
3. ✅ **Auto-loot** (`saque.py`, ~85) — dispara o **Quick Loot do Tibia** (hotkey) quando uma
   criatura morre (a contagem na battle list cai). A **filtragem de itens fica nas loot lists
   do próprio Tibia** — o painel mostra a contagem de saques, mas não gerencia o que ignorar.
4. ✅ **Drop de loot** (`drop.py`, ~50) — arrasta itens cadastrados (template matching) p/ o chão.
5. ✅ **Magia de ataque** (`magia_ataque.py`, ~70) — 1 hotkey de ataque em combate, com piso de mana.
6. ✅ **Cavebot/waypoints** (`cavebot.py`, ~20) — navegação por **clique no minimapa** (o Tibia
   pathfinda cada trecho; chegada por "minimapa parou de rolar"), rota em loop, validação de troca
   de andar e watchdog anti-travamento. **Não** usa A\*/grade — é pixel-puro, mais simples e robusto.
7. **Bestiário** — contagem de kills por criatura (depende de targeting).

Cross-cutting: OCR (`pytesseract`) para números absolutos de HP/Mana no painel; auto-loot
**bot-driven** (abrir corpo + template matching de sprites) para uma lista de ignorados
gerida no portal; posição absoluta no minimapa (SLAM) para cavebot auto-corretivo.

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
- No portal, em **Configurações → Captura**, defina **`backend: obs`** (e salve; reinicie o bot).
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
     instale a lib: `pip install windows-capture`, ou force `backend: wgc` no portal (Configurações → Captura).
  3. **Tela cheia EXCLUSIVA** derrota até WGC/DXGI (ignora o compositor do Windows). Em
     **Options → Graphics**, desligue **Full screen mode** e use **janela / sem bordas**.

  O `calibrar.py` salva o print em `dados/capturas/calibracao_screenshot.png` e avisa quando
  a captura vem preta — abra esse PNG para confirmar o que foi capturado.
- **Tecla não chega no jogo** → rode o terminal como **Administrador**; confirme o `backend`
  e que as hotkeys do perfil (no portal) batem com as do cliente. Lembre que **sem foco** na
  janela do Tibia o bot lê mas **não envia** input.
- **Hotkeys F11/F12 não funcionam** → idem (admin).
- **`bettercam` não instala** → normal no Python 3.13; o bot usa `mss` (veja o log na inicialização).
- **% calibrado errado** → recalibre; em setup **multi-monitor**, mantenha o Tibia no monitor
  primário (coords começam em 0,0). Ajuste `visao.hp.v_min/s_min` se a barra tiver cor atípica.
