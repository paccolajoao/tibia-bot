# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

A Tibia pixel-bot: it **reads the screen** (computer vision), **decides**, and **simulates input** — no memory/packet injection. Ships with a live web dashboard. Windows-only.

> **Language convention:** the code, identifiers, comments, commit messages, and the README are all in **Brazilian Portuguese**. Match this — name new modules/classes/functions in Portuguese and keep comments in Portuguese. (e.g. `captura`=capture, `visao`=vision, `decisao`=decision, `entrada`=input, `nucleo`=core, `seguranca`=safety, `barramento`=event bus, `ponte`=bridge, `comportamento`=behavior, `alvo`=target, `saque`=loot, `cura`=heal.)

## Commands

All commands use the project venv interpreter directly (`.\.venv\Scripts\python.exe`). The shell is PowerShell.

```powershell
# Setup
py -3.13 -m venv .venv                                          # 3.12 or 3.13 both work
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt   # dev deps include pytest/ruff

# Portal frontend (Vite + React + Tailwind + shadcn). Build once; FastAPI serves portal/dist.
cd portal; npm install; npm run build; cd ..   # requires Node 18+
# (dev w/ hot-reload: cd portal; npm run dev  -> :5173, proxies /api and /ws to :8000)

# Run (prefer an Administrator terminal so SendInput reaches the elevated Tibia client)
.\.venv\Scripts\python.exe executar.py     # runs bot loop + portal at http://127.0.0.1:8000
#                                            (portal comes up even uncalibrated — calibrate in-browser)
.\.venv\Scripts\python.exe calibrar.py     # optional CLI calibration (writes the active SQLite profile)

# Tests (all offline — no game needed)
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest tests/test_motor_decisao.py -q          # single file
.\.venv\Scripts\python.exe -m pytest tests/test_alvo.py::test_nome -q        # single test

# Lint
.\.venv\Scripts\python.exe -m ruff check .
```

`pyproject.toml` sets `pythonpath = ["src", "."]` for pytest, so tests import `bot.*` without installing the package. The entrypoints (`executar.py`, `calibrar.py`) instead inject `src/` onto `sys.path` manually at startup.

## Architecture

**Two-thread model bridged by a queue.** This is the central design constraint:

```
THREAD DO BOT (synchronous)                    ASYNCIO (uvicorn / FastAPI)
captura -> visao -> decisao -> entrada    queue.Queue (bounded,    PonteAssincrona drains
        -> publica telemetria          ───  drop-oldest)  ──────►  the queue, broadcasts
                                                                    each event over WebSocket
control (pause/stop) panel -> bot: separate channel (ControladorExecucao: Lock + Event)
```

- [src/bot/nucleo/loop_bot.py](src/bot/nucleo/loop_bot.py) — `LoopBot(threading.Thread)`. The synchronous tick loop: capture → read bars → detect creatures → `motor.decidir` → execute input → publish telemetry. Steady cadence via `captura.fps_alvo`; the annotated preview and stats have their own throttles so they don't flood the WebSocket. `max_ticks` exists only for tests.
- [src/bot/contexto.py](src/bot/contexto.py) — `Contexto`, the per-tick shared state. **Owned exclusively by the bot thread.** The dashboard never touches it — it only sees immutable telemetry snapshots. Preserving this ownership rule is what keeps the threading model simple; do not read/mutate `Contexto` from the async side.
- [src/bot/telemetria/barramento.py](src/bot/telemetria/barramento.py) — `BarramentoEventos`, the bounded queue. **Best-effort: drops the oldest event when full** so the bot loop never blocks on the panel. [ponte.py](src/bot/painel/ponte.py) adapts the blocking `queue.get()` to `await` via `run_in_executor`.

### Decision engine — the extension point

Behaviors are evaluated by **priority** (highest first); the **first non-null decision wins the tick** (one action per tick → human-like timing, no hotkey storms). Per-hotkey cooldowns gate actions. Action types (`TipoAcao` in [decisao/tipos.py](src/bot/decisao/tipos.py)): `PRESSIONAR_TECLA`, `CLICAR`, `ARRASTAR` (drag, for item drop — uses `Decisao.ponto`→`ponto_destino`), `NENHUMA`.

