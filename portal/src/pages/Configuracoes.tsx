import { useEffect, useState } from "react"
import { Save, RotateCcw, Loader2, AlertTriangle } from "lucide-react"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { CampoNumero, CampoSelect, CampoSwitch, CampoTecla, CampoTexto } from "@/components/campos"
import { DropItens } from "@/components/DropItens"
import { Waypoints } from "@/components/Waypoints"
import { useTelemetria } from "@/hooks/useTelemetria"
import { api } from "@/lib/api"
import type { Config, ItemDrop, Meta, Regiao, Waypoint } from "@/lib/types"
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

/** Linha da aba Recursos: liga/desliga uma feature com descrição, selo "em teste" e alerta de dependência. */
function LinhaRecurso({
  titulo,
  descricao,
  ativo,
  onChange,
  emTeste,
  alerta,
}: {
  titulo: string
  descricao: string
  ativo: boolean
  onChange: (v: boolean) => void
  emTeste?: boolean
  alerta?: string
}) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-lg border border-border bg-background/40 p-4">
      <div className="grid gap-1">
        <div className="flex items-center gap-2">
          <span className="font-medium">{titulo}</span>
          {emTeste && <Badge variant="warning">em teste</Badge>}
        </div>
        <p className="text-sm text-muted-foreground">{descricao}</p>
        {ativo && alerta && (
          <p className="flex items-center gap-1.5 text-xs text-warning">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" /> {alerta}
          </p>
        )}
      </div>
      <Switch checked={ativo} onCheckedChange={onChange} />
    </div>
  )
}

const regiaoCalibrada = (r: Regiao | undefined) => Array.isArray(r) && r.some((n) => n !== 0)

