import { useRef, useState } from "react"
import { Camera, Loader2, Plus, Trash2, Upload } from "lucide-react"
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

/** Conteúdo do diálogo: gera o template PNG base64 de duas formas —
 *  (a) capturando um frame e recortando o ícone, ou (b) enviando um PNG/GIF do item. */
function CapturarItem({ onAdicionar }: { onAdicionar: (item: ItemDrop) => void }) {
  const [imgSrc, setImgSrc] = useState<string | null>(null) // data URL exibida/recortada
  const [origem, setOrigem] = useState<"frame" | "arquivo" | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [nome, setNome] = useState("")
  const [ret, setRet] = useState<Ret | null>(null)
  const inicio = useRef<{ x: number; y: number } | null>(null)
  const imgRef = useRef<HTMLImageElement>(null)
  const arquivoRef = useRef<HTMLInputElement>(null)

  async function capturar() {
    setCarregando(true)
    try {
      const f: FrameCalibracao = await api.capturarFrame()
      setImgSrc(`data:image/jpeg;base64,${f.jpeg_base64}`)
      setOrigem("frame")
      setRet(null)
    } catch (e: any) {
      toast.error("Falha na captura", { description: String(e.message) })
    } finally {
      setCarregando(false)
    }
  }

  function aoSelecionarArquivo(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = "" // permite reescolher o mesmo arquivo depois
    if (!file) return
    const leitor = new FileReader()
    leitor.onload = () => {
      setImgSrc(String(leitor.result))
      setOrigem("arquivo")
      setRet(null)
      if (!nome.trim()) setNome(file.name.replace(/\.[^.]+$/, "")) // sugere nome pelo arquivo
    }
    leitor.onerror = () => toast.error("Não consegui ler o arquivo.")
    leitor.readAsDataURL(file)
  }

  function pos(e: React.MouseEvent) {
    const r = imgRef.current!.getBoundingClientRect()
    return { x: e.clientX - r.left, y: e.clientY - r.top }
  }
  function down(e: React.MouseEvent) {
    if (!imgSrc) return
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
    if (!img || !imgSrc) return
    const temRecorte = ret != null && ret.w >= 4 && ret.h >= 4
    // frame inteiro não serve de template -> exige recorte; arquivo pode ir inteiro.
    if (!temRecorte && origem === "frame") {
      toast.error("Recorte um retângulo sobre o ícone do item.")
      return
    }
    const escala = img.naturalWidth / img.clientWidth // display -> pixels nativos
    const sx = temRecorte ? Math.round(ret!.x * escala) : 0
    const sy = temRecorte ? Math.round(ret!.y * escala) : 0
    const sw = temRecorte ? Math.round(ret!.w * escala) : img.naturalWidth
    const sh = temRecorte ? Math.round(ret!.h * escala) : img.naturalHeight
    const canvas = document.createElement("canvas")
    canvas.width = sw
    canvas.height = sh
    const ctx = canvas.getContext("2d")!
    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh) // GIF: 1º frame; PNG/GIF preserva alfa
    const b64 = canvas.toDataURL("image/png").split(",")[1]
    onAdicionar({ nome: nome.trim() || "item", template_b64: b64 })
  }

  return (
    <DialogContent className="max-w-3xl">
      <DialogHeader>
        <DialogTitle>Cadastrar item para drop</DialogTitle>
        <DialogDescription>
          Recorte o ícone de um frame capturado <span className="font-medium">ou</span> envie um PNG/GIF do
          item. O resultado vira o template que o bot procura no inventário (o reconhecimento é multi-escala,
          então ícones de tamanho diferente ainda casam).
        </DialogDescription>
      </DialogHeader>

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={capturar} disabled={carregando}>
          {carregando ? <Loader2 className="animate-spin" /> : <Camera />} Capturar frame
        </Button>
        <Button variant="outline" size="sm" onClick={() => arquivoRef.current?.click()}>
          <Upload /> Enviar PNG/GIF
        </Button>
        <input
          ref={arquivoRef}
          type="file"
          accept="image/png,image/gif"
          className="hidden"
          onChange={aoSelecionarArquivo}
        />
        <div className="grid min-w-[12rem] flex-1 gap-1">
          <Input placeholder="Nome do item (ex.: empty potion flask)" value={nome} onChange={(e) => setNome(e.target.value)} />
        </div>
      </div>

      {imgSrc && (
        <>
          <p className="text-xs text-muted-foreground">
            {origem === "frame"
              ? "Arraste para recortar o ícone do item na backpack."
              : "Arraste para recortar (opcional) — sem recorte, a imagem inteira vira o template."}
          </p>
          <div
            className="relative inline-block max-h-[50vh] cursor-crosshair select-none overflow-auto"
            onMouseDown={down}
            onMouseMove={move}
            onMouseUp={up}
            onMouseLeave={up}
          >
            <img
              ref={imgRef}
              src={imgSrc}
              alt="origem"
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
        </>
      )}

      <DialogFooter>
        <Button onClick={confirmar} disabled={!imgSrc || (origem === "frame" && !ret)}>
          Adicionar
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}
