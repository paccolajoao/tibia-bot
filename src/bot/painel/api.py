"""API REST do portal: perfis, configuração, regiões e calibração.

Tudo que o portal precisa para gerenciar o bot sem editar arquivos à mão. A
configuração vive no SQLite (perfil ativo); mudanças passam a valer no **próximo
start** do bot (aplicação exige reiniciar — decisão de projeto).

Rotas (montadas sob `/api`):
  GET    /perfis                 lista perfis (sem o config inteiro)
  POST   /perfis                 cria perfil {nome, basear_em?}
  GET    /perfis/{id}            um perfil + config
  PATCH  /perfis/{id}            renomeia {nome}
  DELETE /perfis/{id}            exclui
  POST   /perfis/{id}/ativar     torna ativo
  POST   /perfis/{id}/duplicar   duplica {nome}
  GET    /config                 config do perfil ativo
  PUT    /config                 salva config no perfil ativo (validado)
  PUT    /regioes                salva regiões calibradas no perfil ativo
  GET    /config/export          baixa o config ativo como YAML
  POST   /config/importar        cria perfil a partir de YAML {nome, yaml}
  GET    /meta                   opções p/ a UI (backends, defaults) + estado
  POST   /calibracao/frame       captura um frame (JPEG base64) p/ desenhar regiões
"""

from __future__ import annotations

import base64

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from bot.configuracao import Config, Regiao
from bot.persistencia import repo_perfis as repo


class CriarPerfil(BaseModel):
    nome: str
    basear_em: int | None = None  # copia o config deste perfil; senão usa defaults


class Renomear(BaseModel):
    nome: str


class Duplicar(BaseModel):
    nome: str


class Regioes(BaseModel):
    hp: Regiao | None = None
    mana: Regiao | None = None
    battle_list: Regiao | None = None
    inventario: Regiao | None = None
    drop_tile: Regiao | None = None


class ImportarYaml(BaseModel):
    nome: str
    yaml: str


def _resumo(p: repo.Perfil) -> dict:
    """Metadados do perfil sem serializar o config inteiro (listagem leve)."""
    return {
        "id": p.id,
        "nome": p.nome,
        "ativo": p.ativo,
        "criado_em": p.criado_em,
        "atualizado_em": p.atualizado_em,
        "calibrado": p.config.regioes.calibrado,
        "battle_list_calibrado": p.config.regioes.battle_list_calibrado,
    }


