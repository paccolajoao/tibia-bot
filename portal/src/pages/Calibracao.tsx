import { useEffect, useRef, useState } from "react"
import { Camera, Loader2, Save } from "lucide-react"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api"
import type { FrameCalibracao, Regiao } from "@/lib/types"
import { cn } from "@/lib/utils"

type Alvo = "hp" | "mana" | "battle_list" | "inventario" | "drop_tile"
const ALVOS: { id: Alvo; rotulo: string; cor: string }[] = [
  { id: "hp", rotulo: "Barra de HP", cor: "var(--hp)" },
  { id: "mana", rotulo: "Barra de Mana", cor: "var(--mana)" },
  { id: "battle_list", rotulo: "Battle list (opcional)", cor: "var(--primary)" },
  { id: "inventario", rotulo: "Inventário (drop)", cor: "var(--success)" },
  { id: "drop_tile", rotulo: "Tile de drop", cor: "var(--warning)" },
]
const ORDEM: Alvo[] = ["hp", "mana", "battle_list", "inventario", "drop_tile"]
const REGIOES_ZERO: Record<Alvo, Regiao> = {
  hp: [0, 0, 0, 0],
  mana: [0, 0, 0, 0],
  battle_list: [0, 0, 0, 0],
  inventario: [0, 0, 0, 0],
  drop_tile: [0, 0, 0, 0],
}

interface RetDisplay {
  x: number
  y: number
  w: number
  h: number
}