export function Configuracoes() {
  const [cfg, setCfg] = useState<Config | null>(null)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [sujo, setSujo] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const tele = useTelemetria() // mana ao vivo p/ ajudar a calibrar o limiar do "usar mana"

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

  // dependências de calibração p/ os alertas da aba Recursos
  const battleCalibrada = regiaoCalibrada(cfg.regioes.battle_list)
  const dropPronto =
    regiaoCalibrada(cfg.regioes.inventario) &&
    regiaoCalibrada(cfg.regioes.drop_tile) &&
    (cfg.drop.itens?.length ?? 0) >= 1
  const cavebotPronto =
    regiaoCalibrada(cfg.regioes.minimap) && (cfg.cavebot.waypoints?.length ?? 0) >= 1
  const manaAoVivo = tele.estado?.mana_pct

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

      <Tabs defaultValue="recursos">
        <TabsList className="flex w-full flex-wrap justify-start gap-1">
          <TabsTrigger value="recursos">Recursos</TabsTrigger>
          <TabsTrigger value="cura">Cura</TabsTrigger>
          <TabsTrigger value="alvo">Alvo</TabsTrigger>
          <TabsTrigger value="acoes">Saque & Comer</TabsTrigger>
          <TabsTrigger value="drop">Drop</TabsTrigger>
          <TabsTrigger value="cavebot">Cavebot</TabsTrigger>
          <TabsTrigger value="magia">Magia de ataque</TabsTrigger>
          <TabsTrigger value="mana">Usar Mana</TabsTrigger>
          <TabsTrigger value="captura">Captura</TabsTrigger>
          <TabsTrigger value="visao">Visão</TabsTrigger>
          <TabsTrigger value="sistema">Sistema</TabsTrigger>
        </TabsList>

        <TabsContent value="recursos" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Recursos do bot</CardTitle>
              <CardDescription>
                Ligue/desligue cada funcionalidade. Os ajustes finos de cada uma ficam nas abas ao lado.
                Mudanças valem no próximo start do bot.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3">
              <LinhaRecurso
                titulo="Auto-cura"
                descricao="Cura HP e bebe poção de mana por limiares. Recomendado manter sempre ligado."
                ativo={v("cura.ativo")}
                onChange={(x) => set("cura.ativo", x)}
              />
              <LinhaRecurso
                titulo="Targeting (alvo)"
                descricao="Ataca a criatura mais próxima detectada na battle list."
                ativo={v("alvo.ativo")}
                onChange={(x) => set("alvo.ativo", x)}
                alerta={!battleCalibrada ? "Requer a battle list calibrada (aba Calibração)." : undefined}
              />
              <LinhaRecurso
                titulo="Auto-loot (saque)"
                descricao="Dispara o Quick Loot após cada kill. Desligue se sua conta já faz loot automático."
                ativo={v("saque.ativo")}
                onChange={(x) => set("saque.ativo", x)}
                alerta={!battleCalibrada ? "Requer a battle list calibrada (aba Calibração)." : undefined}
              />
              <LinhaRecurso
                titulo="Auto-comer"
                descricao="Aperta a hotkey de comida periodicamente."
                ativo={v("comer.ativo")}
                onChange={(x) => set("comer.ativo", x)}
              />
              <LinhaRecurso
                titulo="Drop de loot"
                descricao="Arrasta itens cadastrados da backpack para um tile do chão (reconhece por imagem)."
                ativo={v("drop.ativo")}
                onChange={(x) => set("drop.ativo", x)}
                alerta={
                  !dropPronto
                    ? "Requer inventário + tile de drop calibrados (aba Calibração) e ≥1 item cadastrado (aba Drop)."
                    : undefined
                }
              />
              <LinhaRecurso
                titulo="Magia de ataque"
                emTeste
                descricao="Em combate, aperta UMA hotkey de ataque (você monta a rotação de magias nessa hotkey no Tibia). Respeita um piso de mana."
                ativo={v("magia_ataque.ativo")}
                onChange={(x) => set("magia_ataque.ativo", x)}
                alerta={!battleCalibrada ? "Requer a battle list calibrada (p/ saber quando há combate)." : undefined}
              />
              <LinhaRecurso
                titulo="Usar mana (treino de Magic Level)"
                emTeste
                descricao="Gasta mana apertando uma tecla enquanto a mana estiver alta (histerese). Ajuste o limiar na aba Usar Mana."
                ativo={v("usar_mana.ativo")}
                onChange={(x) => set("usar_mana.ativo", x)}
              />
              <LinhaRecurso
                titulo="Cavebot (navegação)"
                emTeste
                descricao="Caminha a hunt clicando waypoints no minimapa (o Tibia faz o pathfinding). Cede ao combate; trata escadas/buracos. A rota repete em loop."
                ativo={v("cavebot.ativo")}
                onChange={(x) => set("cavebot.ativo", x)}
                alerta={
                  !cavebotPronto
                    ? "Requer o minimapa calibrado (aba Calibração) e ≥1 waypoint (aba Cavebot)."
                    : undefined
                }
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="cura" className="space-y-6">
          <Secao titulo="Auto-cura" descricao="Limiares de HP/Mana e teclas de cura (prioridade máxima).">
            <CampoSwitch label="Ativo" dica="Liga/desliga a auto-cura (também na aba Recursos)." valor={v("cura.ativo")} onChange={(x) => set("cura.ativo", x)} />
            <div className="hidden sm:block" />
            <CampoNumero label="HP crítico" sufixo="%" min={0} max={100} valor={v("cura.hp_critico")} onChange={(x) => set("cura.hp_critico", x)} dica="Abaixo disso, cura forte." />
            <CampoNumero label="HP baixo" sufixo="%" valor={v("cura.hp_baixo")} onChange={(x) => set("cura.hp_baixo", x)} dica="Abaixo disso, cura leve." />
            <CampoNumero label="Mana baixa" sufixo="%" valor={v("cura.mana_baixa")} onChange={(x) => set("cura.mana_baixa", x)} dica="Abaixo disso, poção de mana." />
            <CampoTecla label="Tecla cura forte (HP crítico)" dica="Pode ser poção OU magia — o que você bindar nessa hotkey no Tibia. Dispara no HP crítico." valor={v("cura.tecla_cura_forte")} onChange={(x) => set("cura.tecla_cura_forte", x)} />
            <CampoTecla label="Tecla cura leve (HP baixo)" dica="Pode ser magia OU poção. Dispara no HP baixo (acima do crítico)." valor={v("cura.tecla_cura_leve")} onChange={(x) => set("cura.tecla_cura_leve", x)} />
            <CampoTecla label="Tecla poção mana" valor={v("cura.tecla_pocao_mana")} onChange={(x) => set("cura.tecla_pocao_mana", x)} />
          </Secao>
        </TabsContent>

        <TabsContent value="alvo" className="space-y-6">
          <Secao titulo="Targeting" descricao="Requer battle list calibrada. Clica/ataca a criatura mais próxima.">
            <CampoSwitch label="Ativo" dica="Liga/desliga o targeting (também na aba Recursos)." valor={v("alvo.ativo")} onChange={(x) => set("alvo.ativo", x)} />
            <div className="hidden sm:block" />
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

        <TabsContent value="drop" className="space-y-6">
          <Secao titulo="Drop de loot" descricao="Arrasta itens cadastrados da backpack para o tile de drop (calibre em Calibração). Itens são reconhecidos por imagem (template).">
            <CampoSwitch label="Ativo" valor={v("drop.ativo")} onChange={(x) => set("drop.ativo", x)} />
            <CampoSwitch label="Confirmar quantidade (Enter)" dica="Aperta Enter após arrastar, p/ a janela 'Move how many?' de itens empilháveis." valor={v("drop.confirmar_quantidade")} onChange={(x) => set("drop.confirmar_quantidade", x)} />
            <CampoNumero label="Confiança do match (threshold)" step={0.01} min={0} max={1} valor={v("drop.threshold")} onChange={(x) => set("drop.threshold", x)} dica="0..1 — quanto maior, mais exato o reconhecimento." />
            <CampoNumero label="Intervalo entre drops" sufixo="s" step={0.5} valor={v("drop.intervalo_s")} onChange={(x) => set("drop.intervalo_s", x)} />
            <CampoNumero label="Prioridade" valor={v("drop.prioridade")} onChange={(x) => set("drop.prioridade", x)} dica="Abaixo de cura/alvo/saque." />
            <DropItens itens={(v("drop.itens") ?? []) as ItemDrop[]} onChange={(itens) => set("drop.itens", itens)} />
          </Secao>
        </TabsContent>

        <TabsContent value="cavebot" className="space-y-6">
          <Secao
            titulo="Cavebot (navegação por waypoints)"
            descricao="Clica pontos no minimapa em sequência (o Tibia pathfinda cada trecho); a chegada é detectada quando o minimapa para de rolar. Cede ao combate. Requer o minimapa calibrado (aba Calibração)."
          >
            <CampoSwitch label="Ativo" dica="Liga/desliga o cavebot (também na aba Recursos)." valor={v("cavebot.ativo")} onChange={(x) => set("cavebot.ativo", x)} />
            <CampoNumero label="Prioridade" valor={v("cavebot.prioridade")} onChange={(x) => set("cavebot.prioridade", x)} dica="Baixa: cura/alvo/saque vêm antes (e o cavebot cede ao combate)." />
            <CampoNumero label="Cooldown entre cliques" sufixo="s" step={0.1} min={0} valor={v("cavebot.cooldown_s")} onChange={(x) => set("cavebot.cooldown_s", x)} />
            <CampoNumero label="Ticks parado p/ 'chegou'" step={1} min={1} valor={v("cavebot.parado_ticks")} onChange={(x) => set("cavebot.parado_ticks", x)} dica="Quantos ticks o minimapa precisa ficar estático para considerar que chegou." />
            <CampoNumero label="Limiar de movimento" step={0.5} min={0} valor={v("cavebot.limiar_movimento")} onChange={(x) => set("cavebot.limiar_movimento", x)} dica="Diff médio por pixel acima disso = minimapa rolando. Aumente se detectar movimento parado." />
            <CampoNumero label="Timeout do trecho" sufixo="s" step={0.5} min={0} valor={v("cavebot.timeout_trecho_s")} onChange={(x) => set("cavebot.timeout_trecho_s", x)} dica="Desiste do trecho e avança após este tempo (rede p/ clique perdido)." />
            <CampoNumero label="Timeout de combate" sufixo="s" step={1} min={0} valor={v("cavebot.combate_timeout_s")} onChange={(x) => set("cavebot.combate_timeout_s", x)} dica="Se há criatura mas nenhuma morte por este tempo (bicho inalcançável), volta a andar em vez de travar. 0 = nunca desiste." />
            <CampoNumero label="Limiar de troca de andar" step={1} min={0} valor={v("cavebot.limiar_troca_andar")} onChange={(x) => set("cavebot.limiar_troca_andar", x)} dica="Pico de mudança do minimapa que confirma escada/buraco/corda. Baixe se trocas não forem detectadas." />
            <CampoNumero label="Tentativas de troca" step={1} min={1} valor={v("cavebot.tentativas_troca")} onChange={(x) => set("cavebot.tentativas_troca", x)} dica="Re-tentativas de um waypoint 'muda de andar' antes de seguir (best-effort, não trava)." />
            <Waypoints waypoints={(v("cavebot.waypoints") ?? []) as Waypoint[]} onChange={(wps) => set("cavebot.waypoints", wps)} />
          </Secao>
        </TabsContent>

        <TabsContent value="magia" className="space-y-6">
          <Secao
            titulo="Magia de ataque"
            descricao="Em combate, aperta UMA hotkey de ataque periodicamente. A rotação de magias (exori → exori gran → ...) é montada no PRÓPRIO Tibia nessa hotkey. Requer a battle list calibrada (p/ saber quando há combate). Cede a cura/saque/alvo."
          >
            <CampoSwitch label="Ativo" dica="Liga/desliga (também na aba Recursos)." valor={v("magia_ataque.ativo")} onChange={(x) => set("magia_ataque.ativo", x)} />
            <CampoTecla label="Tecla de ataque" dica="A hotkey onde você montou a rotação de magias no Tibia." valor={v("magia_ataque.tecla")} onChange={(x) => set("magia_ataque.tecla", x)} />
            <CampoNumero label="Intervalo entre casts" sufixo="s" step={0.5} min={0} valor={v("magia_ataque.intervalo_s")} onChange={(x) => set("magia_ataque.intervalo_s", x)} dica="Espaçamento entre os toques na hotkey." />
            <CampoNumero label="Mana mínima" sufixo="%" min={0} max={100} valor={v("magia_ataque.mana_minima")} onChange={(x) => set("magia_ataque.mana_minima", x)} dica="Não ataca abaixo disso — preserva mana p/ cura." />
            <CampoNumero label="Prioridade" valor={v("magia_ataque.prioridade")} onChange={(x) => set("magia_ataque.prioridade", x)} dica="Abaixo de cura(100)/saque(85)/alvo(80)." />
          </Secao>
        </TabsContent>

        <TabsContent value="mana" className="space-y-6">
          <Secao titulo="Usar Mana (treino de Magic Level)" descricao="Aperta uma tecla (ex.: cura forte) enquanto a mana está alta, para gastar mana e treinar ML. A histerese evita oscilar na borda: começa a gastar em 'mana alto' e só para abaixo de 'mana alvo'.">
            <CampoSwitch label="Ativo" valor={v("usar_mana.ativo")} onChange={(x) => set("usar_mana.ativo", x)} />
            <CampoTecla label="Tecla" dica="Qualquer spell que gaste mana (cura forte serve)." valor={v("usar_mana.tecla")} onChange={(x) => set("usar_mana.tecla", x)} />
            <CampoNumero label="Mana alto" sufixo="%" min={0} max={100} valor={v("usar_mana.mana_alto")} onChange={(x) => set("usar_mana.mana_alto", x)} dica="A partir daqui começa a gastar. Mana cheia raramente lê 100% (bordas/dígitos) → use ~95%." />
            <CampoNumero label="Mana alvo" sufixo="%" min={0} max={100} valor={v("usar_mana.mana_alvo")} onChange={(x) => set("usar_mana.mana_alvo", x)} dica="Para de gastar abaixo disso (deixa folga p/ curar)." />
            <CampoNumero label="Cooldown" sufixo="s" step={0.5} min={0} valor={v("usar_mana.cooldown_s")} onChange={(x) => set("usar_mana.cooldown_s", x)} />
            <CampoNumero label="Prioridade" valor={v("usar_mana.prioridade")} onChange={(x) => set("usar_mana.prioridade", x)} dica="Baixa por padrão (roda quando cura/alvo/saque não têm nada a fazer)." />
            <p className="rounded-md border border-border bg-background/40 p-2.5 text-xs text-muted-foreground sm:col-span-2">
              Mana lida agora:{" "}
              <span className="font-medium tabular-nums text-foreground">
                {manaAoVivo == null ? "— (bot parado/desconectado)" : `${manaAoVivo.toFixed(0)}%`}
              </span>
              {" "}— use este valor com a mana cheia para escolher o "mana alto".
            </p>
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
            <CampoSwitch label="HP enche da direita" dica="Deixe desligado: o HP normalmente enche da esquerda." valor={v("visao.hp.invertido")} onChange={(x) => set("visao.hp.invertido", x)} />
            <div className="hidden sm:block" />
            <CampoNumero label="Mana — brilho mín. (v_min)" valor={v("visao.mana.v_min")} onChange={(x) => set("visao.mana.v_min", x)} />
            <CampoNumero label="Mana — saturação mín. (s_min)" valor={v("visao.mana.s_min")} onChange={(x) => set("visao.mana.s_min", x)} />
            <CampoSwitch label="Mana enche da direita" dica="Ligado: a mana do Tibia esvazia da esquerda p/ direita." valor={v("visao.mana.invertido")} onChange={(x) => set("visao.mana.invertido", x)} />
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
