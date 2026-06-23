"""Configuração tipada e validada (pydantic), carregada/salva em YAML.

A `Config` é a fonte única de thresholds, hotkeys e regiões calibradas. O resto
do bot lê dela; nada hardcoda coordenadas.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

# (left, top, right, bottom) em pixels absolutos do desktop
Regiao = tuple[int, int, int, int]

# Raiz do projeto = .../bot-tibia (configuracao.py está em src/bot/)
RAIZ_PROJETO = Path(__file__).resolve().parents[2]
CAMINHO_CONFIG = RAIZ_PROJETO / "config" / "config.yaml"
CAMINHO_CONFIG_EXEMPLO = RAIZ_PROJETO / "config" / "config.exemplo.yaml"


class MapeamentoObsConfig(BaseModel):
    """Mapeamento canvas (OBS) -> desktop para o clique de targeting.

    box = área do jogo dentro do canvas em coords de canvas [l,t,r,b]; null = canvas
    inteiro (setup recomendado 1:1). O retângulo cliente da janela do Tibia é lido
    ao vivo em runtime, então mover a janela não exige recalibrar.
    """

    box: Regiao | None = None


class CapturaConfig(BaseModel):
    backend: str = "auto"  # auto | bettercam | wgc | mss | obs | tibia_arquivo
    monitor: int = 0
    fps_alvo: float = 15.0
    # campos usados apenas com backend=tibia_arquivo
    tibia_screenshots: str = ""       # pasta de screenshots do Tibia (vazio = auto-detecta)
    hotkey_screenshot: str = "ctrl+p"  # hotkey configurada em Options > Interface do Tibia
    # campos usados apenas com backend=obs (OBS Virtual Camera)
    obs_device_index: int = 0          # índice da webcam virtual (fallback se nome não casar)
    obs_device_nome: str = "OBS Virtual Camera"  # casado por nome se pygrabber instalado
    obs_largura: int = 1920            # resolução pedida ao device (DShow abre 640x480 por padrão)
    obs_altura: int = 1080
    mapeamento_obs: MapeamentoObsConfig = Field(default_factory=MapeamentoObsConfig)


class RegioesConfig(BaseModel):
    hp: Regiao = (0, 0, 0, 0)
    mana: Regiao = (0, 0, 0, 0)
    battle_list: Regiao = (0, 0, 0, 0)
    inventario: Regiao = (0, 0, 0, 0)  # área da backpack varrida no drop de loot
    drop_tile: Regiao = (0, 0, 0, 0)   # tile do chão p/ onde o item é arrastado (usa o centro)
    minimap: Regiao = (0, 0, 0, 0)     # área do minimapa observada pelo cavebot (detecção de "andando")

    @property
    def calibrado(self) -> bool:
        """True quando ambas as barras têm uma região não-zero."""
        return any(self.hp) and any(self.mana)

    @property
    def battle_list_calibrado(self) -> bool:
        """True quando a região da battle list foi marcada (targeting habilitado)."""
        return any(self.battle_list)

    @property
    def drop_calibrado(self) -> bool:
        """True quando inventário e tile de drop foram marcados (drop habilitado)."""
        return any(self.inventario) and any(self.drop_tile)

    @property
    def minimap_calibrado(self) -> bool:
        """True quando a região do minimapa foi marcada (cavebot habilitado)."""
        return any(self.minimap)


class ClassificadorConfig(BaseModel):
    v_min: int = 60  # brilho (HSV Value) mínimo para "preenchido"
    s_min: int = 50  # saturação mínima
    # True quando a barra enche da DIREITA->ESQUERDA (esvazia da esq->dir).
    # A mana do Tibia é assim; o HP é o normal (esq->dir).
    invertido: bool = False


class VisaoConfig(BaseModel):
    confianca_minima: float = 0.6
    hp: ClassificadorConfig = Field(default_factory=ClassificadorConfig)
    # mana enche da direita->esquerda por padrão (comportamento do cliente Tibia)
    mana: ClassificadorConfig = Field(default_factory=lambda: ClassificadorConfig(invertido=True))


class CuraConfig(BaseModel):
    ativo: bool = True  # liga/desliga o comportamento de auto-cura
    hp_critico: float = 35.0
    hp_baixo: float = 60.0
    mana_baixa: float = 40.0
    tecla_cura_forte: str = "f5"
    tecla_cura_leve: str = "f6"
    tecla_pocao_mana: str = "f1"
    cooldown_s: dict[str, float] = Field(
        default_factory=lambda: {"f5": 1.0, "f6": 1.0, "f1": 1.0}
    )


class AlvoConfig(BaseModel):
    """Parâmetros do comportamento de targeting (alvo.py)."""

    ativo: bool = True  # liga/desliga o targeting (também exige battle list calibrada)
    prioridade: int = 80  # abaixo de auto_cura (100): sobreviver antes de atacar
    confianca_minima: float = 0.6
    s_min: int = 60  # saturação mínima do mini HP-bar da criatura na battle list
    v_min: int = 60  # brilho mínimo
    # após atacar, NÃO troca de alvo por este tempo (deixa o auto-attack do Tibia matar).
    # Re-ataca antes disso só se uma criatura morrer; o timeout é a rede p/ clique perdido.
    # Curto (1.5s) para re-engajar rápido quando o clique não pega o alvo.
    recompromisso_s: float = 1.5
    cooldown_s: dict[str, float] = Field(default_factory=lambda: {"atacar": 2.0})
    # Se definida, usa TECLA (ex.: "space") em vez de clique na battle list.
    # Requer que a tecla esteja bindada em Options > Hotkeys do Tibia como "Attack Closest".
    tecla: str | None = None


class ComerConfig(BaseModel):
    """Auto-comer: aperta a hotkey de comida periodicamente (timed)."""

    ativo: bool = True
    tecla: str = "f7"  # hotkey de comida bindada no Tibia
    intervalo_s: float = 120.0  # come a cada N segundos
    prioridade: int = 10  # mais baixa: cura/ataque/saque vêm antes


class SaqueConfig(BaseModel):
    """Auto-loot via Quick Loot do Tibia (hotkey), disparado por kill."""

    ativo: bool = True
    tecla: str = "f4"  # hotkey de Quick Loot bindada no Tibia
    confianca_minima: float = 0.6
    janela_s: float = 5.0  # após um kill, tenta saquear por esta janela
    intervalo_press_s: float = 1.0  # intervalo entre presses dentro da janela
    # ACIMA de alvo (80): Quick Loot é 1 tecla rápida; saquear o corpo logo após a
    # morte evita perder o loot quando ainda há outras criaturas para atacar.
    prioridade: int = 85


class ItemDrop(BaseModel):
    """Um item a ser dropado, identificado por um template (ícone) recortado no portal."""

    nome: str = ""
    template_b64: str = ""  # PNG do ícone em base64 (sem prefixo data:)


class DropConfig(BaseModel):
    """Drop de loot: arrasta itens cadastrados da backpack para um tile do chão.

    Requer `regioes.inventario` e `regioes.drop_tile` calibrados. A detecção é por
    template matching (cv2.matchTemplate) sobre a região do inventário.
    """

    ativo: bool = False
    itens: list[ItemDrop] = Field(default_factory=list)
    threshold: float = 0.85  # confiança mínima do match (0..1)
    intervalo_s: float = 1.0  # intervalo entre drops
    prioridade: int = 50  # abaixo de cura/alvo/saque; acima de comer
    # apertar Enter após arrastar (confirma a janela "Move how many?" de itens empilháveis)
    confirmar_quantidade: bool = True


class UsarManaConfig(BaseModel):
    """Descarga de mana para treino de ML: pressiona uma tecla enquanto mana >= mana_alto."""

    ativo: bool = False
    tecla: str = "f5"          # tecla a pressionar (normalmente cura forte)
    # ATENÇÃO: mana cheia raramente lê exatamente 100% (anti-aliasing de borda +
    # dígitos sobre a barra a deixam em ~96-99%). Por isso o default é 95, e o
    # comportamento trata mana_alto >= 100 como ~97% (ver usar_mana.py).
    mana_alto: float = 95.0    # a partir daqui, começa a gastar mana
    mana_alvo: float = 80.0    # para de gastar abaixo disso (histerese)
    confianca_minima: float = 0.6
    cooldown_s: float = 1.0    # intervalo mínimo entre presses
    prioridade: int = 15       # abaixo de tudo exceto Comer (10)


class Waypoint(BaseModel):
    """Um ponto da rota do cavebot.

    `x`/`y` são coords de FRAME (mesmo espaço das regiões calibradas; sob OBS são
    coords de canvas, convertidas p/ desktop em runtime). Para `ir` o ponto é no
    minimapa; para `andar_em`/`usar` é no game-world.
    """

    tipo: str = "ir"          # ir | andar_em | usar | tecla | esperar
    nome: str = ""
    x: int = 0
    y: int = 0
    tecla: str | None = None  # p/ tipo "tecla" (hotkey de corda/pá bindada no Tibia)
    dwell_s: float = 1.5      # espera após executar (troca de andar / assentar)
    # marca waypoints que MUDAM DE ANDAR (escada/buraco/corda/pá): o cavebot valida a
    # troca pelo pico do minimapa e re-tenta se falhar (ver CavebotConfig.limiar_troca_andar)
    troca_andar: bool = False


class CavebotConfig(BaseModel):
    """Navegação por waypoints: clica pontos no minimapa em sequência (o Tibia
    pathfinda cada trecho). Cede ao combate. Requer `regioes.minimap` calibrado.
    """

    ativo: bool = False
    prioridade: int = 20  # acima dos ociosos (usar_mana=15/comer=10); cede ao combate ele mesmo
    waypoints: list[Waypoint] = Field(default_factory=list)
    cooldown_s: float = 0.8          # intervalo mínimo entre cliques de navegação
    parado_ticks: int = 4            # ticks de minimapa estático p/ considerar "chegou"
    limiar_movimento: float = 2.0    # diff médio por pixel acima disso = "minimapa movendo"
    timeout_trecho_s: float = 8.0    # desiste do trecho (re-clica/avança) após este tempo
    # watchdog de combate: se há criaturas mas nenhuma morte por este tempo (bicho
    # inalcançável), o cavebot volta a andar em vez de ceder p/ sempre. 0 = nunca desiste.
    combate_timeout_s: float = 15.0
    # validação de troca de andar: pico de diff do minimapa que confirma que mudou o andar
    limiar_troca_andar: float = 25.0
    tentativas_troca: int = 3        # re-tentativas de um waypoint troca_andar antes de seguir


class MagiaAtaqueConfig(BaseModel):
    """Aperta UMA hotkey de ataque enquanto há criatura em combate (a rotação de
    magias é montada no próprio Tibia nessa hotkey). Respeita um piso de mana p/ não
    esvaziar a mana necessária para cura. Cede a cura/saque/alvo (prioridade menor).
    """

    ativo: bool = False
    tecla: str = "f7"
    intervalo_s: float = 2.0       # cooldown entre casts (vira o cooldown da chave)
    mana_minima: float = 30.0      # não ataca abaixo disso (preserva mana p/ cura)
    confianca_minima: float = 0.6
    prioridade: int = 70           # abaixo de cura(100)/saque(85)/alvo(80); acima de drop(50)


class EntradaConfig(BaseModel):
    atraso_pre_ms: tuple[int, int] = (40, 90)
    atraso_pos_ms: tuple[int, int] = (30, 70)


class SegurancaConfig(BaseModel):
    hotkey_pausar: str = "f11"
    hotkey_panico: str = "f12"
    titulo_janela_contains: str = "Tibia"


class PainelConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    fps_quadro: float = 6.0


class Config(BaseModel):
    captura: CapturaConfig = Field(default_factory=CapturaConfig)
    regioes: RegioesConfig = Field(default_factory=RegioesConfig)
    visao: VisaoConfig = Field(default_factory=VisaoConfig)
    cura: CuraConfig = Field(default_factory=CuraConfig)
    alvo: AlvoConfig = Field(default_factory=AlvoConfig)
    comer: ComerConfig = Field(default_factory=ComerConfig)
    saque: SaqueConfig = Field(default_factory=SaqueConfig)
    drop: DropConfig = Field(default_factory=DropConfig)
    usar_mana: UsarManaConfig = Field(default_factory=UsarManaConfig)
    cavebot: CavebotConfig = Field(default_factory=CavebotConfig)
    magia_ataque: MagiaAtaqueConfig = Field(default_factory=MagiaAtaqueConfig)
    entrada: EntradaConfig = Field(default_factory=EntradaConfig)
    seguranca: SegurancaConfig = Field(default_factory=SegurancaConfig)
    painel: PainelConfig = Field(default_factory=PainelConfig)


def config_para_dict(config: Config) -> dict:
    """Serializa o Config para um dict JSON-safe (tipos primitivos)."""
    return config.model_dump(mode="json")


def config_de_dict(dados: dict) -> Config:
    """Reconstrói (e valida) um Config a partir de um dict. Levanta em dados inválidos."""
    return Config(**(dados or {}))


def carregar_config(caminho: Path | None = None) -> Config:
    """Carrega config.yaml; se não existir, tenta config.exemplo.yaml; senão usa defaults."""
    caminho = caminho or CAMINHO_CONFIG
    fonte = caminho if caminho.exists() else CAMINHO_CONFIG_EXEMPLO
    if fonte.exists():
        dados = yaml.safe_load(fonte.read_text(encoding="utf-8")) or {}
        return Config(**dados)
    return Config()


def salvar_config(config: Config, caminho: Path | None = None) -> None:
    """Persiste a config em YAML (mode='json' garante tipos serializáveis)."""
    caminho = caminho or CAMINHO_CONFIG
    caminho.parent.mkdir(parents=True, exist_ok=True)
    dados = config.model_dump(mode="json")
    caminho.write_text(
        yaml.safe_dump(dados, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
