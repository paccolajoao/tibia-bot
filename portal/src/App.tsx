import { NavLink, Route, Routes } from "react-router-dom"
import { Activity, Crosshair, Settings, Layers } from "lucide-react"
import { cn } from "@/lib/utils"
import { Toaster } from "@/components/ui/sonner"
import { Dashboard } from "@/pages/Dashboard"
import { Configuracoes } from "@/pages/Configuracoes"
import { Perfis } from "@/pages/Perfis"
import { Calibracao } from "@/pages/Calibracao"

const NAV = [
  { para: "/", rotulo: "Dashboard", icone: Activity, fim: true },
  { para: "/config", rotulo: "Configurações", icone: Settings, fim: false },
  { para: "/perfis", rotulo: "Perfis", icone: Layers, fim: false },
  { para: "/calibracao", rotulo: "Calibração", icone: Crosshair, fim: false },
]

export function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card/50 p-4 md:flex">
        <div className="mb-6 flex items-center gap-2 px-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground font-bold">
            T
          </div>
          <div className="leading-tight">
            <div className="font-semibold">Bot Tibia</div>
            <div className="text-xs text-muted-foreground">Portal de controle</div>
          </div>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV.map(({ para, rotulo, icone: Icone, fim }) => (
            <NavLink
              key={para}
              to={para}
              end={fim}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/15 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )
              }
            >
              <Icone className="h-4 w-4" />
              {rotulo}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto px-2 pt-4 text-xs text-muted-foreground">
          Mudanças de config valem no próximo start do bot.
        </div>
      </aside>

      <main className="flex-1 overflow-x-hidden">
        {/* nav mobile */}
        <div className="flex gap-1 overflow-x-auto border-b border-border bg-card/50 p-2 md:hidden">
          {NAV.map(({ para, rotulo, icone: Icone, fim }) => (
            <NavLink
              key={para}
              to={para}
              end={fim}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-1.5 text-sm",
                  isActive ? "bg-primary/15 text-primary" : "text-muted-foreground"
                )
              }
            >
              <Icone className="h-4 w-4" />
              {rotulo}
            </NavLink>
          ))}
        </div>

        <div className="mx-auto max-w-6xl p-4 md:p-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/config" element={<Configuracoes />} />
            <Route path="/perfis" element={<Perfis />} />
            <Route path="/calibracao" element={<Calibracao />} />
          </Routes>
        </div>
      </main>

      <Toaster />
    </div>
  )
}