- [src/bot/decisao/comportamentos/base.py](src/bot/decisao/comportamentos/base.py) — `ComportamentoBase` protocol: a class with `nome`, `prioridade`, and `avaliar(contexto) -> Decisao | None`.
- [src/bot/decisao/motor.py](src/bot/decisao/motor.py) — `MotorDecisao` sorts behaviors by priority and short-circuits. If the chosen hotkey is on cooldown it returns a `NENHUMA` decision whose `motivo` explains why (surfaced in the panel). The loop calls `confirmar_acao()` **after** executing to register the cooldown.
- Current behaviors & default priorities: `AutoCura` (~100) > `Saque` (~85) > `Alvo` (~80) > `Drop` (~50) > `UsarMana` (~15) > `Comer` (~10). `Saque` sits above `Alvo` so Quick Loot fires right after a kill even with mobs still up. **`Alvo` does NOT gate attacking on `alvo_atual`** (the red-highlight detection conflates the target frame with a wounded creature's reddish HP bar — a false-positive there would stop the bot attacking, e.g. after killing one of several mobs or coming up stairs). Re-targeting is driven by `alvo_engajado_ts` (stamped by the loop on each attack) + battle-list **count drops** (kills via `saque_morte_ts`), with `recompromisso_s` as the missed-click safety net.
- **Every behavior has an `ativo` flag in its config** (`cura.ativo`/`alvo.ativo` included — added so the portal's *Recursos* tab can toggle each feature). `executar.py` only registers the active ones; toggling here is the supported way to disable a feature (e.g. turn off `saque` on a premium account).
- `UsarMana` (Magic-Level training) casts `usar_mana.tecla` while mana ≥ `mana_alto`, with hysteresis down to `mana_alvo`. It's an **idle activity: it yields to combat** (returns nothing while the battle list shows creatures), so it never blocks attacking/looting regardless of its configured priority. **Gotcha:** a full bar rarely reads exactly `100%` (anti-aliased edges + overlaid digits → ~96–99%), so a configured `mana_alto >= 100` is treated as `LIMIAR_CHEIO_INATINGIVEL` (~97%); the default is `95` — set it at/below what a full bar actually reads (the *Usar Mana* tab shows the live mana to help). Its cooldown is keyed by `CHAVE_COOLDOWN` (`"usar_mana"`), not by the hotkey.

**To add a feature:** create a class implementing `ComportamentoBase` under [src/bot/decisao/comportamentos/](src/bot/decisao/comportamentos/), then register it in the `comportamentos` list in [executar.py](executar.py). Behaviors that need cross-tick state use `contexto.estado_comportamentos` (a namespaced scratch dict) — e.g. the loop stamps `saque_morte_ts` / `alvo_engajado_ts` there for `Saque`/`Alvo` to read. Other per-tick reads the loop computes and stores on `Contexto` directly: `criaturas` (battle list) and `itens_inventario` + `ponto_drop` (drop). Some cross-tick bookkeeping is done by the loop itself (e.g. `_rastrear_mortes` runs every tick because the motor short-circuits before low-priority behaviors run).

### Capture — pluggable backends with auto-fallback

[src/bot/captura/fabrica.py](src/bot/captura/fabrica.py) (`criar_capturador`) picks a backend. The rest of the bot only knows the `CapturadorBase` protocol ([base.py](src/bot/captura/base.py)), which returns a `Frame` (BGR `np.ndarray` + the absolute desktop `Regiao` it represents).

`backend: auto` tries **DXGI/bettercam** (Python <3.13 only) → **WGC** (Windows Graphics Capture; reads DX11/DX12/OpenGL, works on 3.13) → **mss** (pure-Python GDI; **cannot read GPU surfaces** — DX12 comes back black). Other backends: `obs` (OBS Virtual Camera, for the official BattlEye client), `tibia_arquivo` (slow screenshot-hotkey fallback). The loop also has a runtime safety net (`_verificar_frames_pretos`): if HP+Mana confidence stays ~0 for 30 ticks it auto-switches to mss (or, on OBS, just warns).

**Black-capture is the #1 operational gotcha.** The official Tibia client (BattlEye) uses `WDA_EXCLUDEFROMCAPTURE`, which makes the Windows compositor blank the window for *every* external capture path → use `backend: obs`. See the README's OBS section for the full setup.

### Vision

- [src/bot/visao/barra_recursos.py](src/bot/visao/barra_recursos.py) — reads bar fill % by classifying **per-column over the full bar height** (not a single mid scanline) in **HSV (brightness + saturation)**, so it survives HP changing color **and the digits overlaid on the bar** (`165/170` — white text is low-saturation, but the bar color above/below the digit keeps the column "filled"; a column counts as filled if ≥`FRACAO_COLUNA` of it is filled). Takes `invertido` for bars that fill **right→left** (Tibia mana empties left→right) — it mirrors the column array before the same contiguous-from-edge logic. Occluded/dirty reads (tooltip covering the bar) yield **low confidence** and are ignored downstream (`visao.confianca_minima`).
- [src/bot/visao/lista_batalha.py](src/bot/visao/lista_batalha.py) — detects creatures in the battle list (mini HP-bars) and whether there's a current target; provides the click point for targeting.
- [src/bot/visao/inventario.py](src/bot/visao/inventario.py) — `detectar_itens` finds registered items in the backpack region via **multi-scale template matching** (`cv2.matchTemplate`, TM_CCOEFF_NORMED, swept over `ESCALAS` ≈ 0.5×–1.5× → robust to client-zoom / icon-size mismatch). Templates are item-icon crops **or uploaded PNG/GIF files** registered in the portal; `decodificar_template` keeps the alpha channel (`IMREAD_UNCHANGED`) and `_normalizar_template` turns it into a **match mask** so transparent backgrounds of external/wiki icons are ignored. Used by the `Drop` behavior.

### OBS coordinate mapping

With `backend: obs`, calibrated regions are in **OBS canvas coordinates**. The targeting click is converted to desktop coordinates at runtime by reading the **live Tibia window client rect** ([src/bot/captura/mapeamento.py](src/bot/captura/mapeamento.py)), so moving the window doesn't require recalibration. See `_configurar_mapeamento_obs` in [loop_bot.py](src/bot/nucleo/loop_bot.py).

### Config, persistence & the portal

- [src/bot/configuracao.py](src/bot/configuracao.py) — pydantic `Config` models. Still the **in-memory single source of truth** (nothing hardcodes coordinates), but no longer loaded from YAML at runtime.
- [src/bot/persistencia/](src/bot/persistencia/) — **config now lives in SQLite** (`config/bot.db`). `repo_perfis.py` does CRUD over **profiles**; each profile stores a whole `Config` as a JSON blob, exactly one is `ativo`. On first run the DB is seeded from the existing `config.yaml` (transparent migration). `executar.py`/`calibrar.py` read/write the **active profile**. YAML survives only as seed + import/export. `Config` (de)serialization helpers: `config_para_dict`/`config_de_dict`.
- [src/bot/painel/api.py](src/bot/painel/api.py) — REST API under `/api` (profiles, config, regions, YAML import/export, one-shot calibration frame via [captura/instantaneo.py](src/bot/captura/instantaneo.py)). [servidor.py](src/bot/painel/servidor.py) mounts it, keeps the `/ws` telemetry/control channel, and serves `portal/dist` (SPA) when built, else the legacy vanilla panel.
- [portal/](portal/) — the web portal (Vite + React + TS + Tailwind v4 + shadcn-style Radix primitives). Pages: Dashboard (live WS; stats incl. abates/curas forte-leve/usos de mana + per-minute rates), Configurações (a **Recursos** tab toggles each feature on/off with dependency hints + "em teste" badges, plus per-section forms; the **Drop** tab registers items by cropping a captured frame **or uploading a PNG/GIF** → PNG base64), Perfis (profiles + import/export), Calibração (draw HP/Mana/battle-list/**inventário**/**drop_tile** rectangles on a captured frame). **TS types in `portal/src/lib/types.ts` mirror the pydantic `Config` (and the telemetry events) — update both sides when adding a field.**
- **Applying config changes requires a bot restart** (deliberate: simpler than live reconfiguration). The portal saves to SQLite; changes take effect on the next `executar.py`. The portal stays up even when uncalibrated so you can calibrate/configure first.
- [src/bot/nucleo/seguranca.py](src/bot/nucleo/seguranca.py) — global hotkeys **F11** (pause/resume) / **F12** (panic, stops input immediately), plus window-focus gating. Focus gates **only the input** (SendInput needs the window focused), not the reading — the panel keeps showing live HP/Mana even when Tibia isn't focused.

## Notes

- Hotkeys must be bound **inside the Tibia client** to match the active profile's config (the bot only presses keys). Auto-loot relies on Tibia's **Quick Loot** + the client's own loot lists — item filtering is not managed by the bot.
- Session stats live in [src/bot/telemetria/estatisticas.py](src/bot/telemetria/estatisticas.py): `registrar_acao` buckets each executed action by `decisao.dados['recurso']` (`hp`→`curas`, split `curas_forte`/`curas_leve` by `dados['nivel']`; `mana`→`pocoes_mana`; `mana_uso`→`usos_mana`; `alvo`→`ataques`; `saque`→`saques`; `comida`→`refeicoes`), and `_rastrear_mortes` bumps `abates` when the battle-list count drops. These count **what the bot did (inputs sent)**, not client-confirmed events — surfaced as such in the dashboard.
- Every behavior is gated by an `ativo` flag (`cura`/`alvo` included). `targeting`/`auto-loot` additionally require the **battle list region calibrated**. **Drop** activates only when `drop.ativo` + `regioes.inventario`/`drop_tile` calibrated + at least one item registered; it drags items to the ground tile (and presses Enter for the stackable "Move how many?" dialog if `confirmar_quantidade`).
- Run as Administrator: required for global hotkeys and for SendInput to reach the (usually elevated) Tibia client.
