import { useEffect, useState } from 'react'
import api from '../lib/api'
import type { AumentoItem } from '../lib/types'
import { MESES, formatMoneda } from '../lib/types'
import { TrendingUp, AlertTriangle, XCircle } from 'lucide-react'

function formatDepto(piso: string | undefined, codigo: string | undefined) {
  if (!piso || !codigo) return `${piso ?? ''} ${codigo ?? ''}`.trim()
  return `${piso} — ${codigo}`
}

export default function Aumentos() {
  const [items, setItems] = useState<AumentoItem[]>([])
  const [loading, setLoading] = useState(true)

  async function cargar() {
    setLoading(true)
    const res = await api.get('/aumentos/')
    setItems(res.data)
    setLoading(false)
  }

  useEffect(() => { cargar() }, [])

  function proximoAumento(item: AumentoItem) {
    const p = item.proximo_aumento
    if (!p.proximo_mes || !p.proximo_anio) return '-'
    return `${MESES[p.proximo_mes - 1]} ${p.proximo_anio}`
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-3xl font-bold text-gray-800">Vista de Aumentos</h2>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500 text-lg">Cargando...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400 text-lg">No hay contratos activos.</div>
      ) : (
        <div className="space-y-4">
          {items.map(item => {
            const p = item.proximo_aumento
            return (
              <div key={item.contrato.id_contratos} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-gray-800 text-base">
                        {formatDepto(item.departamento?.piso, item.departamento?.codigo)}
                        <span className="font-normal text-gray-600"> ({item.inquilino?.nombre_apellido})</span>
                      </span>
                      {item.alerta === 'Vencido' && (
                        <span className="flex items-center gap-1 text-sm px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-semibold">
                          <XCircle size={14} /> Vencido
                        </span>
                      )}
                      {item.alerta === 'Por vencer' && (
                        <span className="flex items-center gap-1 text-sm px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700 font-semibold">
                          <AlertTriangle size={14} /> Por vencer
                        </span>
                      )}
                    </div>
                    {item.departamento?.direccion && (
                      <p className="text-sm text-gray-400 mt-0.5">{item.departamento.direccion}</p>
                    )}
                    <p className="text-base text-gray-600 mt-1 font-medium">
                      Aumento: <span className="text-gray-800">{item.contrato.porcentaje_aumento}%</span> cada <span className="text-gray-800">{item.contrato.periodicidad_aumento_meses} meses</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-blue-600">
                    <TrendingUp size={22} />
                    <span className="font-semibold text-base">Próximo: {proximoAumento(item)}</span>
                  </div>
                </div>

                {p.alquiler_nuevo && (
                  <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-sm text-gray-500 mb-1">Alquiler actual</p>
                      <p className="font-bold text-gray-800 text-base">{formatMoneda(p.alquiler_actual)}</p>
                    </div>
                    <div className="bg-blue-50 rounded-lg p-3">
                      <p className="text-sm text-blue-600 mb-1">Alquiler nuevo</p>
                      <p className="font-bold text-blue-700 text-base">{formatMoneda(p.alquiler_nuevo)}</p>
                      <p className="text-sm text-blue-500 mt-0.5">+{formatMoneda((p.alquiler_nuevo ?? 0) - p.alquiler_actual)}</p>
                    </div>
                    {item.contrato.cobra_expensa && p.expensa_actual != null && (
                      <>
                        <div className="bg-gray-50 rounded-lg p-3">
                          <p className="text-sm text-gray-500 mb-1">Expensa actual</p>
                          <p className="font-bold text-gray-800 text-base">{formatMoneda(p.expensa_actual)}</p>
                        </div>
                        <div className="bg-blue-50 rounded-lg p-3">
                          <p className="text-sm text-blue-600 mb-1">Expensa nueva</p>
                          <p className="font-bold text-blue-700 text-base">{formatMoneda(p.expensa_nueva)}</p>
                          <p className="text-sm text-blue-500 mt-0.5">+{formatMoneda((p.expensa_nueva ?? 0) - (p.expensa_actual ?? 0))}</p>
                        </div>
                      </>
                    )}
                  </div>
                )}

                {!p.alquiler_nuevo && (
                  <div className="mt-3 p-2 bg-gray-50 rounded text-base text-gray-500">
                    Sin aumentos configurados para este contrato.
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
