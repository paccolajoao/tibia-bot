import { Toaster as Sonner } from "sonner"

export function Toaster() {
  return (
    <Sonner
      theme="dark"
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast: "!bg-card !text-card-foreground !border-border",
          description: "!text-muted-foreground",
        },
      }}
    />
  )
}
