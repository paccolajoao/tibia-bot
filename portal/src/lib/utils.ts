import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Atualiza imutavelmente um campo aninhado por caminho ("cura.hp_critico"). */
export function setIn<T>(obj: T, caminho: string, valor: unknown): T {
  const partes = caminho.split(".")
  const copia: any = Array.isArray(obj) ? [...(obj as any)] : { ...obj }
  let alvo = copia
  for (let i = 0; i < partes.length - 1; i++) {
    const k = partes[i]
    alvo[k] = Array.isArray(alvo[k]) ? [...alvo[k]] : { ...alvo[k] }
    alvo = alvo[k]
  }
  alvo[partes[partes.length - 1]] = valor
  return copia
}

/** Lê um campo aninhado por caminho. */
export function getIn(obj: any, caminho: string): any {
  return caminho.split(".").reduce((o, k) => (o == null ? o : o[k]), obj)
}
