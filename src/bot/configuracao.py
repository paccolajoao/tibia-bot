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


class CapturaConfig(BaseModel):
    backend: str = "auto"  # auto | bettercam | wgc | mss | tibia_arquivo
    monitor: int = 0
    fps_alvo: float = 15.0
    # campos usados apenas com backend=tibia_arquivo
    tibia_screenshots: str = ""       # pasta de screenshots do Tibia (vazio = auto-detecta)
    hotkey_screenshot: str = "ctrl+p"  # hotkey configurada em Options > Interface do Tibia


class RegioesConfig(BaseModel):
    hp: Regiao = (0, 0, 0, 0)
    mana: Regiao = (0, 0, 0, 0)
    battle_list: Regiao = (0, 0, 0, 0)

    @property
    def calibrado(self) -> bool:
        """True quando ambas as barras têm uma região não-zero."""
        return any(self.hp) and any(self.mana)

    @property
    def battle_list_calibrado(self) -> bool:
        """True quando a região da battle list foi marcada (targeting habilitado)."""
        return any(self.battle_list)


class ClassificadorConfig(BaseModel):
    v_min: int = 60  # brilho (HSV Value) mínimo para "preenchido"
    s_min: int = 50  # saturação mínima


class VisaoConfig(BaseModel):
    confianca_minima: float = 0.6
    hp: ClassificadorConfig = Field(default_factory=ClassificadorConfig)
    mana: ClassificadorConfig = Field(default_factory=ClassificadorConfig)


class CuraConfig(BaseModel):
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

    prioridade: int = 80  # abaixo de auto_cura (100): sobreviver antes de atacar
    confianca_minima: float = 0.6
    s_min: int = 60  # saturação mínima do mini HP-bar da criatura na battle list
    v_min: int = 60  # brilho mínimo
    cooldown_s: dict[str, float] = Field(default_factory=lambda: {"atacar": 2.0})


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
    janela_s: float = 3.0  # após um kill, tenta saquear por esta janela
    intervalo_press_s: float = 1.0  # intervalo entre presses dentro da janela
    prioridade: int = 60  # abaixo de alvo (80), acima de comer (10)


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
    entrada: EntradaConfig = Field(default_factory=EntradaConfig)
    seguranca: SegurancaConfig = Field(default_factory=SegurancaConfig)
    painel: PainelConfig = Field(default_factory=PainelConfig)


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
