import type { ReactNode } from 'react'

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
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-[60]">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
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
    </div>
  )
}
