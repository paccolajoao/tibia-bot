import { useRef, useState } from "react"
import { ArrowDown, ArrowUp, Camera, Loader2, Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { CampoNumero, CampoSelect, CampoSwitch, CampoTecla } from "@/components/campos"
import { api } from "@/lib/api"
import type { FrameCalibracao, Waypoint, WaypointTipo } from "@/lib/types"

const TIPOS: { valor: WaypointTipo; rotulo: string }[] = [
  { valor: "ir", rotulo: "Ir (clicar no minimapa)" },
  { valor: "andar_em", rotulo: "Pisar no tile (escada/buraco)" },
  { valor: "usar", rotulo: "Usar (clique-direito: escada/alavanca)" },
  { valor: "tecla", rotulo: "Tecla (corda/pá bindada)" },
  { valor: "esperar", rotulo: "Esperar (pausa)" },
]
const ROTULO_TIPO: Record<WaypointTipo, string> = {
  ir: "ir",
  andar_em: "pisar",
  usar: "usar",
  tecla: "tecla",
  esperar: "esperar",
}
// tipos que precisam de um ponto na tela (clicar no frame para gravar)
const TIPOS_PONTO: WaypointTipo[] = ["ir", "andar_em", "usar"]
// tipos que PODEM mudar de andar (escada/buraco/corda/pá) — habilitam a validação
const TIPOS_TROCA: WaypointTipo[] = ["andar_em", "usar", "tecla"]

/** Lista ordenada de waypoints do cavebot + diálogo para gravar um novo (clicando no frame). */
export function Waypoints({
  waypoints,
  onChange,
}: {
  waypoints: Waypoint[]
  onChange: (wps: Waypoint[]) => void
}) {
  const [aberto, setAberto] = useState(false)

  function remover(i: number) {
    onChange(waypoints.filter((_, idx) => idx !== i))
  }
  function mover(de: number, para: number) {
    if (para < 0 || para >= waypoints.length) return
    const copia = [...waypoints]
    const [item] = copia.splice(de, 1)
    copia.splice(para, 0, item)
    onChange(copia)
  }
  function adicionar(wp: Waypoint) {
    onChange([...waypoints, wp])
    setAberto(false)
  }

  return (
    <div className="space-y-3 sm:col-span-2">
      <div className="flex items-center justify-between">
        <Label>Rota (waypoints, em ordem)</Label>
        <Dialog open={aberto} onOpenChange={setAberto}>
          <DialogTrigger asChild>
            <Button size="sm" variant="outline">
              <Plus /> Gravar waypoint
            </Button>
          </DialogTrigger>
          <GravarWaypoint onAdicionar={adicionar} />
        </Dialog>
      </div>

      {waypoints.length === 0 ? (
        <p className="rounded-md border border-dashed border-border p-4 text-center text-sm text-muted-foreground">
          Nenhum waypoint. Clique em "Gravar waypoint" e aponte no minimapa (a rota repete em loop).
        </p>
      ) : (
        <div className="grid gap-2">
          {waypoints.map((wp, i) => (
            <div key={i} className="flex items-center gap-2 rounded-md border border-border bg-background/40 p-2">
              <span className="w-6 text-center text-xs font-bold tabular-nums text-muted-foreground">{i + 1}</span>
              <Badge variant="secondary">{ROTULO_TIPO[wp.tipo]}</Badge>
              {wp.troca_andar && <Badge variant="warning">andar</Badge>}
              <span className="flex-1 truncate text-sm">
                {wp.nome || "(sem nome)"}
                {TIPOS_PONTO.includes(wp.tipo) && (
                  <span className="ml-2 text-xs text-muted-foreground tabular-nums">
                    ({wp.x}, {wp.y})
                  </span>
                )}
                {wp.tipo === "tecla" && <span className="ml-2 text-xs text-muted-foreground">[{wp.tecla}]</span>}
                {wp.tipo === "esperar" && <span className="ml-2 text-xs text-muted-foreground">{wp.dwell_s}s</span>}
              </span>
              <Button size="icon" variant="ghost" onClick={() => mover(i, i - 1)} disabled={i === 0}>
                <ArrowUp />
              </Button>
              <Button size="icon" variant="ghost" onClick={() => mover(i, i + 1)} disabled={i === waypoints.length - 1}>
                <ArrowDown />
              </Button>
              <Button size="icon" variant="ghost" className="text-destructive" onClick={() => remover(i)}>
                <Trash2 />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/** Diálogo: grava um waypoint. Para tipos com ponto, captura um frame e o usuário CLICA o alvo. */
function GravarWaypoint({ onAdicionar }: { onAdicionar: (wp: Waypoint) => void }) {
  const [tipo, setTipo] = useState<WaypointTipo>("ir")
  const [nome, setNome] = useState("")
  const [tecla, setTecla] = useState("f9")
  const [dwell, setDwell] = useState(1.5)
  const [trocaAndar, setTrocaAndar] = useState(false)
  const [frame, setFrame] = useState<FrameCalibracao | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [ponto, setPonto] = useState<{ x: number; y: number } | null>(null) // coords de frame
  const [marcador, setMarcador] = useState<{ x: number; y: number } | null>(null) // coords de display
  const imgRef = useRef<HTMLImageElement>(null)

  const precisaPonto = TIPOS_PONTO.includes(tipo)
  const podeTrocarAndar = TIPOS_TROCA.includes(tipo)

  async function capturar() {
    setCarregando(true)
    try {
      setFrame(await api.capturarFrame())
      setPonto(null)
      setMarcador(null)
    } catch (e: any) {
      toast.error("Falha na captura", { description: String(e.message) })
    } finally {
      setCarregando(false)
    }
  }

  function aoClicar(e: React.MouseEvent) {
    const img = imgRef.current
    if (!img || !frame) return
    const r = img.getBoundingClientRect()
    const escala = img.naturalWidth / img.clientWidth // display -> pixels nativos do frame
    const dx = e.clientX - r.left
    const dy = e.clientY - r.top
    setMarcador({ x: dx, y: dy })
    setPonto({
      x: Math.round(dx * escala) + frame.origem_x,
      y: Math.round(dy * escala) + frame.origem_y,
    })
  }

  function confirmar() {
    if (precisaPonto && !ponto) {
      toast.error("Capture um frame e clique no alvo do waypoint.")
      return
    }
    if (tipo === "tecla" && !tecla.trim()) {
      toast.error("Informe a tecla (hotkey bindada no Tibia).")
      return
    }
    onAdicionar({
      tipo,
      nome: nome.trim(),
      x: ponto?.x ?? 0,
      y: ponto?.y ?? 0,
      tecla: tipo === "tecla" ? tecla.trim() : null,
      dwell_s: dwell,
      troca_andar: podeTrocarAndar && trocaAndar,
    })
  }

  return (
    <DialogContent className="max-w-3xl">
      <DialogHeader>
        <DialogTitle>Gravar waypoint</DialogTitle>
        <DialogDescription>
          <span className="font-medium">Ir</span>: clique no minimapa (o Tibia anda o trecho; a chegada é
          detectada quando o minimapa para de rolar). <span className="font-medium">Pisar/Usar</span>: clique no
          tile/objeto no game-world para trocar de andar. <span className="font-medium">Tecla</span>: dispara uma
          hotkey (ex.: corda/pá).
        </DialogDescription>
      </DialogHeader>

      <div className="grid gap-4 sm:grid-cols-2">
        <CampoSelect label="Tipo" valor={tipo} onChange={(x) => setTipo(x as WaypointTipo)} opcoes={TIPOS} />
        <div className="grid gap-1">
          <Label>Nome (opcional)</Label>
          <Input placeholder="ex.: entrada da cave" value={nome} onChange={(e) => setNome(e.target.value)} />
        </div>
        {tipo === "tecla" && <CampoTecla label="Tecla" valor={tecla} onChange={setTecla} />}
        {tipo !== "ir" && (
          <CampoNumero
            label="Espera (dwell)"
            sufixo="s"
            step={0.5}
            min={0}
            valor={dwell}
            onChange={setDwell}
            dica="Tempo de espera após executar (assentar troca de andar)."
          />
        )}
        {podeTrocarAndar && (
          <CampoSwitch
            label="Muda de andar (validar)"
            dica="Escada/buraco/corda/pá: o bot confirma a troca pelo minimapa e re-tenta se falhar (não trava)."
            valor={trocaAndar}
            onChange={setTrocaAndar}
          />
        )}
      </div>

      {precisaPonto && (
        <>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={capturar} disabled={carregando}>
              {carregando ? <Loader2 className="animate-spin" /> : <Camera />} Capturar frame
            </Button>
            <span className="text-xs text-muted-foreground">
              {tipo === "ir" ? "Clique no MINIMAPA onde o bot deve ir." : "Clique no TILE/objeto no game-world."}
            </span>
          </div>
          {frame && (
            <div className="relative inline-block max-h-[50vh] cursor-crosshair select-none overflow-auto" onClick={aoClicar}>
              <img
                ref={imgRef}
                src={`data:image/jpeg;base64,${frame.jpeg_base64}`}
                alt="frame"
                className="block max-w-full rounded-md border border-border"
                draggable={false}
              />
              {marcador && (
                <div
                  className="pointer-events-none absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--destructive)] bg-white/40"
                  style={{ left: marcador.x, top: marcador.y }}
                />
              )}
            </div>
          )}
          {ponto && (
            <p className="text-xs text-muted-foreground tabular-nums">
              Ponto: ({ponto.x}, {ponto.y})
            </p>
          )}
        </>
      )}

      <DialogFooter>
        <Button onClick={confirmar} disabled={precisaPonto && !ponto}>
          Adicionar waypoint
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}
