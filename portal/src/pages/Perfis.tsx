import { useEffect, useRef, useState } from "react"
import { Check, Copy, Download, Pencil, Plus, Trash2, Upload, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { api } from "@/lib/api"
import type { PerfilResumo } from "@/lib/types"

export function Perfis() {
  const [perfis, setPerfis] = useState<PerfilResumo[] | null>(null)
  const [novoNome, setNovoNome] = useState("")
  const [ocupado, setOcupado] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  async function carregar() {
    try {
      setPerfis(await api.listarPerfis())
    } catch (e: any) {
      toast.error("Falha ao listar perfis", { description: String(e.message) })
    }
  }
  useEffect(() => {
    carregar()
  }, [])

  async function acao<T>(fn: () => Promise<T>, ok: string) {
    setOcupado(true)
    try {
      await fn()
      await carregar()
      toast.success(ok)
    } catch (e: any) {
      toast.error("Erro", { description: String(e.message) })
    } finally {
      setOcupado(false)
    }
  }

  async function importarArquivo(file: File) {
    const texto = await file.text()
    const nome = file.name.replace(/\.(ya?ml)$/i, "") || "Importado"
    await acao(() => api.importarYaml(nome, texto), "Perfil importado")
  }

  if (!perfis) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Carregando perfis…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Perfis</h1>
          <p className="text-sm text-muted-foreground">
            Conjuntos de configuração independentes (ex.: por personagem ou caçada).
          </p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".yaml,.yml"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) importarArquivo(f)
              e.target.value = ""
            }}
          />
          <Button variant="outline" onClick={() => fileRef.current?.click()} disabled={ocupado}>
            <Upload /> Importar YAML
          </Button>
          <Dialog>
            <DialogTrigger asChild>
              <Button disabled={ocupado}>
                <Plus /> Novo perfil
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Novo perfil</DialogTitle>
                <DialogDescription>Começa a partir dos valores padrão.</DialogDescription>
              </DialogHeader>
              <div className="grid gap-2">
                <Label>Nome</Label>
                <Input value={novoNome} onChange={(e) => setNovoNome(e.target.value)} placeholder="ex.: Knight cacar" />
              </div>
              <DialogFooter>
                <DialogClose asChild>
                  <Button variant="outline">Cancelar</Button>
                </DialogClose>
                <DialogClose asChild>
                  <Button
                    onClick={() => {
                      if (novoNome.trim()) acao(() => api.criarPerfil(novoNome.trim()), "Perfil criado")
                      setNovoNome("")
                    }}
                  >
                    Criar
                  </Button>
                </DialogClose>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="grid gap-3">
        {perfis.map((p) => (
          <LinhaPerfil key={p.id} perfil={p} ocupado={ocupado} acao={acao} />
        ))}
      </div>
    </div>
  )
}

function LinhaPerfil({
  perfil,
  ocupado,
  acao,
}: {
  perfil: PerfilResumo
  ocupado: boolean
  acao: <T>(fn: () => Promise<T>, ok: string) => Promise<void>
}) {
  const [nome, setNome] = useState(perfil.nome)

  return (
    <Card className={perfil.ativo ? "border-primary/50" : undefined}>
      <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium">{perfil.nome}</span>
              {perfil.ativo && <Badge variant="success">ativo</Badge>}
              {perfil.calibrado ? (
                <Badge variant="secondary">calibrado</Badge>
              ) : (
                <Badge variant="warning">sem calibração</Badge>
              )}
              {perfil.battle_list_calibrado && <Badge variant="secondary">battle list</Badge>}
            </div>
            <div className="text-xs text-muted-foreground">
              atualizado em {new Date(perfil.atualizado_em).toLocaleString()}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {!perfil.ativo && (
            <Button size="sm" onClick={() => acao(() => api.ativarPerfil(perfil.id), "Perfil ativado")} disabled={ocupado}>
              <Check /> Ativar
            </Button>
          )}
          <Button size="sm" variant="outline" asChild>
            <a href={api.exportUrl(perfil.id)} download>
              <Download /> Exportar
            </a>
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => acao(() => api.duplicarPerfil(perfil.id, `${perfil.nome} (cópia)`), "Perfil duplicado")}
            disabled={ocupado}
          >
            <Copy /> Duplicar
          </Button>

          <Dialog>
            <DialogTrigger asChild>
              <Button size="sm" variant="outline">
                <Pencil /> Renomear
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Renomear perfil</DialogTitle>
              </DialogHeader>
              <Input value={nome} onChange={(e) => setNome(e.target.value)} />
              <DialogFooter>
                <DialogClose asChild>
                  <Button variant="outline">Cancelar</Button>
                </DialogClose>
                <DialogClose asChild>
                  <Button onClick={() => acao(() => api.renomearPerfil(perfil.id, nome.trim()), "Renomeado")}>
                    Salvar
                  </Button>
                </DialogClose>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          <Dialog>
            <DialogTrigger asChild>
              <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive">
                <Trash2 />
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Excluir “{perfil.nome}”?</DialogTitle>
                <DialogDescription>Esta ação não pode ser desfeita.</DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <DialogClose asChild>
                  <Button variant="outline">Cancelar</Button>
                </DialogClose>
                <DialogClose asChild>
                  <Button
                    variant="destructive"
                    onClick={() => acao(() => api.excluirPerfil(perfil.id), "Perfil excluído")}
                  >
                    Excluir
                  </Button>
                </DialogClose>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </CardContent>
    </Card>
  )
}
