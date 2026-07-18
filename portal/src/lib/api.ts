import type {
  Config,
  FrameCalibracao,
  Meta,
  PerfilResumo,
  Regiao,
  TesteArduinoBody,
  TesteArduinoResultado,
  TesteMarcaResultado,
} from "./types"

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
    minimap?: Regiao
  }) => req<unknown>("/api/regioes", { method: "PUT", body: JSON.stringify(regioes) }),

  // import/export
  exportUrl: (id?: number) => (id ? `/api/config/export?perfil_id=${id}` : "/api/config/export"),
  importarYaml: (nome: string, yaml: string) =>
    req<PerfilResumo>("/api/config/importar", { method: "POST", body: JSON.stringify({ nome, yaml }) }),

  // meta + calibração
  meta: () => req<Meta>("/api/meta"),
  // regiao opcional (ex.: "minimap") recorta só esse trecho no servidor
  capturarFrame: (regiao?: string) =>
    req<FrameCalibracao>(`/api/calibracao/frame${regiao ? `?regiao=${encodeURIComponent(regiao)}` : ""}`, {
      method: "POST",
    }),

  // entrada: teste rápido do board Arduino (não salva nada)
  testarArduino: (body: TesteArduinoBody) =>
    req<TesteArduinoResultado>("/api/entrada/arduino/testar", { method: "POST", body: JSON.stringify(body) }),

  // cavebot: testa a detecção de uma marca no minimapa (não salva nada)
  testarMarca: (template_b64: string, threshold?: number) =>
    req<TesteMarcaResultado>("/api/cavebot/testar_marca", {
      method: "POST",
      body: JSON.stringify({ template_b64, threshold }),
    }),
}
