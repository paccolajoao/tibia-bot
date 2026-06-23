import { useEffect, useState } from "react"
import { Save, RotateCcw, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { CampoNumero, CampoSelect, CampoSwitch, CampoTecla, CampoTexto } from "@/components/campos"
import { api } from "@/lib/api"
import type { Config, Meta } from "@/lib/types"
import { getIn, setIn } from "@/lib/utils"

function Secao({ titulo, descricao, children }: { titulo: string; descricao?: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{titulo}</CardTitle>
        {descricao && <CardDescription>{descricao}</CardDescription>}
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-2">{children}</CardContent>
    </Card>
  )
}

export function Configuracoes() {
  const [cfg, setCfg] = useState<Config | null>(null)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [sujo, setSujo] = useState(false)
  const [salvando, setSalvando] = useState(false)

  useEffect(() => {
    Promise.all([api.getConfig(), api.meta()])
      .then(([c, m]) => {
        setCfg(c)
        setMeta(m)
      })
      .catch((e) => toast.error("Falha ao carregar", { description: String(e.message) }))
  }, [])

  function set(caminho: string, valor: unknown) {
    setCfg((c) => (c ? setIn(c, caminho, valor) : c))
    setSujo(true)
  }
  const v = (caminho: string) => getIn(cfg, caminho)

  async function salvar() {
    if (!cfg) return
    setSalvando(true)
    try {
      await api.putConfig(cfg)
      setSujo(false)
      toast.success("Configuração salva", { description: "Reinicie o bot para aplicar." })
    } catch (e: any) {
      toast.error("Erro ao salvar", { description: String(e.message) })
    } finally {
      setSalvando(false)
    }
  }

  async function recarregar() {
    try {
      const c = await api.getConfig()
      setCfg(c)
      setSujo(false)
    } catch {
      /* ignore */
    }
  }

  if (!cfg) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Carregando configuração…
      </div>
    )
  }

  const backends = (meta?.backends_captura ?? ["auto", "wgc", "mss", "obs", "tibia_arquivo"]).map((b) => ({
    valor: b,
    rotulo: b,
  }))

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Configurações</h1>
          <p className="text-sm text-muted-foreground">
            Perfil <span className="text-foreground">{meta?.perfil_ativo.nome}</span> — mudanças valem no
            próximo start do bot.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={recarregar} disabled={salvando}>
            <RotateCcw /> Descartar
          </Button>
          <Button onClick={salvar} disabled={!sujo || salvando}>
            {salvando ? <Loader2 className="animate-spin" /> : <Save />} Salvar
          </Button>
        </div>
      </div>

      <Tabs defaultValue="cura">
        <TabsList className="flex w-full flex-wrap justify-start gap-1">
          <TabsTrigger value="cura">Cura</TabsTrigger>
          <TabsTrigger value="alvo">Alvo</TabsTrigger>
          <TabsTrigger value="acoes">Saque & Comer</TabsTrigger>
          <TabsTrigger value="mana">Usar Mana</TabsTrigger>
          <TabsTrigger value="captura">Captura</TabsTrigger>
          <TabsTrigger value="visao">Visão</TabsTrigger>
          <TabsTrigger value="sistema">Sistema</TabsTrigger>
        </TabsList>

        <TabsContent value="cura" className="space-y-6">
          <Secao titulo="Auto-cura" descricao="Limiares de HP/Mana e teclas de cura (prioridade máxima).">
            <CampoNumero label="HP crítico" sufixo="%" valor={v("cura.hp_critico")} onChange={(x) => set("cura.hp_critico", x)} dica="Abaixo disso, cura forte." />
            <CampoNumero label="HP baixo" sufixo="%" valor={v("cura.hp_baixo")} onChange={(x) => set("cura.hp_baixo", x)} dica="Abaixo disso, cura leve." />
            <CampoNumero label="Mana baixa" sufixo="%" valor={v("cura.mana_baixa")} onChange={(x) => set("cura.mana_baixa", x)} dica="Abaixo disso, poção de mana." />
            <CampoTecla label="Tecla cura forte" valor={v("cura.tecla_cura_forte")} onChange={(x) => set("cura.tecla_cura_forte", x)} />
            <CampoTecla label="Tecla cura leve" valor={v("cura.tecla_cura_leve")} onChange={(x) => set("cura.tecla_cura_leve", x)} />
            <CampoTecla label="Tecla poção mana" valor={v("cura.tecla_pocao_mana")} onChange={(x) => set("cura.tecla_pocao_mana", x)} />
          </Secao>
        </TabsContent>

        <TabsContent value="alvo" className="space-y-6">
          <Secao titulo="Targeting" descricao="Requer battle list calibrada. Clica/ataca a criatura mais próxima.">
            <CampoNumero label="Prioridade" valor={v("alvo.prioridade")} onChange={(x) => set("alvo.prioridade", x)} dica="Abaixo da cura (100)." />
            <CampoNumero label="Recompromisso" sufixo="s" step={0.5} valor={v("alvo.recompromisso_s")} onChange={(x) => set("alvo.recompromisso_s", x)} dica="Não troca de alvo por este tempo após atacar." />
            <CampoNumero label="Confiança mínima" step={0.05} min={0} max={1} valor={v("alvo.confianca_minima")} onChange={(x) => set("alvo.confianca_minima", x)} />
            <CampoNumero label="Cooldown atacar" sufixo="s" step={0.5} valor={v("alvo.cooldown_s.atacar")} onChange={(x) => set("alvo.cooldown_s.atacar", x)} />
            <CampoNumero label="Saturação mín. (s_min)" valor={v("alvo.s_min")} onChange={(x) => set("alvo.s_min", x)} />
            <CampoNumero label="Brilho mín. (v_min)" valor={v("alvo.v_min")} onChange={(x) => set("alvo.v_min", x)} />
            <CampoTexto label="Tecla de ataque (opcional)" placeholder="ex.: space (vazio = clique)" valor={v("alvo.tecla") ?? ""} onChange={(x) => set("alvo.tecla", x === "" ? null : x.toLowerCase())} dica="Se definida, usa a hotkey 'Attack Closest' em vez de clicar." />
          </Secao>
        </TabsContent>

        <TabsContent value="acoes" className="space-y-6">
          <Secao titulo="Auto-loot (Quick Loot)" descricao="Dispara a hotkey de saque após cada kill.">
            <CampoSwitch label="Ativo" valor={v("saque.ativo")} onChange={(x) => set("saque.ativo", x)} />
            <CampoTecla label="Tecla de saque" valor={v("saque.tecla")} onChange={(x) => set("saque.tecla", x)} />
            <CampoNumero label="Janela após kill" sufixo="s" step={0.5} valor={v("saque.janela_s")} onChange={(x) => set("saque.janela_s", x)} />
            <CampoNumero label="Intervalo entre presses" sufixo="s" step={0.5} valor={v("saque.intervalo_press_s")} onChange={(x) => set("saque.intervalo_press_s", x)} />
            <CampoNumero label="Prioridade" valor={v("saque.prioridade")} onChange={(x) => set("saque.prioridade", x)} />
          </Secao>
          <Secao titulo="Auto-comer" descricao="Aperta a hotkey de comida periodicamente.">
            <CampoSwitch label="Ativo" valor={v("comer.ativo")} onChange={(x) => set("comer.ativo", x)} />
            <CampoTecla label="Tecla de comida" valor={v("comer.tecla")} onChange={(x) => set("comer.tecla", x)} />
            <CampoNumero label="Intervalo" sufixo="s" step={5} valor={v("comer.intervalo_s")} onChange={(x) => set("comer.intervalo_s", x)} />
            <CampoNumero label="Prioridade" valor={v("comer.prioridade")} onChange={(x) => set("comer.prioridade", x)} />
          </Secao>
        </TabsContent>

        <TabsContent value="mana" className="space-y-6">
          <Secao titulo="Usar Mana (treino)" descricao="Gasta mana apertando uma tecla enquanto a mana estiver alta (histerese).">
            <CampoSwitch label="Ativo" valor={v("usar_mana.ativo")} onChange={(x) => set("usar_mana.ativo", x)} />
            <CampoTecla label="Tecla" valor={v("usar_mana.tecla")} onChange={(x) => set("usar_mana.tecla", x)} />
            <CampoNumero label="Mana alto" sufixo="%" valor={v("usar_mana.mana_alto")} onChange={(x) => set("usar_mana.mana_alto", x)} dica="Acima disso, começa a gastar." />
            <CampoNumero label="Mana alvo" sufixo="%" valor={v("usar_mana.mana_alvo")} onChange={(x) => set("usar_mana.mana_alvo", x)} dica="Para de gastar abaixo disso." />
            <CampoNumero label="Cooldown" sufixo="s" step={0.5} valor={v("usar_mana.cooldown_s")} onChange={(x) => set("usar_mana.cooldown_s", x)} />
            <CampoNumero label="Prioridade" valor={v("usar_mana.prioridade")} onChange={(x) => set("usar_mana.prioridade", x)} />
          </Secao>
        </TabsContent>

        <TabsContent value="captura" className="space-y-6">
          <Secao titulo="Captura de tela" descricao="Tibia oficial (BattlEye) exige backend 'obs'. Veja o README.">
            <CampoSelect label="Backend" valor={v("captura.backend")} onChange={(x) => set("captura.backend", x)} opcoes={backends} />
            <CampoNumero label="Monitor" valor={v("captura.monitor")} onChange={(x) => set("captura.monitor", x)} />
            <CampoNumero label="FPS alvo" step={1} valor={v("captura.fps_alvo")} onChange={(x) => set("captura.fps_alvo", x)} />
            <CampoTexto label="Hotkey screenshot (tibia_arquivo)" valor={v("captura.hotkey_screenshot")} onChange={(x) => set("captura.hotkey_screenshot", x)} />
            <CampoTexto label="Pasta screenshots (tibia_arquivo)" placeholder="vazio = auto-detecta" valor={v("captura.tibia_screenshots")} onChange={(x) => set("captura.tibia_screenshots", x)} />
            <CampoTexto label="Nome do device OBS" valor={v("captura.obs_device_nome")} onChange={(x) => set("captura.obs_device_nome", x)} />
            <CampoNumero label="Índice device OBS" valor={v("captura.obs_device_index")} onChange={(x) => set("captura.obs_device_index", x)} />
            <CampoNumero label="OBS largura" valor={v("captura.obs_largura")} onChange={(x) => set("captura.obs_largura", x)} />
            <CampoNumero label="OBS altura" valor={v("captura.obs_altura")} onChange={(x) => set("captura.obs_altura", x)} />
          </Secao>
        </TabsContent>

        <TabsContent value="visao" className="space-y-6">
          <Secao titulo="Visão" descricao="Classificação dos pixels das barras em HSV (brilho + saturação).">
            <CampoNumero label="Confiança mínima" step={0.05} min={0} max={1} valor={v("visao.confianca_minima")} onChange={(x) => set("visao.confianca_minima", x)} dica="Leituras abaixo disso são ignoradas." />
            <div className="hidden sm:block" />
            <CampoNumero label="HP — brilho mín. (v_min)" valor={v("visao.hp.v_min")} onChange={(x) => set("visao.hp.v_min", x)} />
            <CampoNumero label="HP — saturação mín. (s_min)" valor={v("visao.hp.s_min")} onChange={(x) => set("visao.hp.s_min", x)} />
            <CampoNumero label="Mana — brilho mín. (v_min)" valor={v("visao.mana.v_min")} onChange={(x) => set("visao.mana.v_min", x)} />
            <CampoNumero label="Mana — saturação mín. (s_min)" valor={v("visao.mana.s_min")} onChange={(x) => set("visao.mana.s_min", x)} />
          </Secao>
        </TabsContent>

        <TabsContent value="sistema" className="space-y-6">
          <Secao titulo="Entrada (humanização)" descricao="Atrasos aleatórios antes/depois de cada input (ms).">
            <CampoNumero label="Pré — mín." sufixo="ms" valor={v("entrada.atraso_pre_ms.0")} onChange={(x) => set("entrada.atraso_pre_ms.0", x)} />
            <CampoNumero label="Pré — máx." sufixo="ms" valor={v("entrada.atraso_pre_ms.1")} onChange={(x) => set("entrada.atraso_pre_ms.1", x)} />
            <CampoNumero label="Pós — mín." sufixo="ms" valor={v("entrada.atraso_pos_ms.0")} onChange={(x) => set("entrada.atraso_pos_ms.0", x)} />
            <CampoNumero label="Pós — máx." sufixo="ms" valor={v("entrada.atraso_pos_ms.1")} onChange={(x) => set("entrada.atraso_pos_ms.1", x)} />
          </Secao>
          <Secao titulo="Segurança" descricao="Hotkeys globais e janela-alvo.">
            <CampoTexto label="Hotkey pausar" valor={v("seguranca.hotkey_pausar")} onChange={(x) => set("seguranca.hotkey_pausar", x)} />
            <CampoTexto label="Hotkey pânico" valor={v("seguranca.hotkey_panico")} onChange={(x) => set("seguranca.hotkey_panico", x)} />
            <CampoTexto label="Título da janela contém" valor={v("seguranca.titulo_janela_contains")} onChange={(x) => set("seguranca.titulo_janela_contains", x)} />
          </Secao>
          <Secao titulo="Portal" descricao="Host/porta do servidor web e FPS do preview.">
            <CampoTexto label="Host" valor={v("painel.host")} onChange={(x) => set("painel.host", x)} />
            <CampoNumero label="Porta" valor={v("painel.port")} onChange={(x) => set("painel.port", x)} />
            <CampoNumero label="FPS do preview" step={1} valor={v("painel.fps_quadro")} onChange={(x) => set("painel.fps_quadro", x)} />
          </Secao>
        </TabsContent>
      </Tabs>
    </div>
  )
}
