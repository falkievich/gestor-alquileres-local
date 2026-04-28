import { useEffect, useState } from 'react'
import api from '../lib/api'
import type { DashboardItem, Inquilino } from '../lib/types'
import { formatMoneda, MESES } from '../lib/types'
import {
  CheckCircle2, AlertCircle, XCircle, Eye, EyeOff,
  RefreshCw, Printer, HardDriveDownload
} from 'lucide-react'

interface HistorialPagoItem {
  registro: DashboardItem['registro']
  contrato: DashboardItem['contrato']
  departamento: DashboardItem['departamento']
  inquilino: DashboardItem['inquilino']
  anio: number
  mes: number
  total: number
}

export default function Dashboard() {
  const [items, setItems] = useState<DashboardItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showPagados, setShowPagados] = useState(false)
  const [backupMsg, setBackupMsg] = useState('')
  const [overrideModal, setOverrideModal] = useState<DashboardItem | null>(null)
  const [overrideData, setOverrideData] = useState({ alquiler_override: '', expensa_override: '', nota_override: '' })
  const [confirmarPagoModal, setConfirmarPagoModal] = useState<DashboardItem | null>(null)

  // Historial de pagos
  const [historial, setHistorial] = useState<HistorialPagoItem[]>([])
  const [historialLoading, setHistorialLoading] = useState(false)
  const [filtroAnio, setFiltroAnio] = useState('')
  const [filtroMes, setFiltroMes] = useState('')
  const [filtroInquilino, setFiltroInquilino] = useState('')
  const [inquilinos, setInquilinos] = useState<Inquilino[]>([])

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

  async function cargarHistorial() {
    setHistorialLoading(true)
    try {
      const params: Record<string, string> = {}
      if (filtroAnio) params.anio = filtroAnio
      if (filtroMes) params.mes = filtroMes
      if (filtroInquilino) params.id_inquilinos = filtroInquilino
      const res = await api.get('/dashboard/historial-pagos', { params })
      setHistorial(res.data)
    } finally {
      setHistorialLoading(false)
    }
  }

  useEffect(() => { cargar() }, [])

  useEffect(() => {
    api.get('/inquilinos/').then(res => setInquilinos(res.data))
  }, [])

  useEffect(() => {
    if (showPagados) cargarHistorial()
  }, [showPagados])

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

  const visibles = items.filter(i => !i.registro.pagado)
  const mesActual = items.length > 0 ? `${MESES[items[0].mes - 1]} ${items[0].anio}` : ''

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 print:hidden">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">{showPagados ? 'Historial de pagos' : 'Dashboard'}</h2>
          {!showPagados && mesActual && <p className="text-gray-500 text-sm mt-1">Mes actual: {mesActual}</p>}
        </div>
        <div className="flex gap-2 flex-wrap justify-end">
          <button
            onClick={() => setShowPagados(!showPagados)}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition"
          >
            {showPagados ? <EyeOff size={16} /> : <Eye size={16} />}
            {showPagados ? 'Ocultar pagados' : 'Mostrar pagados'}
          </button>
          <button onClick={handleImprimir} className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-700 text-white rounded-lg hover:bg-gray-800 transition">
            <Printer size={16} /> Imprimir
          </button>
          <button onClick={cargar} className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition">
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
      ) : showPagados ? (
        /* ── VISTA HISTORIAL DE PAGOS ── */
        <div>
          {/* Barra de filtros */}
          <div className="flex flex-wrap gap-3 mb-4 items-end print:hidden">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500">Año</label>
              <select
                className="border rounded-lg px-3 py-2 text-sm min-w-[110px]"
                value={filtroAnio}
                onChange={e => setFiltroAnio(e.target.value)}
              >
                <option value="">Todos</option>
                {[2024, 2025, 2026, 2027, 2028, 2029, 2030].map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500">Mes</label>
              <select
                className="border rounded-lg px-3 py-2 text-sm min-w-[130px]"
                value={filtroMes}
                onChange={e => setFiltroMes(e.target.value)}
              >
                <option value="">Todos</option>
                {MESES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500">Inquilino</label>
              <select
                className="border rounded-lg px-3 py-2 text-sm min-w-[200px]"
                value={filtroInquilino}
                onChange={e => setFiltroInquilino(e.target.value)}
              >
                <option value="">Todos</option>
                {inquilinos.map(inq => (
                  <option key={inq.id_inquilinos} value={inq.id_inquilinos}>
                    {inq.nombre_apellido}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={cargarHistorial}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              <RefreshCw size={14} /> Filtrar
            </button>
            {(filtroAnio || filtroMes || filtroInquilino) && (
              <button
                onClick={() => {
                  setFiltroAnio('')
                  setFiltroMes('')
                  setFiltroInquilino('')
                  setTimeout(cargarHistorial, 0)
                }}
                className="flex items-center gap-1 px-3 py-2 text-sm bg-white border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-100 transition"
              >
                <XCircle size={14} /> Limpiar filtros
              </button>
            )}
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            {historialLoading ? (
              <div className="py-12 text-center text-gray-500">Cargando...</div>
            ) : historial.length === 0 ? (
              <div className="py-12 text-center text-gray-400">No hay pagos registrados con esos filtros.</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Mes / Año</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Depto</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Inquilino</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-600">Alquiler</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-600">Expensa</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-600">Agua</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-600">Luz</th>
                    <th className="text-center px-4 py-3 font-semibold text-gray-600">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {historial.map(h => {
                    const reg = h.registro
                    const alq = reg.alquiler_override ?? reg.alquiler_calculado
                    const exp = reg.expensa_override ?? reg.expensa_calculada
                    return (
                      <tr key={reg.id_registros_mensuales} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <span className="font-semibold text-gray-800">{MESES[h.mes - 1]}</span>
                          <span className="text-gray-500 ml-1">{h.anio}</span>
                        </td>
                        <td className="px-4 py-3 font-medium text-gray-800">
                          {h.departamento?.piso} {h.departamento?.codigo}
                        </td>
                        <td className="px-4 py-3 text-gray-700">{h.inquilino?.nombre_apellido}</td>
                        <td className="px-4 py-3 text-right font-mono">{formatMoneda(alq)}</td>
                        <td className="px-4 py-3 text-right font-mono">
                          {h.contrato.cobra_expensa ? formatMoneda(exp) : <span className="text-gray-400">-</span>}
                        </td>
                        <td className="px-4 py-3 text-right font-mono">
                          {h.contrato.cobra_agua ? (reg.agua != null ? formatMoneda(reg.agua) : <span className="text-gray-400">-</span>) : <span className="text-gray-400">-</span>}
                        </td>
                        <td className="px-4 py-3 text-right font-mono">
                          {h.contrato.cobra_luz ? (reg.luz != null ? formatMoneda(reg.luz) : <span className="text-gray-400">-</span>) : <span className="text-gray-400">-</span>}
                        </td>
                        <td className="px-4 py-3 text-center font-bold font-mono text-green-700">{formatMoneda(h.total)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
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
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Agua</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Luz</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Total</th>
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
                    <td className="px-4 py-3 text-center font-mono">
                      {item.contrato.cobra_agua ? (reg.agua != null ? formatMoneda(reg.agua) : <span className="text-orange-500">Pend.</span>) : <span className="text-gray-400">-</span>}
                    </td>
                    <td className="px-4 py-3 text-center font-mono">
                      {item.contrato.cobra_luz ? (reg.luz != null ? formatMoneda(reg.luz) : <span className="text-orange-500">Pend.</span>) : <span className="text-gray-400">-</span>}
                    </td>
                    <td className="px-4 py-3 text-center font-bold font-mono">{formatMoneda(item.total)}</td>
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
                        <div className="inline-flex flex-col items-center gap-0.5">
                          <span className="inline-flex items-center gap-1 text-blue-600 text-xs font-semibold">
                            <CheckCircle2 size={14} /> Pagado
                          </span>
                          <span className="text-xs text-blue-400">
                            {MESES[item.mes - 1]} {item.anio}
                          </span>
                        </div>
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
                            onClick={() => setConfirmarPagoModal(item)}
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
                          className="text-xs px-2 py-1 bg-white border border-gray-300 text-gray-700 rounded hover:bg-gray-100 transition"
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
              Todos los cobros del mes están pagados. Usá "Historial de pagos" para verlos.
            </div>
          )}
        </div>
      )}

      {/* Override Modal */}
      {overrideModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 print:hidden">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <h3 className="font-bold text-lg mb-1">
              Ajuste del mes — {overrideModal.departamento?.piso} {overrideModal.departamento?.codigo}
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              Usá este formulario para modificar el alquiler y/o la expensa <strong>solo por este mes</strong>,
              sin alterar los valores base del contrato ni los cálculos de meses futuros.
              Es útil para aplicar descuentos, acuerdos puntuales o correcciones extraordinarias.
              Dejá un campo vacío para que se use el valor calculado automáticamente.
            </p>
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
              <button onClick={() => setOverrideModal(null)} className="px-4 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100">
                Cancelar
              </button>
              <button onClick={guardarOverride} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Guardar ajuste
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal confirmación cobro */}
      {confirmarPagoModal && (() => {
        const item = confirmarPagoModal
        const dep = item.departamento
        const depLabel = [dep?.piso, dep?.codigo, dep?.direccion].filter(Boolean).join(' · ')
        return (
          <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 print:hidden">
            <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                  <CheckCircle2 size={20} className="text-green-600" />
                </div>
                <h3 className="font-bold text-lg text-gray-800">Confirmar cobro</h3>
              </div>
              <p className="text-sm text-gray-600 mb-1">
                ¿Confirmar que se cobró el alquiler de:
              </p>
              <p className="text-sm font-semibold text-gray-800 mb-0.5">
                {item.inquilino?.nombre_apellido}
              </p>
              <p className="text-sm text-gray-500 mb-3">{depLabel}</p>
              <div className="bg-gray-50 rounded-lg px-4 py-2 mb-5 text-center">
                <span className="text-xs text-gray-500 uppercase tracking-wide">Total a cobrar</span>
                <p className="text-2xl font-bold text-gray-800 mt-0.5">{formatMoneda(item.total)}</p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setConfirmarPagoModal(null)}
                  className="flex-1 px-4 py-2 text-sm border border-gray-300 bg-white text-gray-700 rounded-lg hover:bg-gray-100 hover:border-gray-400 transition font-medium"
                >
                  No, cancelar
                </button>
                <button
                  onClick={() => {
                    marcarPagado(item.registro.id_registros_mensuales)
                    setConfirmarPagoModal(null)
                  }}
                  className="flex-1 px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 transition font-semibold"
                >
                  Sí, cobrar
                </button>
              </div>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