export function Calibracao() {
  const [frame, setFrame] = useState<FrameCalibracao | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [alvo, setAlvo] = useState<Alvo>("hp")
  const [regioes, setRegioes] = useState<Record<Alvo, Regiao>>(REGIOES_ZERO)
  const [desenho, setDesenho] = useState<RetDisplay | null>(null)
  const inicio = useRef<{ x: number; y: number } | null>(null)
  const imgRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    api
      .getConfig()
      .then((c) =>
        setRegioes({
          hp: c.regioes.hp,
          mana: c.regioes.mana,
          battle_list: c.regioes.battle_list,
          inventario: c.regioes.inventario,
          drop_tile: c.regioes.drop_tile,
        })
      )
      .catch(() => {})
  }, [])

  async function capturar() {
    setCarregando(true)
    try {
      setFrame(await api.capturarFrame())
    } catch (e: any) {
      toast.error("Falha na captura", { description: String(e.message) })
    } finally {
      setCarregando(false)
    }
  }

  function escala() {
    const img = imgRef.current
    if (!img || !frame) return 1
    return img.clientWidth / frame.largura
  }

  // ----- desenho do retângulo (coords relativas à imagem exibida) -----
  function posRelativa(e: React.MouseEvent) {
    const r = imgRef.current!.getBoundingClientRect()
    return { x: e.clientX - r.left, y: e.clientY - r.top }
  }
  function aoPressionar(e: React.MouseEvent) {
    if (!frame) return
    const p = posRelativa(e)
    inicio.current = p
    setDesenho({ x: p.x, y: p.y, w: 0, h: 0 })
  }
  function aoMover(e: React.MouseEvent) {
    if (!inicio.current) return
    const p = posRelativa(e)
    const x = Math.min(p.x, inicio.current.x)
    const y = Math.min(p.y, inicio.current.y)
    setDesenho({ x, y, w: Math.abs(p.x - inicio.current.x), h: Math.abs(p.y - inicio.current.y) })
  }
  function aoSoltar() {
    if (!desenho || !frame || !inicio.current) {
      inicio.current = null
      return
    }
    inicio.current = null
    if (desenho.w < 4 || desenho.h < 4) {
      setDesenho(null)
      return
    }
    const s = escala()
    // display -> nativo -> + origem (coords que o bot usa)
    const l = Math.round(desenho.x / s) + frame.origem_x
    const t = Math.round(desenho.y / s) + frame.origem_y
    const r = Math.round((desenho.x + desenho.w) / s) + frame.origem_x
    const b = Math.round((desenho.y + desenho.h) / s) + frame.origem_y
    setRegioes((prev) => ({ ...prev, [alvo]: [l, t, r, b] as Regiao }))
    setDesenho(null)
    // avança automaticamente para o próximo alvo não-definido
    const prox = ORDEM.find((a) => a !== alvo && regioes[a].every((v) => v === 0))
    if (prox) setAlvo(prox)
  }

  // converte uma região salva (coords do bot) de volta para display
  function retDisplay(reg: Regiao): RetDisplay | null {
    if (!frame || reg.every((v) => v === 0)) return null
    const s = escala()
    return {
      x: (reg[0] - frame.origem_x) * s,
      y: (reg[1] - frame.origem_y) * s,
      w: (reg[2] - reg[0]) * s,
      h: (reg[3] - reg[1]) * s,
    }
  }

  async function salvar() {
    setSalvando(true)
    try {
      const payload: Partial<Record<Alvo, Regiao>> = {}
      ORDEM.forEach((a) => {
        if (!regioes[a].every((v) => v === 0)) payload[a] = regioes[a]
      })
      await api.putRegioes(payload)
      toast.success("Regiões salvas", { description: "Reinicie o bot para aplicar a calibração." })
    } catch (e: any) {
      toast.error("Erro ao salvar", { description: String(e.message) })
    } finally {
      setSalvando(false)
    }
  }

  const temAlgo = ORDEM.some((a) => !regioes[a].every((v) => v === 0))

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Calibração</h1>
          <p className="text-sm text-muted-foreground">
            Capture um frame e arraste um retângulo sobre cada barra. Substitui o <code>calibrar.py</code>.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={capturar} disabled={carregando}>
            {carregando ? <Loader2 className="animate-spin" /> : <Camera />} Capturar frame
          </Button>
          <Button onClick={salvar} disabled={!temAlgo || salvando}>
            {salvando ? <Loader2 className="animate-spin" /> : <Save />} Salvar regiões
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>O que marcar</CardTitle>
          <CardDescription>Selecione o alvo, depois arraste sobre o frame.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {ALVOS.map((a) => {
            const definido = !regioes[a.id].every((v) => v === 0)
            return (
              <button
                key={a.id}
                onClick={() => setAlvo(a.id)}
                className={cn(
                  "flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors",
                  alvo === a.id ? "border-primary bg-primary/10" : "border-border hover:bg-accent"
                )}
              >
                <span className="h-3 w-3 rounded-sm" style={{ backgroundColor: a.cor }} />
                {a.rotulo}
                {definido && <Badge variant="success">✓</Badge>}
              </button>
            )
          })}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4">
          {!frame ? (
            <div className="flex h-80 flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border text-center text-sm text-muted-foreground">
              <Camera className="h-8 w-8" />
              <div>
                Nenhum frame capturado. Deixe o Tibia visível e clique em <b>Capturar frame</b>.
                <br />
                (Tibia oficial com BattlEye exige backend <code>obs</code> com a Virtual Camera ativa.)
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-xs text-muted-foreground">
                {frame.largura}×{frame.altura} · backend {frame.backend} · origem ({frame.origem_x},{" "}
                {frame.origem_y})
              </div>
              <div
                className="relative inline-block max-w-full cursor-crosshair select-none"
                onMouseDown={aoPressionar}
                onMouseMove={aoMover}
                onMouseUp={aoSoltar}
                onMouseLeave={aoSoltar}
              >
                <img
                  ref={imgRef}
                  src={`data:image/jpeg;base64,${frame.jpeg_base64}`}
                  alt="frame"
                  className="block max-w-full rounded-md border border-border"
                  draggable={false}
                />
                {/* regiões já definidas */}
                {ALVOS.map((a) => {
                  const r = retDisplay(regioes[a.id])
                  if (!r) return null
                  return (
                    <div
                      key={a.id}
                      className="pointer-events-none absolute border-2"
                      style={{ left: r.x, top: r.y, width: r.w, height: r.h, borderColor: a.cor }}
                    >
                      <span
                        className="absolute -top-5 left-0 rounded px-1 text-[10px] font-medium text-background"
                        style={{ backgroundColor: a.cor }}
                      >
                        {a.id}
                      </span>
                    </div>
                  )
                })}
                {/* retângulo em desenho */}
                {desenho && (
                  <div
                    className="pointer-events-none absolute border-2 border-dashed bg-white/10"
                    style={{
                      left: desenho.x,
                      top: desenho.y,
                      width: desenho.w,
                      height: desenho.h,
                      borderColor: ALVOS.find((a) => a.id === alvo)!.cor,
                    }}
                  />
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
