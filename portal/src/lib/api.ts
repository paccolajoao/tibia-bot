import type { Config, FrameCalibracao, Meta, PerfilResumo, Regiao } from "./types"

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  })
  if (!res.ok) {
    let detalhe = res.statusText
    try {
      const corpo = await res.json()
      detalhe = corpo.detail ?? detalhe
    } catch {
      /* corpo não-JSON */
    }
    throw new Error(typeof detalhe === "string" ? detalhe : JSON.stringify(detalhe))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  // perfis
  listarPerfis: () => req<PerfilResumo[]>("/api/perfis"),
  criarPerfil: (nome: string, basear_em?: number) =>
    req<PerfilResumo>("/api/perfis", { method: "POST", body: JSON.stringify({ nome, basear_em }) }),
  obterPerfil: (id: number) => req<PerfilResumo & { config: Config }>(`/api/perfis/${id}`),
  renomearPerfil: (id: number, nome: string) =>
    req<PerfilResumo>(`/api/perfis/${id}`, { method: "PATCH", body: JSON.stringify({ nome }) }),
  excluirPerfil: (id: number) => req<void>(`/api/perfis/${id}`, { method: "DELETE" }),
  ativarPerfil: (id: number) => req<PerfilResumo>(`/api/perfis/${id}/ativar`, { method: "POST" }),
  duplicarPerfil: (id: number, nome: string) =>
    req<PerfilResumo>(`/api/perfis/${id}/duplicar`, { method: "POST", body: JSON.stringify({ nome }) }),

  // config do perfil ativo
  getConfig: () => req<Config>("/api/config"),
  putConfig: (config: Config) => req<Config>("/api/config", { method: "PUT", body: JSON.stringify(config) }),
  putRegioes: (regioes: {
    hp?: Regiao
    mana?: Regiao
    battle_list?: Regiao
    inventario?: Regiao
    drop_tile?: Regiao
  }) => req<unknown>("/api/regioes", { method: "PUT", body: JSON.stringify(regioes) }),

  // import/export
  exportUrl: (id?: number) => (id ? `/api/config/export?perfil_id=${id}` : "/api/config/export"),
  importarYaml: (nome: string, yaml: string) =>
    req<PerfilResumo>("/api/config/importar", { method: "POST", body: JSON.stringify({ nome, yaml }) }),

  // meta + calibração
  meta: () => req<Meta>("/api/meta"),
  capturarFrame: () => req<FrameCalibracao>("/api/calibracao/frame", { method: "POST" }),
}