def criar_router_api(barramento=None) -> APIRouter:
    repo.garantir_inicializado()  # cria o esquema + semeia o perfil "Padrão" se vazio
    r = APIRouter(prefix="/api")

    # ----- perfis -----
    @r.get("/perfis")
    def listar():
        return [_resumo(p) for p in repo.listar_perfis()]

    @r.post("/perfis", status_code=201)
    def criar(body: CriarPerfil):
        base = repo.obter_perfil(body.basear_em).config if body.basear_em else Config()
        try:
            p = repo.criar_perfil(body.nome, base)
        except Exception as e:
            raise HTTPException(409, f"Não foi possível criar o perfil: {e}") from e
        return _resumo(p)

    @r.get("/perfis/{id_perfil}")
    def obter(id_perfil: int):
        try:
            p = repo.obter_perfil(id_perfil)
        except KeyError as e:
            raise HTTPException(404, str(e)) from e
        return {**_resumo(p), "config": p.config.model_dump(mode="json")}

    @r.patch("/perfis/{id_perfil}")
    def patch(id_perfil: int, body: Renomear):
        try:
            return _resumo(repo.renomear(id_perfil, body.nome))
        except KeyError as e:
            raise HTTPException(404, str(e)) from e
        except Exception as e:
            raise HTTPException(409, str(e)) from e

    @r.delete("/perfis/{id_perfil}", status_code=204)
    def deletar(id_perfil: int):
        try:
            repo.excluir(id_perfil)
        except KeyError as e:
            raise HTTPException(404, str(e)) from e
        except ValueError as e:
            raise HTTPException(409, str(e)) from e

    @r.post("/perfis/{id_perfil}/ativar")
    def ativar(id_perfil: int):
        try:
            return _resumo(repo.ativar(id_perfil))
        except KeyError as e:
            raise HTTPException(404, str(e)) from e

    @r.post("/perfis/{id_perfil}/duplicar", status_code=201)
    def duplicar(id_perfil: int, body: Duplicar):
        try:
            return _resumo(repo.duplicar(id_perfil, body.nome))
        except KeyError as e:
            raise HTTPException(404, str(e)) from e
        except Exception as e:
            raise HTTPException(409, str(e)) from e

    # ----- config do perfil ativo -----
    @r.get("/config")
    def get_config():
        return repo.carregar_config_ativa().model_dump(mode="json")

    @r.put("/config")
    def put_config(config: Config):
        # FastAPI já validou o corpo contra o modelo Config.
        repo.salvar_config_ativa(config)
        return config.model_dump(mode="json")

    @r.put("/regioes")
    def put_regioes(body: Regioes):
        cfg = repo.carregar_config_ativa()
        if body.hp is not None:
            cfg.regioes.hp = body.hp
        if body.mana is not None:
            cfg.regioes.mana = body.mana
        if body.battle_list is not None:
            cfg.regioes.battle_list = body.battle_list
        if body.inventario is not None:
            cfg.regioes.inventario = body.inventario
        if body.drop_tile is not None:
            cfg.regioes.drop_tile = body.drop_tile
        repo.salvar_config_ativa(cfg)
        return cfg.regioes.model_dump(mode="json")

    # ----- import/export YAML -----
    @r.get("/config/export")
    def exportar(perfil_id: int | None = None):
        from fastapi.responses import PlainTextResponse

        try:
            cfg = repo.obter_perfil(perfil_id).config if perfil_id else repo.carregar_config_ativa()
        except KeyError as e:
            raise HTTPException(404, str(e)) from e
        texto = yaml.safe_dump(cfg.model_dump(mode="json"), sort_keys=False, allow_unicode=True)
        return PlainTextResponse(
            texto,
            media_type="application/x-yaml",
            headers={"Content-Disposition": 'attachment; filename="config.yaml"'},
        )

    @r.post("/config/importar", status_code=201)
    def importar(body: ImportarYaml):
        try:
            dados = yaml.safe_load(body.yaml) or {}
            cfg = Config(**dados)
        except Exception as e:
            raise HTTPException(422, f"YAML inválido: {e}") from e
        try:
            p = repo.criar_perfil(body.nome, cfg)
        except Exception as e:
            raise HTTPException(409, f"Não foi possível criar o perfil: {e}") from e
        return _resumo(p)

    # ----- meta (opções p/ a UI + estado bruto) -----
    @r.get("/meta")
    def meta():
        ativo = repo.obter_ativo()
        snap = barramento.ultimo_snapshot() if barramento is not None else None
        return {
            "backends_captura": ["auto", "bettercam", "wgc", "mss", "obs", "tibia_arquivo"],
            "perfil_ativo": _resumo(ativo),
            "bot_rodando": snap is not None,
            "estado": snap.to_dict() if snap is not None else None,
        }

    # ----- calibração: captura um frame para desenhar as regiões -----
    @r.post("/calibracao/frame")
    def calibracao_frame():
        from bot.captura.instantaneo import capturar_frame_calibracao, codificar_jpeg

        cfg = repo.carregar_config_ativa()
        try:
            frame = capturar_frame_calibracao(cfg)
        except Exception as e:
            raise HTTPException(500, f"Falha na captura: {e}") from e
        if frame is None:
            raise HTTPException(
                503,
                "Captura veio preta ou vazia. Confira o backend (Tibia oficial exige OBS) "
                "e se o jogo está visível.",
            )
        jpeg = codificar_jpeg(frame.imagem)
        return {
            "jpeg_base64": base64.b64encode(jpeg).decode("ascii"),
            "largura": frame.largura,
            "altura": frame.altura,
            "origem_x": frame.origem_x,
            "origem_y": frame.origem_y,
            "backend": frame.backend,
        }

    return r
