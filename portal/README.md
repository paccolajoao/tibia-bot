# Portal — Bot Tibia

Frontend do portal de controle/configuração do bot. **Vite + React + TypeScript +
Tailwind v4 + primitivos no estilo shadcn/ui** (Radix). Todo o português, igual ao resto do
projeto.

## Scripts

```bash
npm install          # instala deps (Node 18+)
npm run dev          # dev server na 5173 (proxy /api e /ws -> FastAPI 8000)
npm run build        # gera dist/ (servido pelo FastAPI em produção)
npm run lint         # checagem de tipos (tsc --noEmit)
```

## Como conversa com o backend

- **REST** sob `/api` (ver [src/lib/api.ts](src/lib/api.ts)) — perfis, config, regiões,
  import/export YAML, calibração. Implementado em `src/bot/painel/api.py`.
- **WebSocket** `/ws` (ver [src/hooks/useTelemetria.ts](src/hooks/useTelemetria.ts)) —
  telemetria ao vivo (estado, decisão, stats, detecção, preview, raciocínio) e canal de
  controle (pausar/retomar/parar).

Em **dev**, o Vite faz proxy de `/api` e `/ws` para o FastAPI (`vite.config.ts`), então rode
o `executar.py` em paralelo. Em **produção**, `npm run build` e o FastAPI serve o `dist/`.

## Estrutura

```
src/
  pages/        Dashboard · Configuracoes · Perfis · Calibracao
  components/
    ui/         primitivos shadcn (button, card, input, select, dialog, tabs, switch, ...)
    campos.tsx  campos de formulário reutilizáveis (CampoNumero, CampoTexto, ...)
  hooks/        useTelemetria (WebSocket)
  lib/          api (cliente REST) · types (espelha o Config pydantic) · utils
```

> Os tipos em `src/lib/types.ts` espelham os modelos pydantic de
> `src/bot/configuracao.py`. Ao adicionar um campo no `Config`, atualize os dois lados.
