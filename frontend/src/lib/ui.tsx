import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { CheckCircle2, AlertCircle } from 'lucide-react'

export function Asterisco() {
  return (
    <span className="text-red-600 font-bold text-base align-middle">&nbsp;*</span>
  )
}

export function Label({
  children,
  required,
  htmlFor,
}: {
  children: ReactNode
  required?: boolean
  htmlFor?: string
}) {
  return (
    <label htmlFor={htmlFor} className="block text-sm font-medium text-gray-700 mb-1">
      {children}
      {required && <Asterisco />}
    </label>
  )
}

export function clasesCampo(
  errores: Record<string, string | undefined>,
  campo: string,
): string {
  return errores[campo]
    ? 'w-full border border-red-600 ring-2 ring-red-300 rounded-lg px-3 py-2 text-sm'
    : 'w-full border rounded-lg px-3 py-2 text-sm'
}

export function ErrorCamposModal({
  errores,
  onCerrar,
}: {
  errores: string[]
  onCerrar: () => void
}) {
  if (errores.length === 0) return null
  return (
    <ModalShell max="max-w-lg" z="z-[60]">
      <div className="p-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xl">⚠️</span>
          <h3 className="font-bold text-lg text-red-700">Faltan campos obligatorios</h3>
        </div>
        <p className="text-sm text-gray-500 mb-3">
          Completá los siguientes campos (están marcados en rojo en el formulario):
        </p>
        <ul className="list-disc list-inside text-sm text-gray-700 space-y-1 mb-4">
          {errores.map(e => <li key={e}>{e}</li>)}
        </ul>
        <div className="flex justify-end">
          <button
            onClick={onCerrar}
            className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Entendido
          </button>
        </div>
      </div>
    </ModalShell>
  )
}

/**
 * Contenedor de modal con scroll accesible con zoom:
 * el wrapper interior (min-h-full) permite llegar al tope/inferior
 * del contenido aunque este sea más alto que la ventana.
 */
export function ModalShell({
  children,
  max = 'max-w-lg',
  z = 'z-50',
}: {
  children: ReactNode
  max?: string
  z?: string
}) {
  return (
    <div className={`fixed inset-0 bg-black/40 overflow-auto ${z} print:hidden`}>
      <div className="flex min-h-full items-center justify-center p-4">
        <div className={`modal-grande bg-white rounded-xl shadow-xl w-full ${max}`}>
          {children}
        </div>
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────
   Toasts globales de éxito/error
   ────────────────────────────────────────────── */

interface ToastItem {
  id: number
  mensaje: string
  tipo: 'exito' | 'error'
}

type MostrarToast = (mensaje: string, tipo?: 'exito' | 'error') => void

const ToastContext = createContext<MostrarToast>(() => {})

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const mostrar = useCallback((mensaje: string, tipo: 'exito' | 'error' = 'exito') => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { id, mensaje, tipo }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 3000)
  }, [])

  return (
    <ToastContext.Provider value={mostrar}>
      {children}
      <div className="fixed bottom-6 right-6 z-[80] space-y-2 print:hidden">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white ${
              t.tipo === 'exito' ? 'bg-green-600' : 'bg-red-600'
            }`}
          >
            {t.tipo === 'exito' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
            {t.mensaje}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): MostrarToast {
  return useContext(ToastContext)
}
