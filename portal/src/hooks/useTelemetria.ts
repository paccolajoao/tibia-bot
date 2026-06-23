import { useCallback, useEffect, useRef, useState } from "react"
import type {
  TelemetriaDecisao,
  TelemetriaDeteccao,
  TelemetriaEstado,
  TelemetriaStats,
} from "@/lib/types"

export interface LinhaLog {
  id: number
  texto: string
  nivel: string
  hora: string
}

export interface Telemetria {
  conectado: boolean
  estado: TelemetriaEstado | null
  decisao: TelemetriaDecisao | null
  stats: TelemetriaStats | null
  deteccao: TelemetriaDeteccao | null
  quadro: string | null // data URL do JPEG
  log: LinhaLog[]
  enviar: (cmd: "pausar" | "retomar" | "parar") => void
}

const MAX_LOG = 250

/** Conecta ao /ws, reconecta sozinho e expõe o último estado de cada tipo + log. */
export function useTelemetria(): Telemetria {
  const [conectado, setConectado] = useState(false)
  const [estado, setEstado] = useState<TelemetriaEstado | null>(null)
  const [decisao, setDecisao] = useState<TelemetriaDecisao | null>(null)
  const [stats, setStats] = useState<TelemetriaStats | null>(null)
  const [deteccao, setDeteccao] = useState<TelemetriaDeteccao | null>(null)
  const [quadro, setQuadro] = useState<string | null>(null)
  const [log, setLog] = useState<LinhaLog[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const idRef = useRef(0)

  useEffect(() => {
    let vivo = true
    let timer: ReturnType<typeof setTimeout>

    const conectar = () => {
      if (!vivo) return
      const proto = location.protocol === "https:" ? "wss://" : "ws://"
      const ws = new WebSocket(`${proto}${location.host}/ws`)
      wsRef.current = ws

      ws.onopen = () => setConectado(true)
      ws.onclose = () => {
        setConectado(false)
        if (vivo) timer = setTimeout(conectar, 1500)
      }
      ws.onerror = () => ws.close()
      ws.onmessage = (ev) => {
        let msg: any
        try {
          msg = JSON.parse(ev.data)
        } catch {
          return
        }
        switch (msg.tipo) {
          case "estado":
            setEstado(msg)
            break
          case "decisao":
            setDecisao(msg)
            break
          case "stats":
            setStats(msg)
            break
          case "deteccao":
            setDeteccao(msg)
            break
          case "quadro":
            setQuadro("data:image/jpeg;base64," + msg.jpeg_base64)
            break
          case "raciocinio":
            setLog((prev) => {
              const linha: LinhaLog = {
                id: idRef.current++,
                texto: msg.texto,
                nivel: msg.nivel || "info",
                hora: new Date().toLocaleTimeString(),
              }
              const novo = [...prev, linha]
              return novo.length > MAX_LOG ? novo.slice(novo.length - MAX_LOG) : novo
            })
            break
        }
      }
    }

    conectar()
    return () => {
      vivo = false
      clearTimeout(timer)
      wsRef.current?.close()
    }
  }, [])

  const enviar = useCallback((cmd: "pausar" | "retomar" | "parar") => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ cmd }))
  }, [])

  return { conectado, estado, decisao, stats, deteccao, quadro, log, enviar }
}
