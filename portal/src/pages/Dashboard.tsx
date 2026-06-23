import { useEffect, useRef, useState } from "react"
import { Link } from "react-router-dom"
import { Pause, Play, Square, Wifi, WifiOff, AlertTriangle } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useTelemetria } from "@/hooks/useTelemetria"
import { api } from "@/lib/api"
import type { Meta } from "@/lib/types"
import { cn } from "@/lib/utils"

function corEstado(e?: string) {
  if (e === "RODANDO") return "success"
  if (e === "PAUSADO") return "warning"
  if (e === "PARADO" || e === "PANICO") return "destructive"
  return "secondary"
}

function Barra({ rotulo, pct, cor }: { rotulo: string; pct: number | null; cor: string }) {
  const v = pct == null ? 0 : Math.max(0, Math.min(100, pct))
  return (
    <div className="grid gap-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{rotulo}</span>
        <span className="tabular-nums text-muted-foreground">{pct == null ? "—" : `${pct.toFixed(0)}%`}</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${v}%`, backgroundColor: cor }}
        />
      </div>
    </div>
  )
}

function Estatistica({ rotulo, valor, sub }: { rotulo: string; valor: string | number; sub?: string }) {
  return (
    <div className="rounded-lg border border-border bg-background/40 p-3">
      <div className="text-2xl font-semibold tabular-nums">{valor}</div>
      <div className="text-xs text-muted-foreground">{rotulo}</div>
      {sub && <div className="text-[10px] text-muted-foreground/70 tabular-nums">{sub}</div>}
    </div>
  )
}

/** Taxa por minuto formatada (ex.: "3.2/min"), a partir de um total e o uptime em segundos. */
function porMinuto(total: number | undefined, uptime_s: number | undefined): string {
  const n = total ?? 0
  const min = (uptime_s ?? 0) / 60
  if (min < 0.1) return "—"
  return `${(n / min).toFixed(1)}/min`
}

function formatarTempo(s: number) {
  s = Math.floor(s || 0)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ${s % 60}s`
  return `${Math.floor(m / 60)}h ${m % 60}m`
}

export function Dashboard() {
  const t = useTelemetria()
  const [meta, setMeta] = useState<Meta | null>(null)
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {})
  }, [])

  useEffect(() => {
    const el = logRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [t.log])

  const e = t.estado
  const semBot = meta && !meta.bot_rodando && !e
  const naoCalibrado = meta && !meta.perfil_ativo.calibrado

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Perfil ativo: <span className="text-foreground">{meta?.perfil_ativo.nome ?? "—"}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={t.conectado ? "success" : "destructive"}>
            {t.conectado ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
            {t.conectado ? "conectado" : "desconectado"}
          </Badge>
          {e && <Badge variant={corEstado(e.estado_execucao) as any}>{e.estado_execucao}</Badge>}
          {e && (
            <Badge variant={e.janela_focada ? "secondary" : "warning"}>
              foco: {e.janela_focada ? "sim" : "não"}
            </Badge>
          )}
        </div>
      </div>

      {naoCalibrado && (
        <Card className="border-warning/40 bg-warning/5">
          <CardContent className="flex items-center gap-3 py-4 text-sm">
            <AlertTriangle className="h-5 w-5 text-warning" />
            <span>
              Este perfil ainda não foi calibrado.{" "}
              <Link to="/calibracao" className="font-medium text-primary underline-offset-4 hover:underline">
                Calibre as barras de HP/Mana
              </Link>{" "}
              e reinicie o bot.
            </span>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap gap-2">
        <Button onClick={() => t.enviar("retomar")} disabled={!t.conectado}>
          <Play /> Retomar
        </Button>
        <Button variant="secondary" onClick={() => t.enviar("pausar")} disabled={!t.conectado}>
          <Pause /> Pausar
        </Button>
        <Button variant="destructive" onClick={() => t.enviar("parar")} disabled={!t.conectado}>
          <Square /> Parar
        </Button>
      </div>

      {semBot && (
        <Card className="border-border bg-card">
          <CardContent className="py-4 text-sm text-muted-foreground">
            O loop do bot não está rodando (provavelmente sem calibração). O portal continua disponível
            para configurar e calibrar — depois reinicie <code>executar.py</code>.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recursos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Barra rotulo="HP" pct={e?.hp_pct ?? null} cor="var(--hp)" />
            <Barra rotulo="Mana" pct={e?.mana_pct ?? null} cor="var(--mana)" />
            <div className="grid grid-cols-2 gap-3 pt-2 sm:grid-cols-4">
              <Estatistica
                rotulo="abates"
                valor={t.stats?.abates ?? 0}
                sub={porMinuto(t.stats?.abates, t.stats?.uptime_s)}
              />
              <Estatistica
                rotulo="alvos (cliques)"
                valor={t.stats?.ataques ?? 0}
                sub={porMinuto(t.stats?.ataques, t.stats?.uptime_s)}
              />
              <Estatistica
                rotulo="curas"
                valor={t.stats?.curas ?? 0}
                sub={`forte ${t.stats?.curas_forte ?? 0} · leve ${t.stats?.curas_leve ?? 0}`}
              />
              <Estatistica rotulo="saques" valor={t.stats?.saques ?? 0} sub={porMinuto(t.stats?.saques, t.stats?.uptime_s)} />
              <Estatistica rotulo="poções mana" valor={t.stats?.pocoes_mana ?? 0} />
              <Estatistica rotulo="usos mana (treino)" valor={t.stats?.usos_mana ?? 0} />
              <Estatistica rotulo="refeições" valor={t.stats?.refeicoes ?? 0} />
              <Estatistica rotulo="uptime" valor={formatarTempo(t.stats?.uptime_s ?? 0)} />
              <Estatistica rotulo="fps" valor={(e?.fps ?? 0).toFixed(0)} />
              <Estatistica rotulo="tick" valor={e?.tick ?? 0} />
            </div>
            <p className="text-[11px] text-muted-foreground/80">
              Contagens refletem o que o bot <span className="italic">acionou</span> (inputs enviados), não
              confirmação do cliente. "alvos" conta cliques de targeting; "abates" estima quedas na battle list.
            </p>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Decisão atual</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <Info rotulo="Ação" valor={t.decisao?.acao ?? "—"} />
              <Info rotulo="Comportamento" valor={t.decisao?.comportamento ?? "—"} />
              <Info rotulo="Tecla" valor={t.decisao?.tecla?.toUpperCase() ?? "—"} />
              <Info rotulo="Motivo" valor={t.decisao?.motivo ?? "—"} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Detecção</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <Info rotulo="Criaturas" valor={t.deteccao?.criaturas?.n ?? "—"} />
              <Info rotulo="Alvo atual" valor={t.deteccao?.criaturas ? (t.deteccao.criaturas.alvo_atual ? "sim" : "não") : "—"} />
              <Info
                rotulo="Confiança"
                valor={t.deteccao?.criaturas?.confianca != null ? t.deteccao.criaturas.confianca.toFixed(2) : "—"}
              />
              <Info rotulo="Backend" valor={e?.backend_captura ?? "—"} />
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Preview</CardTitle>
          </CardHeader>
          <CardContent>
            {t.quadro ? (
              <img src={t.quadro} alt="preview" className="w-full rounded-md border border-border" />
            ) : (
              <div className="flex h-48 items-center justify-center rounded-md border border-dashed border-border text-sm text-muted-foreground">
                Sem frame ainda
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Raciocínio</CardTitle>
          </CardHeader>
          <CardContent>
            <div ref={logRef} className="h-72 overflow-y-auto rounded-md bg-background/60 p-3 font-mono text-xs">
              {t.log.length === 0 && <div className="text-muted-foreground">Aguardando eventos…</div>}
              {t.log.map((l) => (
                <div
                  key={l.id}
                  className={cn(
                    "py-0.5",
                    l.nivel === "alerta" && "text-warning",
                    l.nivel === "erro" && "text-destructive"
                  )}
                >
                  <span className="mr-2 text-muted-foreground">{l.hora}</span>
                  {l.texto}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function Info({ rotulo, valor }: { rotulo: string; valor: string | number }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-muted-foreground">{rotulo}</span>
      <span className="text-right font-medium">{valor}</span>
    </div>
  )
}
