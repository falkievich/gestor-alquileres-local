import { useEffect, useState } from 'react'
import api from '../lib/api'
import type { DashboardItem } from '../lib/types'
import { formatMoneda, MESES } from '../lib/types'
import {
  CheckCircle2, AlertCircle, XCircle, Eye, EyeOff,
  RefreshCw, Printer, HardDriveDownload
} from 'lucide-react'

export default function Dashboard() {
  const [items, setItems] = useState<DashboardItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showPagados, setShowPagados] = useState(false)
  const [backupMsg, setBackupMsg] = useState('')
  const [overrideModal, setOverrideModal] = useState<DashboardItem | null>(null)
  const [overrideData, setOverrideData] = useState({ alquiler_override: '', expensa_override: '', nota_override: '' })

  async function cargar() {
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/dashboard/mes-actual')
      setItems(res.data)
    } catch {
      setError('Error al cargar el dashboard. ¿Está el backend corriendo?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { cargar() }, [])

  async function marcarPagado(id: number) {
    await api.post(`/dashboard/registros/${id}/pagado`)
    cargar()
  }

  async function desmarcarPagado(id: number) {
    await api.post(`/dashboard/registros/${id}/desmarcar-pagado`)
    cargar()
  }

  async function crearBackup() {
    try {
      const res = await api.post('/backup/')
      setBackupMsg(`✅ Backup creado: ${res.data.archivo}`)
      setTimeout(() => setBackupMsg(''), 5000)
    } catch {
      setBackupMsg('❌ Error al crear backup')
    }
  }

  async function guardarOverride() {
    if (!overrideModal) return
    const idReg = overrideModal.registro.id_registros_mensuales
    const params: Record<string, string | number> = {}
    if (overrideData.alquiler_override !== '') params.alquiler_override = Number(overrideData.alquiler_override)
    if (overrideData.expensa_override !== '') params.expensa_override = Number(overrideData.expensa_override)
    if (overrideData.nota_override !== '') params.nota_override = overrideData.nota_override
    await api.post(`/dashboard/registros/${idReg}/override`, null, { params })
    setOverrideModal(null)
    cargar()
  }

  function handleImprimir() { window.print() }

  const visibles = showPagados ? items : items.filter(i => !i.registro.pagado)
  const mesActual = items.length > 0 ? `${MESES[items[0].mes - 1]} ${items[0].anio}` : ''

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 print:hidden">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Dashboard</h2>
          {mesActual && <p className="text-gray-500 text-sm mt-1">Mes actual: {mesActual}</p>}
        </div>
        <div className="flex gap-2 flex-wrap justify-end">
          <button
            onClick={() => setShowPagados(!showPagados)}
            className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-100 transition text-white"
          >
            {showPagados ? <EyeOff size={16} /> : <Eye size={16} />}
            {showPagados ? 'Ocultar pagados' : 'Mostrar pagados'}
          </button>
          <button onClick={handleImprimir} className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-700 text-white rounded-lg hover:bg-gray-800 transition">
            <Printer size={16} /> Imprimir
          </button>
          <button onClick={cargar} className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-100 transition text-white">
            <RefreshCw size={16} /> Actualizar
          </button>
          <button onClick={crearBackup} className="flex items-center gap-2 px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
            <HardDriveDownload size={16} /> Backup
          </button>
        </div>
      </div>

      {backupMsg && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700 print:hidden">
          {backupMsg}
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Cargando...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          No hay contratos activos para el mes actual.
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          {/* Print header */}
          <div className="hidden print:block p-4 border-b">
            <h2 className="text-xl font-bold">Cobros — {mesActual}</h2>
          </div>

          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Depto</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Inquilino</th>
                <th className="text-right px-4 py-3 font-semibold text-gray-600">Alquiler</th>
                <th className="text-right px-4 py-3 font-semibold text-gray-600">Expensa</th>
                <th className="text-right px-4 py-3 font-semibold text-gray-600">Agua</th>
                <th className="text-right px-4 py-3 font-semibold text-gray-600">Luz</th>
                <th className="text-right px-4 py-3 font-semibold text-gray-600">Total</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Servicios</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Pago</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600 print:hidden">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {visibles.map((item) => {
                const reg = item.registro
                const alq = reg.alquiler_override ?? reg.alquiler_calculado
                const exp = reg.expensa_override ?? reg.expensa_calculada
                return (
                  <tr key={reg.id_registros_mensuales} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-800">
                        {item.departamento?.piso} {item.departamento?.codigo}
                      </div>
                      <div className="flex gap-1 mt-1 flex-wrap">
                        {item.vencido && (
                          <span className="inline-block text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded font-semibold">
                            Vencido
                          </span>
                        )}
                        {reg.nota_override && (
                          <span className="inline-block text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">
                            Ajuste
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-700">{item.inquilino?.nombre_apellido}</td>
                    <td className="px-4 py-3 text-right font-mono">{formatMoneda(alq)}</td>
                    <td className="px-4 py-3 text-right font-mono">{item.contrato.cobra_expensa ? formatMoneda(exp) : <span className="text-gray-400">-</span>}</td>
                    <td className="px-4 py-3 text-right font-mono">
                      {item.contrato.cobra_agua ? (reg.agua != null ? formatMoneda(reg.agua) : <span className="text-orange-500">Pend.</span>) : <span className="text-gray-400">-</span>}
                    </td>
                    <td className="px-4 py-3 text-right font-mono">
                      {item.contrato.cobra_luz ? (reg.luz != null ? formatMoneda(reg.luz) : <span className="text-orange-500">Pend.</span>) : <span className="text-gray-400">-</span>}
                    </td>
                    <td className="px-4 py-3 text-right font-bold font-mono">{formatMoneda(item.total)}</td>
                    <td className="px-4 py-3 text-center">
                      {item.estado_servicios === 'OK' ? (
                        <span className="inline-flex items-center gap-1 text-green-600 text-xs font-semibold">
                          <CheckCircle2 size={14} /> OK
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-orange-500 text-xs font-semibold">
                          <AlertCircle size={14} /> Pendiente
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {reg.pagado ? (
                        <span className="inline-flex items-center gap-1 text-blue-600 text-xs font-semibold">
                          <CheckCircle2 size={14} /> Pagado
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-gray-400 text-xs font-semibold">
                          <XCircle size={14} /> No pagado
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center print:hidden">
                      <div className="flex gap-1 justify-center">
                        {!reg.pagado && item.estado_servicios === 'OK' && (
                          <button
                            onClick={() => marcarPagado(reg.id_registros_mensuales)}
                            className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition"
                          >
                            Cobrado
                          </button>
                        )}
                        {reg.pagado && (
                          <button
                            onClick={() => desmarcarPagado(reg.id_registros_mensuales)}
                            className="text-xs px-2 py-1 bg-gray-400 text-white rounded hover:bg-gray-500 transition"
                          >
                            Desmarcar
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setOverrideModal(item)
                            setOverrideData({
                              alquiler_override: reg.alquiler_override?.toString() ?? '',
                              expensa_override: reg.expensa_override?.toString() ?? '',
                              nota_override: reg.nota_override ?? '',
                            })
                          }}
                          className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-gray-100 transition text-white"
                        >
                          Ajuste
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {visibles.length === 0 && !loading && (
            <div className="py-8 text-center text-gray-400">
              {showPagados ? 'No hay cobros este mes.' : 'Todos los cobros están pagados. Activá "Mostrar pagados" para verlos.'}
            </div>
          )}
        </div>
      )}

      {/* Override Modal */}
      {overrideModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 print:hidden">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <h3 className="font-bold text-lg mb-4">
              Ajuste del mes — {overrideModal.departamento?.piso} {overrideModal.departamento?.codigo}
            </h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Alquiler (dejar vacío para usar calculado: {formatMoneda(overrideModal.registro.alquiler_calculado)})
                </label>
                <input
                  type="number"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={overrideData.alquiler_override}
                  onChange={e => setOverrideData(d => ({ ...d, alquiler_override: e.target.value }))}
                  placeholder="Ej: 150000"
                />
              </div>
              {overrideModal.contrato.cobra_expensa && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Expensa (dejar vacío para usar calculada)
                  </label>
                  <input
                    type="number"
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    value={overrideData.expensa_override}
                    onChange={e => setOverrideData(d => ({ ...d, expensa_override: e.target.value }))}
                    placeholder="Ej: 20000"
                  />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nota</label>
                <input
                  type="text"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={overrideData.nota_override}
                  onChange={e => setOverrideData(d => ({ ...d, nota_override: e.target.value }))}
                  placeholder="Motivo del ajuste..."
                />
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-5">
              <button onClick={() => setOverrideModal(null)} className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-100 text-white">
                Cancelar
              </button>
              <button onClick={guardarOverride} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Guardar ajuste
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
