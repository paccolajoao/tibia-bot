import type { ReactNode } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { cn } from "@/lib/utils"

function Linha({ label, dica, children }: { label: string; dica?: string; children: ReactNode }) {
  return (
    <div className="grid gap-1.5">
      <Label>{label}</Label>
      {children}
      {dica && <p className="text-xs text-muted-foreground">{dica}</p>}
    </div>
  )
}

export function CampoNumero({
  label,
  dica,
  valor,
  onChange,
  step = 1,
  min,
  max,
  sufixo,
}: {
  label: string
  dica?: string
  valor: number
  onChange: (v: number) => void
  step?: number
  min?: number
  max?: number
  sufixo?: string
}) {
  const foraDoLimite =
    Number.isFinite(valor) && ((min != null && valor < min) || (max != null && valor > max))
  return (
    <Linha label={label} dica={dica}>
      <div className="relative">
        <Input
          type="number"
          value={Number.isFinite(valor) ? valor : ""}
          step={step}
          min={min}
          max={max}
          onChange={(e) => onChange(e.target.value === "" ? 0 : Number(e.target.value))}
          className={cn(sufixo && "pr-10", foraDoLimite && "border-destructive focus-visible:ring-destructive")}
        />
        {sufixo && (
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
            {sufixo}
          </span>
        )}
      </div>
      {foraDoLimite && (
        <p className="text-xs text-destructive">
          Valor fora do intervalo {min ?? "−∞"}–{max ?? "∞"}.
        </p>
      )}
    </Linha>
  )
}

export function CampoTexto({
  label,
  dica,
  valor,
  onChange,
  placeholder,
}: {
  label: string
  dica?: string
  valor: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <Linha label={label} dica={dica}>
      <Input value={valor ?? ""} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
    </Linha>
  )
}

export function CampoTecla({
  label,
  dica,
  valor,
  onChange,
}: {
  label: string
  dica?: string
  valor: string
  onChange: (v: string) => void
}) {
  return (
    <CampoTexto
      label={label}
      dica={dica ?? "Deve bater com a hotkey configurada no Tibia."}
      valor={valor}
      onChange={(v) => onChange(v.toLowerCase())}
    />
  )
}

export function CampoSwitch({
  label,
  dica,
  valor,
  onChange,
}: {
  label: string
  dica?: string
  valor: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-md border border-border bg-background/40 px-3 py-2.5">
      <div className="grid gap-0.5">
        <Label>{label}</Label>
        {dica && <p className="text-xs text-muted-foreground">{dica}</p>}
      </div>
      <Switch checked={valor} onCheckedChange={onChange} />
    </div>
  )
}

export function CampoSelect({
  label,
  dica,
  valor,
  onChange,
  opcoes,
}: {
  label: string
  dica?: string
  valor: string
  onChange: (v: string) => void
  opcoes: { valor: string; rotulo: string }[]
}) {
  return (
    <Linha label={label} dica={dica}>
      <Select value={valor} onValueChange={onChange}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {opcoes.map((o) => (
            <SelectItem key={o.valor} value={o.valor}>
              {o.rotulo}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </Linha>
  )
}
