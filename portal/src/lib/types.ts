// Espelha os modelos pydantic de src/bot/configuracao.py.

export type Regiao = [number, number, number, number]

export interface MapeamentoObs {
  box: Regiao | null
}

export interface CapturaConfig {
  backend: string
  monitor: number
  fps_alvo: number
  tibia_screenshots: string
  hotkey_screenshot: string
  obs_device_index: number
  obs_device_nome: string
  obs_largura: number
  obs_altura: number
  mapeamento_obs: MapeamentoObs
}

export interface RegioesConfig {
  hp: Regiao
  mana: Regiao
  battle_list: Regiao
}

export interface Classificador {
  v_min: number
  s_min: number
}

export interface VisaoConfig {
  confianca_minima: number
  hp: Classificador
  mana: Classificador
}

export interface CuraConfig {
  hp_critico: number
  hp_baixo: number
  mana_baixa: number
  tecla_cura_forte: string
  tecla_cura_leve: string
  tecla_pocao_mana: string
  cooldown_s: Record<string, number>
}

export interface AlvoConfig {
  prioridade: number
  confianca_minima: number
  s_min: number
  v_min: number
  recompromisso_s: number
  cooldown_s: Record<string, number>
  tecla: string | null
}

export interface ComerConfig {
  ativo: boolean
  tecla: string
  intervalo_s: number
  prioridade: number
}

export interface SaqueConfig {
  ativo: boolean
  tecla: string
  confianca_minima: number
  janela_s: number
  intervalo_press_s: number
  prioridade: number
}

export interface UsarManaConfig {
  ativo: boolean
  tecla: string
  mana_alto: number
  mana_alvo: number
  confianca_minima: number
  cooldown_s: number
  prioridade: number
}

export interface EntradaConfig {
  atraso_pre_ms: [number, number]
  atraso_pos_ms: [number, number]
}

export interface SegurancaConfig {
  hotkey_pausar: string
  hotkey_panico: string
  titulo_janela_contains: string
}

export interface PainelConfig {
  host: string
  port: number
  fps_quadro: number
}

export interface Config {
  captura: CapturaConfig
  regioes: RegioesConfig
  visao: VisaoConfig
  cura: CuraConfig
  alvo: AlvoConfig
  comer: ComerConfig
  saque: SaqueConfig
  usar_mana: UsarManaConfig
  entrada: EntradaConfig
  seguranca: SegurancaConfig
  painel: PainelConfig
}

export interface PerfilResumo {
  id: number
  nome: string
  ativo: boolean
  criado_em: string
  atualizado_em: string
  calibrado: boolean
  battle_list_calibrado: boolean
}

export interface Meta {
  backends_captura: string[]
  perfil_ativo: PerfilResumo
  bot_rodando: boolean
  estado: TelemetriaEstado | null
}

export interface FrameCalibracao {
  jpeg_base64: string
  largura: number
  altura: number
  origem_x: number
  origem_y: number
  backend: string
}

// ---- telemetria (WebSocket) ----
export interface TelemetriaEstado {
  tipo: "estado"
  hp_pct: number | null
  mana_pct: number | null
  hp_confianca: number | null
  fps: number
  tick: number
  estado_execucao: string
  janela_focada: boolean
  backend_captura: string
}

export interface TelemetriaDecisao {
  tipo: "decisao"
  acao: string
  motivo: string
  comportamento: string
  tecla: string | null
  dados?: { recurso?: string }
}

export interface TelemetriaStats {
  tipo: "stats"
  curas: number
  pocoes_mana: number
  ataques?: number
  refeicoes?: number
  saques?: number
  uptime_s: number
}

export interface TelemetriaDeteccao {
  tipo: "deteccao"
  criaturas: { n: number; alvo_atual: boolean; confianca: number | null } | null
}

export interface TelemetriaRaciocinio {
  tipo: "raciocinio"
  texto: string
  nivel: string
}

export interface TelemetriaQuadro {
  tipo: "quadro"
  jpeg_base64: string
}
