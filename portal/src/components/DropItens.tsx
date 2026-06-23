import { useRef, useState } from "react"
import { Camera, Loader2, Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { api } from "@/lib/api"
import type { FrameCalibracao, ItemDrop } from "@/lib/types"

interface Ret {
  x: number
  y: number
  w: number
  h: number
}

/** Lista de itens de drop + diálogo para cadastrar um item recortando seu ícone do frame. */
export function DropItens({
  itens,
  onChange,
}: {
  itens: ItemDrop[]
  onChange: (itens: ItemDrop[]) => void
}) {
  const [aberto, setAberto] = useState(false)

  function remover(i: number) {
    onChange(itens.filter((_, idx) => idx !== i))
  }

  function adicionar(item: ItemDrop) {
    onChange([...itens, item])
    setAberto(false)
  }

  return (
    <div className="space-y-3 sm:col-span-2">
      <div className="flex items-center justify-between">
        <Label>Itens a dropar</Label>
        <Dialog open={aberto} onOpenChange={setAberto}>
          <DialogTrigger asChild>
            <Button size="sm" variant="outline">
              <Plus /> Adicionar item
            </Button>
          </DialogTrigger>
          <CapturarItem onAdicionar={adicionar} />
        </Dialog>
      </div>

      {itens.length === 0 ? (
        <p className="rounded-md border border-dashed border-border p-4 text-center text-sm text-muted-foreground">
          Nenhum item cadastrado. Clique em "Adicionar item" e recorte o ícone na backpack.
        </p>
      ) : (
        <div className="grid gap-2">
          {itens.map((it, i) => (
            <div key={i} className="flex items-center gap-3 rounded-md border border-border bg-background/40 p-2">
              <img
                src={`data:image/png;base64,${it.template_b64}`}
                alt={it.nome}
                className="h-10 w-10 rounded border border-border object-contain"
              />
              <span className="flex-1 text-sm font-medium">{it.nome || "(sem nome)"}</span>
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

/** Conteúdo do diálogo: captura um frame, recorta um retângulo e gera o template PNG base64. */
function CapturarItem({ onAdicionar }: { onAdicionar: (item: ItemDrop) => void }) {
  const [frame, setFrame] = useState<FrameCalibracao | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [nome, setNome] = useState("")
  const [ret, setRet] = useState<Ret | null>(null)
  const inicio = useRef<{ x: number; y: number } | null>(null)
  const imgRef = useRef<HTMLImageElement>(null)

  async function capturar() {
    setCarregando(true)
    try {
      setFrame(await api.capturarFrame())
      setRet(null)
    } catch (e: any) {
      toast.error("Falha na captura", { description: String(e.message) })
    } finally {
      setCarregando(false)
    }
  }

  function pos(e: React.MouseEvent) {
    const r = imgRef.current!.getBoundingClientRect()
    return { x: e.clientX - r.left, y: e.clientY - r.top }
  }
  function down(e: React.MouseEvent) {
    if (!frame) return
    inicio.current = pos(e)
    setRet({ ...inicio.current, w: 0, h: 0 })
  }
  function move(e: React.MouseEvent) {
    if (!inicio.current) return
    const p = pos(e)
    setRet({
      x: Math.min(p.x, inicio.current.x),
      y: Math.min(p.y, inicio.current.y),
      w: Math.abs(p.x - inicio.current.x),
      h: Math.abs(p.y - inicio.current.y),
    })
  }
  function up() {
    inicio.current = null
  }

  function confirmar() {
    const img = imgRef.current
    if (!img || !frame || !ret || ret.w < 4 || ret.h < 4) {
      toast.error("Recorte um retângulo sobre o ícone do item.")
      return
    }
    const escala = img.naturalWidth / img.clientWidth // display -> pixels nativos do frame
    const sx = Math.round(ret.x * escala)
    const sy = Math.round(ret.y * escala)
    const sw = Math.round(ret.w * escala)
    const sh = Math.round(ret.h * escala)
    const canvas = document.createElement("canvas")
    canvas.width = sw
    canvas.height = sh
    const ctx = canvas.getContext("2d")!
    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh)
    const b64 = canvas.toDataURL("image/png").split(",")[1]
    onAdicionar({ nome: nome.trim() || "item", template_b64: b64 })
  }

  return (
    <DialogContent className="max-w-3xl">
      <DialogHeader>
        <DialogTitle>Cadastrar item para drop</DialogTitle>
        <DialogDescription>
          Capture um frame com a backpack aberta e recorte o ícone do item. O recorte vira o
          template que o bot procura no inventário.
        </DialogDescription>
      </DialogHeader>

      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={capturar} disabled={carregando}>
          {carregando ? <Loader2 className="animate-spin" /> : <Camera />} Capturar frame
        </Button>
        <div className="grid flex-1 gap-1">
          <Input placeholder="Nome do item (ex.: empty potion flask)" value={nome} onChange={(e) => setNome(e.target.value)} />
        </div>
      </div>

      {frame && (
        <div
          className="relative inline-block max-h-[50vh] cursor-crosshair select-none overflow-auto"
          onMouseDown={down}
          onMouseMove={move}
          onMouseUp={up}
          onMouseLeave={up}
        >
          <img
            ref={imgRef}
            src={`data:image/jpeg;base64,${frame.jpeg_base64}`}
            alt="frame"
            className="block max-w-full rounded-md border border-border"
            draggable={false}
          />
          {ret && (
            <div
              className="pointer-events-none absolute border-2 border-dashed border-[var(--success)] bg-white/10"
              style={{ left: ret.x, top: ret.y, width: ret.w, height: ret.h }}
            />
          )}
        </div>
      )}

      <DialogFooter>
        <Button onClick={confirmar} disabled={!frame || !ret}>
          Adicionar
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}
