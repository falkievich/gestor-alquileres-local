import { useEffect, useState } from 'react'
import api from '../lib/api'
import type { DashboardItem, Inquilino } from '../lib/types'
import { formatMoneda, MESES } from '../lib/types'
import { useToast, ModalShell } from '../lib/ui'
import {
  CheckCircle2, AlertCircle, XCircle, Eye, EyeOff,
  RefreshCw, Printer, HardDriveDownload, SlidersHorizontal, ListChecks, Filter
} from 'lucide-react'

function formatDepto(piso: string | undefined, codigo: string | undefined) {
  if (!piso || !codigo) return `${piso ?? ''} ${codigo ?? ''}`.trim()
  return `${piso} — ${codigo}`
}

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
  const toast = useToast()
  const [items, setItems] = useState<DashboardItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showPagados, setShowPagados] = useState(false)
  const [overrideModal, setOverrideModal] = useState<DashboardItem | null>(null)
  const [overrideData, setOverrideData] = useState({ alquiler_delta: '', expensa_delta: '', nota_override: '' })
  const [confirmarPagoModal, setConfirmarPagoModal] = useState<DashboardItem | null>(null)
  const [detalleAjusteModal, setDetalleAjusteModal] = useState<HistorialPagoItem | null>(null)

  // Ajuste masivo
  const [modoSeleccion, setModoSeleccion] = useState(false)
  const [seleccionados, setSeleccionados] = useState<Set<number>>(new Set())
  const [ajusteMasivoModal, setAjusteMasivoModal] = useState(false)
  const [ajusteMasivoData, setAjusteMasivoData] = useState({ alquiler_delta: '', nota_override: '' })

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
    try {
      await api.post(`/dashboard/registros/${id}/pagado`)
      toast('El cobro se registró correctamente')
      cargar()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al registrar el cobro'
      toast(msg, 'error')
    }
  }

  async function crearBackup() {
    try {
      const res = await api.post('/backup/')
      toast(`Backup creado: ${res.data.archivo}`)
    } catch {
      toast('Error al crear backup', 'error')
    }
  }

  async function guardarOverride() {
    if (!overrideModal) return
    const idReg = overrideModal.registro.id_registros_mensuales
    const params: Record<string, string | number> = {}
    if (overrideData.alquiler_delta !== '') {
      const delta = Number(overrideData.alquiler_delta)
      params.alquiler_override = overrideModal.registro.alquiler_calculado + delta
    }
    if (overrideData.expensa_delta !== '') {
      const delta = Number(overrideData.expensa_delta)
      params.expensa_override = (overrideModal.registro.expensa_calculada ?? 0) + delta
    }
    if (overrideData.nota_override !== '') params.nota_override = overrideData.nota_override
    await api.post(`/dashboard/registros/${idReg}/override`, null, { params })
    toast('Se guardó el ajuste correctamente')
    setOverrideModal(null)
    cargar()
  }

  async function restaurarOverride() {
    if (!overrideModal) return
    const idReg = overrideModal.registro.id_registros_mensuales
    await api.post(`/dashboard/registros/${idReg}/override`, null, { params: {} })
    toast('Se restauraron los valores originales')
    setOverrideModal(null)
    cargar()
  }

  async function guardarAjusteMasivo() {
    if (seleccionados.size === 0) return
    const delta = Number(ajusteMasivoData.alquiler_delta)
    const promises = Array.from(seleccionados).map(idReg => {
      const item = visibles.find(i => i.registro.id_registros_mensuales === idReg)
      if (!item) return Promise.resolve()
      const params: Record<string, string | number> = {
        alquiler_override: item.registro.alquiler_calculado + delta,
      }
      if (ajusteMasivoData.nota_override !== '') params.nota_override = ajusteMasivoData.nota_override
      return api.post(`/dashboard/registros/${idReg}/override`, null, { params })
    })
    await Promise.all(promises)
    toast('Ajuste masivo aplicado correctamente')
    setAjusteMasivoModal(false)
    setModoSeleccion(false)
    setSeleccionados(new Set())
    setAjusteMasivoData({ alquiler_delta: '', nota_override: '' })
    cargar()
  }

  function toggleSeleccion(idReg: number) {
    setSeleccionados(prev => {
      const next = new Set(prev)
      if (next.has(idReg)) next.delete(idReg)
      else next.add(idReg)
      return next
    })
  }

  function toggleTodos() {
    if (seleccionados.size === visibles.length) {
      setSeleccionados(new Set())
    } else {
      setSeleccionados(new Set(visibles.map(i => i.registro.id_registros_mensuales)))
    }
  }

  function cancelarModoSeleccion() {
    setModoSeleccion(false)
    setSeleccionados(new Set())
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
          {!showPagados && mesActual && (
            <p className="text-3xl font-extrabold text-blue-700 mt-1">Mes actual: {mesActual}</p>
          )}
        </div>
        <div className="flex gap-2 flex-wrap justify-end">
          <button
            onClick={() => setShowPagados(!showPagados)}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition"
          >
            {showPagados ? <EyeOff size={16} /> : <Eye size={16} />}
            {showPagados ? 'Ocultar pagados' : 'Mostrar pagados'}
          </button>
          {!showPagados && !modoSeleccion && (
            <button
              onClick={() => setModoSeleccion(true)}
              className="flex items-center gap-2 px-3 py-2 text-sm bg-yellow-50 border border-yellow-300 text-yellow-700 rounded-lg hover:bg-yellow-100 transition"
            >
              <ListChecks size={16} /> Ajuste masivo
            </button>
          )}
          {!showPagados && modoSeleccion && (
            <>
              <button
                onClick={cancelarModoSeleccion}
                className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-100 transition"
              >
                <XCircle size={16} /> Cancelar selección
              </button>
              <button
                onClick={() => {
                  if (seleccionados.size === 0) return
                  setAjusteMasivoData({ alquiler_delta: '', nota_override: '' })
                  setAjusteMasivoModal(true)
                }}
                disabled={seleccionados.size === 0}
                className="flex items-center gap-2 px-3 py-2 text-sm bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                <SlidersHorizontal size={16} /> Ajustar seleccionados ({seleccionados.size})
              </button>
            </>
          )}
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
              className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium bg-slate-700 text-white rounded-lg hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-300 transition"
            >
              <Filter size={14} /> Filtrar
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

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-x-auto">
            {historialLoading ? (
              <div className="py-12 text-center text-gray-500">Cargando...</div>
            ) : historial.length === 0 ? (
              <div className="py-12 text-center text-gray-400">No hay pagos registrados con esos filtros.</div>
            ) : (
              <>
                <table className="w-full text-sm min-w-[820px]">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="text-center px-4 py-3 font-semibold text-gray-600">Mes / Año</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Depto</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Inquilino</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Alquiler</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Expensa</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Agua</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Luz</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Impuesto</th>
                      <th className="text-center px-4 py-3 font-semibold text-gray-600">Total</th>
                      <th className="text-center px-4 py-3 font-semibold text-gray-600 print:hidden">Acción</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {historial.map(h => {
                      const reg = h.registro
                      const alq = reg.alquiler_override ?? reg.alquiler_calculado
                      const exp = reg.expensa_override ?? reg.expensa_calculada
                      return (
                        <tr key={reg.id_registros_mensuales} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-center">
                            <span className="font-semibold text-gray-800">{MESES[h.mes - 1]}</span>
                            <span className="text-gray-500 ml-1">{h.anio}</span>
                          </td>
                          <td className="px-4 py-3 font-medium text-gray-800">
                            {formatDepto(h.departamento?.piso, h.departamento?.codigo)}
                            {(reg.alquiler_override != null || reg.expensa_override != null) && (
                              <span className="ml-2 inline-block text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded font-semibold">
                                Ajustado
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-gray-700">{h.inquilino?.nombre_apellido}</td>
                    <td className="px-4 py-3 text-left font-mono whitespace-nowrap">{formatMoneda(alq)}</td>
                          <td className="px-4 py-3 text-left font-mono whitespace-nowrap">
                            {h.contrato.cobra_expensa ? formatMoneda(exp) : <span className="text-gray-400">-</span>}
                          </td>
                          <td className="px-4 py-3 text-left font-mono whitespace-nowrap">
                            {h.contrato.cobra_agua ? (reg.agua != null ? formatMoneda(reg.agua) : <span className="text-gray-400">-</span>) : <span className="text-gray-400">-</span>}
                          </td>
                          <td className="px-4 py-3 text-left font-mono whitespace-nowrap">
                            {h.contrato.cobra_luz ? (reg.luz != null ? formatMoneda(reg.luz) : <span className="text-gray-400">-</span>) : <span className="text-gray-400">-</span>}
                          </td>
                          <td className="px-4 py-3 text-left font-mono whitespace-nowrap">
                            {reg.impuesto != null ? formatMoneda(reg.impuesto) : <span className="text-gray-400">-</span>}
                          </td>
                          <td className="px-4 py-3 text-center font-bold font-mono text-green-700">{formatMoneda(h.total)}</td>
                          <td className="px-4 py-3 text-center print:hidden">
                            {(reg.alquiler_override != null || reg.expensa_override != null) && (
                              <button
                                onClick={() => setDetalleAjusteModal(h)}
                                className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-yellow-50 border border-yellow-300 text-yellow-700 rounded hover:bg-yellow-100 transition"
                              >
                                <SlidersHorizontal size={12} /> Ver ajuste
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </>
            )}
          </div>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          No hay contratos activos para el mes actual.
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-x-auto">
          {/* Print header */}
          <div className="hidden print:block p-4 border-b">
            <h2 className="text-xl font-bold">Cobros — {mesActual}</h2>
          </div>

          <table className="tabla-cobros w-full text-sm min-w-[760px]">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {modoSeleccion && (
                  <th className="px-4 py-3 print:hidden">
                    <input
                      type="checkbox"
                      className="w-4 h-4 rounded accent-yellow-500 cursor-pointer"
                      checked={seleccionados.size === visibles.length && visibles.length > 0}
                      onChange={toggleTodos}
                      title="Seleccionar todos"
                    />
                  </th>
                )}
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Depto</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Inquilino</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Alquiler</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Expensa</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Agua</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Luz</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Impuesto</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Total</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600 col-servicios-impresion">Servicios</th>
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
                  <tr
                    key={reg.id_registros_mensuales}
                    className={`hover:bg-gray-50 ${modoSeleccion && seleccionados.has(reg.id_registros_mensuales) ? 'bg-yellow-50' : ''}`}
                    onClick={modoSeleccion ? () => toggleSeleccion(reg.id_registros_mensuales) : undefined}
                    style={modoSeleccion ? { cursor: 'pointer' } : undefined}
                  >
                    {modoSeleccion && (
                      <td className="px-4 py-3 print:hidden" onClick={e => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          className="w-4 h-4 rounded accent-yellow-500 cursor-pointer"
                          checked={seleccionados.has(reg.id_registros_mensuales)}
                          onChange={() => toggleSeleccion(reg.id_registros_mensuales)}
                        />
                      </td>
                    )}
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-800">
                        {formatDepto(item.departamento?.piso, item.departamento?.codigo)}
                      </div>
                      {item.departamento?.direccion && (
                        <div className="text-xs text-gray-400 truncate max-w-[180px]" title={item.departamento.direccion}>
                          {item.departamento.direccion}
                        </div>
                      )}
                      <div className="flex gap-1 mt-1 flex-wrap">
                        {item.vencido && (
                          <span className="inline-block text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded font-semibold">
                            Vencido
                          </span>
                        )}
                        {(reg.alquiler_override != null || reg.expensa_override != null) && (
                          <span className="inline-block text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded font-semibold">
                            Ajustado
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-700">{item.inquilino?.nombre_apellido}</td>
                    <td className="px-4 py-3 text-left font-mono whitespace-nowrap">{formatMoneda(alq)}</td>
                    <td className="px-4 py-3 text-left font-mono whitespace-nowrap">{item.contrato.cobra_expensa ? formatMoneda(exp) : <span className="text-gray-400">-</span>}</td>
                    <td className="px-4 py-3 text-left font-mono whitespace-nowrap">
                      {item.contrato.cobra_agua ? (reg.agua != null ? formatMoneda(reg.agua) : <span className="text-orange-500">Pend.</span>) : <span className="text-gray-400">-</span>}
                    </td>
                    <td className="px-4 py-3 text-left font-mono whitespace-nowrap">
                      {item.contrato.cobra_luz ? (reg.luz != null ? formatMoneda(reg.luz) : <span className="text-orange-500">Pend.</span>) : <span className="text-gray-400">-</span>}
                    </td>
                    <td className="px-4 py-3 text-left font-mono whitespace-nowrap">
                      {reg.impuesto != null ? formatMoneda(reg.impuesto) : <span className="text-gray-400">-</span>}
                    </td>
                    <td className="px-4 py-3 text-center font-bold font-mono">{formatMoneda(item.total)}</td>
                    <td className="px-4 py-3 text-center col-servicios-impresion">
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
                      <div className="flex gap-1 justify-center whitespace-nowrap">
                        {!reg.pagado && item.estado_servicios === 'OK' && (
                          <button
                            onClick={() => setConfirmarPagoModal(item)}
                            className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition"
                          >
                            Cobrado
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setOverrideModal(item)
                            // Convert existing absolute override back to delta for display
                            const alqDelta = reg.alquiler_override != null
                              ? (reg.alquiler_override - reg.alquiler_calculado).toString()
                              : ''
                            const expDelta = reg.expensa_override != null
                              ? (reg.expensa_override - (reg.expensa_calculada ?? 0)).toString()
                              : ''
                            setOverrideData({
                              alquiler_delta: alqDelta,
                              expensa_delta: expDelta,
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

      {/* Modal ajuste masivo */}
      {ajusteMasivoModal && (() => {
        const delta = ajusteMasivoData.alquiler_delta !== '' ? Number(ajusteMasivoData.alquiler_delta) : 0
        const itemsSeleccionados = visibles.filter(i => seleccionados.has(i.registro.id_registros_mensuales))
        return (
          <ModalShell max="max-w-lg">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-yellow-100 flex items-center justify-center">
                  <ListChecks size={20} className="text-yellow-600" />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-gray-800">Ajuste masivo</h3>
                  <p className="text-sm text-gray-500">{itemsSeleccionados.length} pago{itemsSeleccionados.length !== 1 ? 's' : ''} seleccionado{itemsSeleccionados.length !== 1 ? 's' : ''}</p>
                </div>
              </div>

              {/* Lista de afectados */}
              <div className="mb-4 max-h-36 overflow-y-auto rounded-lg border border-gray-200 divide-y divide-gray-100">
                {itemsSeleccionados.map(i => (
                  <div key={i.registro.id_registros_mensuales} className="flex items-center justify-between px-3 py-2 text-sm">
                    <span className="font-medium text-gray-700">{formatDepto(i.departamento?.piso, i.departamento?.codigo)}</span>
                    <span className="text-gray-500">{i.inquilino?.nombre_apellido}</span>
                    {delta !== 0 && ajusteMasivoData.alquiler_delta !== '' ? (
                      <span className="flex items-center gap-1.5 font-mono text-xs font-semibold">
                        <span className="text-gray-800">{formatMoneda(i.registro.alquiler_calculado)}</span>
                        <span className={delta >= 0 ? 'text-green-600' : 'text-red-600'}>
                          → {formatMoneda(i.registro.alquiler_calculado + delta)}
                        </span>
                      </span>
                    ) : (
                      <span className="font-mono text-xs text-gray-400">{formatMoneda(i.registro.alquiler_calculado)}</span>
                    )}
                  </div>
                ))}
              </div>

              <p className="text-sm text-gray-500 mb-3">
                Ingresá el monto a <strong>sumar o restar</strong> al alquiler base de cada pago seleccionado.
                Usá un número negativo para aplicar un descuento.
              </p>

              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ajuste de alquiler
                  </label>
                  <input
                    type="number"
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    value={ajusteMasivoData.alquiler_delta}
                    onChange={e => setAjusteMasivoData(d => ({ ...d, alquiler_delta: e.target.value }))}
                    placeholder="Ej: 50000 o -30000"
                  />
                  {ajusteMasivoData.alquiler_delta !== '' && (
                    <p className={`text-xs mt-1 ${delta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      Se {delta >= 0 ? 'sumará' : 'restará'} {formatMoneda(Math.abs(delta))} al alquiler de cada pago seleccionado.
                    </p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nota (opcional)</label>
                  <textarea
                    rows={3}
                    className="w-full border rounded-lg px-3 py-2 text-sm resize-y"
                    value={ajusteMasivoData.nota_override}
                    onChange={e => setAjusteMasivoData(d => ({ ...d, nota_override: e.target.value }))}
                    placeholder="Motivo del ajuste..."
                  />
                </div>
              </div>

              <div className="flex gap-2 justify-end mt-5">
                <button
                  onClick={() => setAjusteMasivoModal(false)}
                  className="px-4 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100"
                >
                  Cancelar
                </button>
                <button
                  onClick={guardarAjusteMasivo}
                  disabled={ajusteMasivoData.alquiler_delta === ''}
                  className="px-4 py-2 text-sm bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Aplicar ajuste
                </button>
              </div>
            </div>
          </ModalShell>
        )
      })()}

      {/* Override Modal */}
      {overrideModal && (() => {
        const reg = overrideModal.registro
        const alqBase = reg.alquiler_calculado
        const expBase = reg.expensa_calculada ?? 0
        const alqDelta = overrideData.alquiler_delta !== '' ? Number(overrideData.alquiler_delta) : 0
        const expDelta = overrideData.expensa_delta !== '' ? Number(overrideData.expensa_delta) : 0
        const alqFinal = alqBase + alqDelta
        const expFinal = expBase + expDelta
        const tieneOverride = reg.alquiler_override != null || reg.expensa_override != null
        return (
        <ModalShell max="max-w-lg">
          <div className="p-6">
            <h3 className="font-bold text-lg mb-1">
              Ajuste del mes — {formatDepto(overrideModal.departamento?.piso, overrideModal.departamento?.codigo)}
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              Ingresá el monto a <strong>sumar o restar</strong> al valor base de este mes.
              Usá un número negativo para aplicar un descuento. Dejá vacío si no querés ajustar.
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ajuste alquiler · Base: {formatMoneda(alqBase)}
                </label>
                <input
                  type="number"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={overrideData.alquiler_delta}
                  onChange={e => setOverrideData(d => ({ ...d, alquiler_delta: e.target.value }))}
                  placeholder="Ej: 50000 o -30000"
                />
                {overrideData.alquiler_delta !== '' && (
                  <p className={`text-xs mt-1 ${alqDelta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    Resultado: {formatMoneda(alqFinal)} ({alqDelta >= 0 ? '+' : ''}{formatMoneda(alqDelta)})
                  </p>
                )}
              </div>
              {overrideModal.contrato.cobra_expensa && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ajuste expensa · Base: {formatMoneda(expBase)}
                  </label>
                  <input
                    type="number"
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    value={overrideData.expensa_delta}
                    onChange={e => setOverrideData(d => ({ ...d, expensa_delta: e.target.value }))}
                    placeholder="Ej: 5000 o -5000"
                  />
                  {overrideData.expensa_delta !== '' && (
                    <p className={`text-xs mt-1 ${expDelta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      Resultado: {formatMoneda(expFinal)} ({expDelta >= 0 ? '+' : ''}{formatMoneda(expDelta)})
                    </p>
                  )}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nota</label>
                <textarea
                  rows={3}
                  className="w-full border rounded-lg px-3 py-2 text-sm resize-y"
                  value={overrideData.nota_override}
                  onChange={e => setOverrideData(d => ({ ...d, nota_override: e.target.value }))}
                  placeholder="Motivo del ajuste..."
                />
              </div>
            </div>
            <div className="flex gap-2 justify-between mt-5">
              <div>
                {tieneOverride && (
                  <button onClick={restaurarOverride} className="px-4 py-2 text-sm bg-orange-50 border border-orange-300 text-orange-700 rounded-lg hover:bg-orange-100">
                    Restaurar original
                  </button>
                )}
              </div>
              <div className="flex gap-2">
                <button onClick={() => setOverrideModal(null)} className="px-4 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100">
                  Cancelar
                </button>
                <button onClick={guardarOverride} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                  Guardar ajuste
                </button>
              </div>
            </div>
            </div>
          </ModalShell>
        )
      })()}

      {/* Modal detalle de ajuste (historial) */}
      {detalleAjusteModal && (() => {
        const h = detalleAjusteModal
        const reg = h.registro
        const tieneAlqAjuste = reg.alquiler_override != null
        const tieneExpAjuste = reg.expensa_override != null
        return (
          <ModalShell max="max-w-lg">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-yellow-100 flex items-center justify-center">
                  <SlidersHorizontal size={20} className="text-yellow-600" />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-gray-800">Detalle del ajuste</h3>
                  <p className="text-sm text-gray-500">
                    {MESES[h.mes - 1]} {h.anio} · {formatDepto(h.departamento?.piso, h.departamento?.codigo)}
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                {/* Alquiler */}
                <div className="rounded-lg border border-gray-200 overflow-hidden">
                  <div className="bg-gray-50 px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Alquiler</div>
                  <div className="px-4 py-3 grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-xs text-gray-400 mb-0.5">Valor original</p>
                      <p className="font-mono font-semibold text-gray-700">{formatMoneda(reg.alquiler_calculado)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400 mb-0.5">Valor cobrado</p>
                      {tieneAlqAjuste ? (
                        <div>
                          <p className="font-mono font-semibold text-yellow-700">{formatMoneda(reg.alquiler_override!)}</p>
                          <p className={`text-xs mt-0.5 ${(reg.alquiler_override! - reg.alquiler_calculado) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {(reg.alquiler_override! - reg.alquiler_calculado) >= 0 ? '+' : ''}{formatMoneda(reg.alquiler_override! - reg.alquiler_calculado)}
                          </p>
                        </div>
                      ) : (
                        <p className="font-mono font-semibold text-gray-400">Sin ajuste</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Expensa (solo si cobra) */}
                {h.contrato.cobra_expensa && (
                  <div className="rounded-lg border border-gray-200 overflow-hidden">
                    <div className="bg-gray-50 px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Expensa</div>
                    <div className="px-4 py-3 grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <p className="text-xs text-gray-400 mb-0.5">Valor original</p>
                        <p className="font-mono font-semibold text-gray-700">{formatMoneda(reg.expensa_calculada)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 mb-0.5">Valor cobrado</p>
                        {tieneExpAjuste ? (
                          <div>
                            <p className="font-mono font-semibold text-yellow-700">{formatMoneda(reg.expensa_override!)}</p>
                            <p className={`text-xs mt-0.5 ${(reg.expensa_override! - (reg.expensa_calculada ?? 0)) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {(reg.expensa_override! - (reg.expensa_calculada ?? 0)) >= 0 ? '+' : ''}{formatMoneda(reg.expensa_override! - (reg.expensa_calculada ?? 0))}
                            </p>
                          </div>
                        ) : (
                          <p className="font-mono font-semibold text-gray-400">Sin ajuste</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Nota */}
                {reg.nota_override && (
                  <div className="rounded-lg bg-yellow-50 border border-yellow-200 px-4 py-3">
                    <p className="text-xs font-semibold text-yellow-700 mb-1">Nota del ajuste</p>
                    <p className="text-sm text-yellow-800">{reg.nota_override}</p>
                  </div>
                )}
              </div>

              <div className="mt-5 flex justify-end">
                <button
                  onClick={() => setDetalleAjusteModal(null)}
                  className="px-4 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100"
                >
                  Cerrar
                </button>
              </div>
            </div>
          </ModalShell>
        )
      })()}

      {/* Modal confirmación cobro */}
      {confirmarPagoModal && (() => {
        const item = confirmarPagoModal
        const reg = item.registro
        const dep = item.departamento
        const depLabel = [dep?.piso && dep?.codigo ? `${dep.piso} — ${dep.codigo}` : [dep?.piso, dep?.codigo].filter(Boolean).join(' '), dep?.direccion].filter(Boolean).join(' · ')
        return (
          <ModalShell max="max-w-lg">
            <div className="p-6">
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
              <div className="bg-gray-50 rounded-lg px-4 py-3 mb-5 text-sm">
                <div className="flex justify-between py-0.5">
                  <span className="text-gray-500">Alquiler</span>
                  <span className="font-mono text-gray-700">{formatMoneda(reg.alquiler_override ?? reg.alquiler_calculado)}</span>
                </div>
                {item.contrato.cobra_expensa && (
                  <div className="flex justify-between py-0.5">
                    <span className="text-gray-500">Expensa</span>
                    <span className="font-mono text-gray-700">{formatMoneda(reg.expensa_override ?? reg.expensa_calculada)}</span>
                  </div>
                )}
                {item.contrato.cobra_agua && reg.agua != null && (
                  <div className="flex justify-between py-0.5">
                    <span className="text-gray-500">Agua</span>
                    <span className="font-mono text-gray-700">{formatMoneda(reg.agua)}</span>
                  </div>
                )}
                {item.contrato.cobra_luz && reg.luz != null && (
                  <div className="flex justify-between py-0.5">
                    <span className="text-gray-500">Luz</span>
                    <span className="font-mono text-gray-700">{formatMoneda(reg.luz)}</span>
                  </div>
                )}
                {reg.impuesto != null && (
                  <div className="flex justify-between py-0.5">
                    <span className="text-gray-500">Impuesto</span>
                    <span className="font-mono text-gray-700">{formatMoneda(reg.impuesto)}</span>
                  </div>
                )}
                <div className="flex justify-between border-t border-gray-200 mt-2 pt-2">
                  <span className="text-xs text-gray-500 uppercase tracking-wide font-semibold">Total</span>
                  <span className="text-xl font-bold text-gray-800">{formatMoneda(item.total)}</span>
                </div>
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
          </ModalShell>
        )
      })()}
    </div>
  )
}
