import { useState } from "react"
import { CheckCircle2, Loader2, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api"
import type { ArduinoConfig, EtapaTesteArduino, TesteArduinoResultado } from "@/lib/types"

const ROTULOS: Record<EtapaTesteArduino["nome"], string> = {
  conectar: "Conectar (abrir a porta + aguardar o board)",
  ping: "Ping (round-trip, não toca em teclado/mouse)",
  teclado: "Teclado (aperta Caps Lock — reversível)",
  mouse_movimento: "Mouse — movimento (sem clicar)",
  mouse_clique: "Mouse — clique real",
}

function LinhaEtapa({ etapa }: { etapa: EtapaTesteArduino }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-md border border-border bg-background/40 px-3 py-2">
      <div className="flex items-start gap-2">
        {etapa.ok ? (
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
        ) : (
          <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
        )}
        <div className="grid gap-0.5">
          <span className="text-sm">{ROTULOS[etapa.nome] ?? etapa.nome}</span>
          {etapa.detalhe && <span className="text-xs text-muted-foreground">{etapa.detalhe}</span>}
        </div>
      </div>
      {etapa.latencia_ms != null && (
        <span className="shrink-0 text-xs tabular-nums text-muted-foreground">{etapa.latencia_ms.toFixed(1)} ms</span>
      )}
    </div>
  )
}

/** Painel de teste rápido do board Arduino — usa a config COMO DIGITADA (não precisa salvar antes). */
export function TesteArduino({ arduino }: { arduino: ArduinoConfig }) {
  const [testando, setTestando] = useState(false)
  const [resultado, setResultado] = useState<TesteArduinoResultado | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [testarClique, setTestarClique] = useState(false)
  const [x, setX] = useState(960)
  const [y, setY] = useState(540)

  async function testar() {
    setTestando(true)
    setErro(null)
    try {
      const r = await api.testarArduino({
        porta: arduino.porta,
        baud_rate: arduino.baud_rate,
        timeout_s: arduino.timeout_s,
        largura_tela: arduino.largura_tela,
        altura_tela: arduino.altura_tela,
        testar_clique: testarClique,
        ponto_clique: testarClique ? [x, y] : null,
      })
      setResultado(r)
      if (r.largura_usada > 0 && r.altura_usada > 0) {
        setX(Math.round(r.largura_usada / 2))
        setY(Math.round(r.altura_usada / 2))
      }
    } catch (e: any) {
      setErro(String(e.message))
      setResultado(null)
    } finally {
      setTestando(false)
    }
  }

  return (
    <div className="grid gap-3">
      <div className="flex items-start justify-between gap-4 rounded-lg border border-border bg-background/40 p-4">
        <div className="grid gap-1">
          <span className="font-medium">Testar clique real do mouse</span>
          <p className="text-sm text-muted-foreground">
            As outras etapas são seguras (não digitam texto nem clicam em nada). Esta clica DE VERDADE no
            ponto abaixo — escolha um lugar vazio da tela antes de ligar.
          </p>
          {testarClique && (
            <div className="mt-1 flex items-center gap-2">
              <Label className="text-xs">X</Label>
              <Input
                type="number"
                className="h-8 w-24"
                value={x}
                onChange={(e) => setX(Number(e.target.value))}
              />
              <Label className="text-xs">Y</Label>
              <Input
                type="number"
                className="h-8 w-24"
                value={y}
                onChange={(e) => setY(Number(e.target.value))}
              />
            </div>
          )}
        </div>
        <Switch checked={testarClique} onCheckedChange={setTestarClique} />
      </div>

      <Button onClick={testar} disabled={testando || !arduino.porta.trim()} className="w-fit">
        {testando ? <Loader2 className="animate-spin" /> : null}
        {testando ? "Testando…" : "Testar conexão"}
      </Button>
      {!arduino.porta.trim() && (
        <p className="text-xs text-muted-foreground">Preencha a porta serial acima antes de testar.</p>
      )}

      {erro && <p className="text-sm text-destructive">{erro}</p>}

      {resultado && (
        <div className="grid gap-2">
          <div className="flex items-center gap-2">
            {resultado.sucesso ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            ) : (
              <XCircle className="h-4 w-4 text-destructive" />
            )}
            <span className="text-sm font-medium">
              {resultado.sucesso ? "Tudo funcionando" : "Alguma etapa falhou — veja os detalhes abaixo"}
            </span>
          </div>
          {resultado.largura_usada > 0 && (
            <p className="text-xs text-muted-foreground">
              Resolução usada para escalar o mouse: {resultado.largura_usada}×{resultado.altura_usada}
              {arduino.largura_tela <= 0 ? " (auto-detectada — monitor primário)" : ""}
            </p>
          )}
          <div className="grid gap-1.5">
            {resultado.etapas.map((etapa) => (
              <LinhaEtapa key={etapa.nome} etapa={etapa} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
