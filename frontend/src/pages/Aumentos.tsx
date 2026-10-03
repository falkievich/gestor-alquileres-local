import { useEffect, useState } from 'react'
import api from '../lib/api'
import type { AumentoItem, HistorialAumentoItem, Inquilino } from '../lib/types'
import { MESES, formatMoneda, formatFecha } from '../lib/types'
import {
  TrendingUp,
  AlertTriangle,
  XCircle,
  Clock,
  CheckCircle2,
  History,
  Filter,
} from 'lucide-react'

function formatDepto(piso: string | undefined, codigo: string | undefined) {
  if (!piso || !codigo) return `${piso ?? ''} ${codigo ?? ''}`.trim()
  return `${piso} — ${codigo}`
}

function proximoLabel(item: AumentoItem) {
  const p = item.proximo_aumento
  if (!p.proximo_mes || !p.proximo_anio) return '-'
  return `${MESES[p.proximo_mes - 1]} ${p.proximo_anio}`
}

function TipoBadge({ tipo }: { tipo?: string }) {
  if (tipo === 'ICL') {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">
        ICL
      </span>
    )
  }
  if (tipo === 'SIN_AUMENTO') {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-200 text-gray-600">
        SIN AUMENTO
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
      MANUAL
    </span>
  )
}

function EstadoAumentoBadge({ estado }: { estado: string }) {
  return (
    <span className={`inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full ${
      estado === 'CONSOLIDADO' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
    }`}>
      {estado}
    </span>
  )
}

function ProximosAumentos({ items }: { items: AumentoItem[] }) {
  if (items.length === 0) {
    return <div className="text-center py-12 text-gray-400 text-lg">No hay contratos activos.</div>
  }

  return (
    <div className="space-y-3">
      {items.map(item => {
        const p = item.proximo_aumento
        const esICL = (p.tipo_aumento ?? item.contrato.tipo_aumento) === 'ICL'
        const iclPendiente = esICL && p.icl_pendiente
        const iclCalculado = esICL && !iclPendiente && !!p.icl_calculado
        const fueraDeContrato = !!p.aumento_fuera_de_contrato
        const diferencia = p.alquiler_nuevo != null ? p.alquiler_nuevo - p.alquiler_actual : null
        const porcentaje = p.porcentaje
        const diferenciaExpensa = p.expensa_nueva != null && p.expensa_actual != null
          ? p.expensa_nueva - p.expensa_actual
          : null

        return (
          <div
            key={item.contrato.id_contratos}
            className={`rounded-xl shadow-sm overflow-hidden border ${
              fueraDeContrato
                ? 'bg-red-50 border-red-300'
                : 'bg-white border-gray-200'
            }`}
          >
            <div className="px-5 py-4">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-gray-800">
                      {formatDepto(item.departamento?.piso, item.departamento?.codigo)}
                    </span>
                    <TipoBadge tipo={p.tipo_aumento ?? item.contrato.tipo_aumento} />
                    {item.alerta === 'Vencido' && (
                      <span className="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 font-semibold">
                        <XCircle size={11} /> Vencido
                      </span>
                    )}
                    {item.alerta === 'Por vencer' && (
                      <span className="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full bg-yellow-100 text-yellow-700 font-semibold">
                        <AlertTriangle size={11} /> Por vencer
                      </span>
                    )}
                    {fueraDeContrato && (
                      <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-red-200 text-red-800 font-semibold">
                        <XCircle size={11} /> Sin más aumentos
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500 mt-0.5">
                    {item.inquilino?.nombre_apellido}
                    {item.departamento?.direccion && (
                      <span className="text-gray-400"> · {item.departamento.direccion}</span>
                    )}
                  </div>
                </div>

                <div className="shrink-0 text-right">
                  <div className="flex items-center gap-1.5 justify-end text-sm font-medium text-gray-700">
                    <TrendingUp size={14} className="text-blue-500" />
                    {proximoLabel(item)}
                  </div>
                  <div className="text-xs mt-1">
                    {p.requires_fecha_ultimo ? (
                      <span className="flex items-center gap-1 justify-end text-amber-600"><AlertTriangle size={11} /> Falta fecha</span>
                    ) : (p.tipo_aumento ?? item.contrato.tipo_aumento) === 'SIN_AUMENTO' ? (
                      <span className="text-gray-500">Sin aumentos</span>
                    ) : !p.alquiler_nuevo && !iclPendiente ? (
                      <span className="text-gray-400">Sin aumento</span>
                    ) : iclPendiente ? (
                      <span className="flex items-center gap-1 justify-end text-amber-600"><Clock size={11} /> ICL pendiente</span>
                    ) : iclCalculado ? (
                      <span className="flex items-center gap-1 justify-end text-sky-700"><CheckCircle2 size={11} /> ICL calculado</span>
                    ) : (
                      <span className="flex items-center gap-1 justify-end text-green-600"><CheckCircle2 size={11} /> Aplicado</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-3">
                <div className={`bg-gray-50 rounded-lg px-3 py-2.5 ${item.contrato.cobra_expensa && p.expensa_actual != null ? 'row-span-2' : ''}`}>
                  <p className="text-xs text-gray-400 mb-0.5">Periodicidad</p>
                  <p className="text-sm font-medium text-gray-700">{item.contrato.periodicidad_aumento_meses} meses</p>
                </div>
                <div className="bg-gray-50 rounded-lg px-3 py-2.5">
                  <p className="text-xs text-gray-400 mb-0.5">Alquiler actual</p>
                  <p className="text-sm font-mono font-semibold text-gray-800">{formatMoneda(p.alquiler_actual)}</p>
                </div>
                <div className={`rounded-lg px-3 py-2.5 ${iclPendiente ? 'bg-amber-50' : p.alquiler_nuevo ? 'bg-blue-50' : 'bg-gray-50'}`}>
                  <p className="text-xs text-gray-400 mb-0.5">Alquiler nuevo</p>
                  {iclPendiente ? (
                    <span className="text-amber-600 text-sm flex items-center gap-1"><Clock size={12} /> Pendiente</span>
                  ) : p.alquiler_nuevo != null ? (
                    <p className="text-sm font-mono font-semibold text-blue-700">{formatMoneda(p.alquiler_nuevo)}</p>
                  ) : (
                    <p className="text-sm text-gray-400">-</p>
                  )}
                </div>
                <div className={`rounded-lg px-3 py-2.5 ${!iclPendiente && diferencia != null ? 'bg-green-50' : 'bg-gray-50'}`}>
                  <p className="text-xs text-gray-400 mb-0.5">Diferencia</p>
                  {iclPendiente ? (
                    <p className="text-sm text-gray-400">-</p>
                  ) : diferencia != null ? (
                    <div>
                      <p className="text-sm font-mono font-semibold text-green-600">+{formatMoneda(diferencia)}</p>
                      {porcentaje != null && <p className="text-xs text-gray-400">{porcentaje.toFixed(2)}%</p>}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-400">-</p>
                  )}
                </div>

                {item.contrato.cobra_expensa && p.expensa_actual != null && (
                  <>
                    <div className="bg-gray-50 rounded-lg px-3 py-2.5">
                      <p className="text-xs text-gray-400 mb-0.5">Expensa actual</p>
                      <p className="text-sm font-mono font-semibold text-gray-800">{formatMoneda(p.expensa_actual)}</p>
                    </div>
                    <div className={`rounded-lg px-3 py-2.5 ${iclPendiente ? 'bg-amber-50' : p.expensa_nueva ? 'bg-blue-50' : 'bg-gray-50'}`}>
                      <p className="text-xs text-gray-400 mb-0.5">Expensa nueva</p>
                      {iclPendiente ? (
                        <span className="text-amber-600 text-sm flex items-center gap-1"><Clock size={12} /> Pendiente</span>
                      ) : p.expensa_nueva != null ? (
                        <p className="text-sm font-mono font-semibold text-blue-700">{formatMoneda(p.expensa_nueva)}</p>
                      ) : (
                        <p className="text-sm text-gray-400">-</p>
                      )}
                    </div>
                    <div className={`rounded-lg px-3 py-2.5 ${!iclPendiente && diferenciaExpensa != null ? 'bg-green-50' : 'bg-gray-50'}`}>
                      <p className="text-xs text-gray-400 mb-0.5">Diferencia</p>
                      {diferenciaExpensa != null && !iclPendiente ? (
                        <div>
                          <p className="text-sm font-mono font-semibold text-green-600">+{formatMoneda(diferenciaExpensa)}</p>
                          {porcentaje != null && <p className="text-xs text-gray-400">{porcentaje.toFixed(2)}%</p>}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-400">-</p>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>

            {p.requires_fecha_ultimo && (
              <div className="px-5 pb-4">
                <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                  <AlertTriangle size={15} className="shrink-0 mt-0.5 text-amber-500" />
                  <span>
                    Este contrato ya lleva un tiempo en curso pero no tiene registrado el último aumento.
                    Edita el contrato e indica la fecha del último aumento para que el sistema calcule correctamente el próximo.
                  </span>
                </div>
              </div>
            )}

            {fueraDeContrato && (
              <div className="px-5 pb-4">
                <div className="flex items-start gap-2 p-3 bg-red-100 border border-red-300 rounded-lg text-sm text-red-800">
                  <XCircle size={15} className="shrink-0 mt-0.5 text-red-600" />
                  <span>
                    Este contrato finaliza el <span className="font-semibold">{formatFecha(item.contrato.fecha_fin)}</span>,
                    antes del próximo aumento ({proximoLabel(item)}). No se le aplicará más aumentos.
                  </span>
                </div>
              </div>
            )}

            {iclPendiente && (
              <div className="px-5 pb-4">
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm">
                  <div className="flex items-center gap-2 text-amber-800 font-semibold mb-1">
                    <Clock size={14} className="text-amber-500" />
                    ICL pendiente de cálculo
                  </div>
                  {p.icl_error ? (
                    <p className="text-red-600 text-xs">
                      El Banco Central (BCRA) todavía no tiene disponible la información para calcular el aumento de este período. Volvé a intentarlo más tarde.
                    </p>
                  ) : (
                    <div className="text-amber-700 text-xs space-y-1">
                      {p.ultima_fecha_disponible_bcra && (
                        <p>Última fecha disponible BCRA: <span className="font-semibold">{formatFecha(p.ultima_fecha_disponible_bcra)}</span></p>
                      )}
                      {p.dias_faltantes != null && p.dias_faltantes > 0 && (
                        <p>Faltan aproximadamente <span className="font-semibold">{p.dias_faltantes} días</span> para completar el período requerido.</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {iclCalculado && p.fecha_vigencia && (
              <div className="px-5 pb-4">
                <div className="p-3 bg-sky-50 border border-sky-200 rounded-lg text-sm">
                  <div className="flex items-center gap-2 text-sky-800 font-semibold mb-1">
                    <CheckCircle2 size={14} className="text-sky-600" />
                    ICL calculado
                  </div>
                  <p className="text-sky-700 text-xs">
                    Entrará en vigencia: <span className="font-semibold">{formatFecha(p.fecha_vigencia)}</span>
                  </p>
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function HistorialAumentos({
  items,
  loading,
  inquilinos,
  onFiltrar,
}: {
  items: HistorialAumentoItem[]
  loading: boolean
  inquilinos: Inquilino[]
  onFiltrar: (idInq: string, anio: string, mes: string) => void
}) {
  const [filtroInq, setFiltroInq] = useState('')
  const [filtroAnio, setFiltroAnio] = useState('')
  const [filtroMes, setFiltroMes] = useState('')
  const [detalleAbierto, setDetalleAbierto] = useState<Set<number>>(new Set())

  function aplicar() {
    onFiltrar(filtroInq, filtroAnio, filtroMes)
  }

  function limpiar() {
    setFiltroInq('')
    setFiltroAnio('')
    setFiltroMes('')
    onFiltrar('', '', '')
  }

  function toggleDetalle(idHistorial: number) {
    setDetalleAbierto(prev => {
      const next = new Set(prev)
      if (next.has(idHistorial)) next.delete(idHistorial)
      else next.add(idHistorial)
      return next
    })
  }

  const aniosDisponibles = [2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030]

  return (
    <div>
      <div className="flex flex-wrap gap-3 mb-4 items-center">
        <select className="border rounded-lg px-3 py-2 text-sm" value={filtroInq} onChange={e => setFiltroInq(e.target.value)}>
          <option value="">Todos los inquilinos</option>
          {inquilinos.map(i => (
            <option key={i.id_inquilinos} value={i.id_inquilinos}>{i.nombre_apellido}</option>
          ))}
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm" value={filtroAnio} onChange={e => setFiltroAnio(e.target.value)}>
          <option value="">Todos los años</option>
          {aniosDisponibles.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm" value={filtroMes} onChange={e => setFiltroMes(e.target.value)}>
          <option value="">Todos los meses</option>
          {MESES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
        </select>
        <button
          onClick={aplicar}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium bg-slate-700 text-white rounded-lg hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-300 transition"
        >
          <Filter size={14} /> Filtrar
        </button>
        {(filtroInq || filtroAnio || filtroMes) && (
          <button onClick={limpiar} className="px-3 py-2 text-sm text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50">
            Limpiar
          </button>
        )}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500 text-lg">Cargando historial...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <History size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">Aun no hay aumentos registrados.</p>
          <p className="text-xs text-gray-300 mt-1">Los aumentos se registran automaticamente cuando corresponden y se consolidan al cobrar el mes.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="grid grid-cols-[1fr_2fr_1.4fr_1fr_1fr_1fr_1fr] gap-3 px-4 py-2.5 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wide">
            <span className="text-center">Mes / Ano</span>
            <span>Departamento / Inquilino</span>
            <span className="text-center">Tipo / Estado</span>
            <span>% Aplicado</span>
            <span>Alquiler anterior</span>
            <span>Alquiler aplicado</span>
            <span>Diferencia</span>
          </div>

          <div className="divide-y divide-gray-100">
            {items.map(item => {
              const h = item.historial
              const idHistorial = h.id_historial_aumentos
              const dep = item.departamento
              const mesLabel = `${MESES[h.mes - 1]} ${h.anio}`
              const abierto = idHistorial != null && detalleAbierto.has(idHistorial)

              return (
                <div key={idHistorial ?? `${h.id_contratos}-${h.anio}-${h.mes}`}>
                  <div
                    onClick={() => idHistorial != null && toggleDetalle(idHistorial)}
                    className="grid grid-cols-[1fr_2fr_1.4fr_1fr_1fr_1fr_1fr] gap-3 px-4 py-3 items-center hover:bg-gray-50 transition-colors cursor-pointer"
                    title="Clic para ver el detalle del aumento"
                  >
                    <div className="text-sm font-medium text-gray-700 text-center">{mesLabel}</div>

                    <div className="min-w-0">
                      <div className="font-semibold text-gray-800 text-sm truncate">{formatDepto(dep?.piso, dep?.codigo)}</div>
                      <div className="text-xs text-gray-500 truncate mt-0.5">
                        {item.inquilino?.nombre_apellido}
                        {dep?.direccion && <span className="text-gray-400"> · {dep.direccion}</span>}
                      </div>
                    </div>

                    <div className="flex items-center justify-center gap-1 flex-wrap">
                      <TipoBadge tipo={h.tipo_aumento} />
                      <EstadoAumentoBadge estado={h.estado} />
                    </div>

                    <div className="text-sm font-semibold text-gray-800 whitespace-nowrap">
                      {h.porcentaje_alquiler_aplicado.toFixed(2)}%
                    </div>

                    <div className="text-sm font-mono text-gray-600 whitespace-nowrap">
                      {formatMoneda(h.alquiler_anterior)}
                    </div>

                    <div className="text-sm font-mono font-semibold text-blue-700 whitespace-nowrap">
                      {formatMoneda(h.alquiler_aplicado)}
                    </div>

                    <div className="text-sm font-mono whitespace-nowrap">
                      <span className="text-green-600 font-semibold">+{formatMoneda(item.diferencia_aplicada)}</span>
                    </div>
                  </div>

                  {abierto && idHistorial != null && (
                    <div className="px-4 pb-4">
                      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm space-y-3">
                        {/* Alquiler: propuesto vs aplicado */}
                        <div>
                          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Alquiler</p>
                          <div className="grid grid-cols-3 gap-3">
                            <div>
                              <p className="text-xs text-gray-400 mb-0.5">Propuesto</p>
                              <p className="font-mono font-semibold text-gray-700">{formatMoneda(h.alquiler_propuesto)} ({h.porcentaje_alquiler_propuesto.toFixed(2)}%)</p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-400 mb-0.5">Aplicado</p>
                              <p className="font-mono font-semibold text-blue-700">{formatMoneda(h.alquiler_aplicado)} ({h.porcentaje_alquiler_aplicado.toFixed(2)}%)</p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-400 mb-0.5">Anterior</p>
                              <p className="font-mono font-semibold text-gray-700">{formatMoneda(h.alquiler_anterior)}</p>
                            </div>
                          </div>
                          {h.alquiler_aplicado !== h.alquiler_propuesto && (
                            <p className="text-xs text-amber-700 mt-1">El monto aplicado fue corregido manualmente respecto de la propuesta original.</p>
                          )}
                        </div>

                        {/* Expensa */}
                        {h.expensa_anterior != null && (
                          <div>
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Expensa</p>
                            <div className="grid grid-cols-3 gap-3">
                              <div>
                                <p className="text-xs text-gray-400 mb-0.5">Propuesta</p>
                                <p className="font-mono font-semibold text-gray-700">
                                  {formatMoneda(h.expensa_propuesta)} ({h.porcentaje_expensa_propuesto != null ? `${h.porcentaje_expensa_propuesto.toFixed(2)}%` : '-'})
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-400 mb-0.5">Aplicada</p>
                                <p className="font-mono font-semibold text-blue-700">
                                  {formatMoneda(h.expensa_aplicada)} ({h.porcentaje_expensa_aplicado != null ? `${h.porcentaje_expensa_aplicado.toFixed(2)}%` : '-'})
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-400 mb-0.5">Anterior</p>
                                <p className="font-mono font-semibold text-gray-700">{formatMoneda(h.expensa_anterior)}</p>
                              </div>
                            </div>
                            {item.diferencia_expensa_aplicada != null && (
                              <p className="text-xs text-green-600 font-semibold mt-1">+{formatMoneda(item.diferencia_expensa_aplicada)}</p>
                            )}
                          </div>
                        )}

                        {/* Datos ICL */}
                        {h.coeficiente_icl != null && (
                          <div>
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Datos ICL (BCRA)</p>
                            <div className="grid grid-cols-2 gap-3">
                              <div>
                                <p className="text-xs text-gray-400 mb-0.5">Coeficiente</p>
                                <p className="font-mono font-semibold text-gray-700">{h.coeficiente_icl.toFixed(6)}</p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-400 mb-0.5">ICL inicial / final</p>
                                <p className="font-mono font-semibold text-gray-700">{h.icl_inicial} → {h.icl_final}</p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-400 mb-0.5">Período consultado</p>
                                <p className="text-gray-700">{formatFecha(h.fecha_icl_inicial)} → {formatFecha(h.fecha_icl_final)}</p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Auditoría */}
                        <div className="text-xs text-gray-500 border-t border-gray-200 pt-2">
                          Estado: <span className="font-semibold">{h.estado}</span>
                          {h.estado === 'CONSOLIDADO' && h.fecha_consolidacion && (
                            <> · Consolidado al cobrar: <span className="font-semibold">{new Date(h.fecha_consolidacion).toLocaleString('es-AR', { hour12: false })}</span></>
                          )}
                          {' '}· Generado: {new Date(h.fecha_creacion).toLocaleString('es-AR', { hour12: false })}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

type Tab = 'proximos' | 'historial'

export default function Aumentos() {
  const [tab, setTab] = useState<Tab>('proximos')
  const [items, setItems] = useState<AumentoItem[]>([])
  const [historial, setHistorial] = useState<HistorialAumentoItem[]>([])
  const [inquilinos, setInquilinos] = useState<Inquilino[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingHistorial, setLoadingHistorial] = useState(false)

  async function cargarProximos() {
    setLoading(true)
    const res = await api.get('/aumentos/')
    setItems(res.data)
    setLoading(false)
  }

  async function cargarHistorial(idInq = '', anio = '', mes = '') {
    setLoadingHistorial(true)
    const params: Record<string, string> = {}
    if (idInq) params.id_inquilinos = idInq
    if (anio) params.anio = anio
    if (mes) params.mes = mes
    const res = await api.get('/aumentos/historial', { params })
    setHistorial(res.data)
    setLoadingHistorial(false)
  }

  async function cargarInquilinos() {
    const res = await api.get('/inquilinos/')
    setInquilinos(res.data)
  }

  useEffect(() => {
    cargarProximos()
    cargarInquilinos()
  }, [])

  function handleTab(t: Tab) {
    setTab(t)
    if (t === 'historial' && historial.length === 0 && !loadingHistorial) {
      cargarHistorial()
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-2xl font-bold text-gray-800">Aumentos</h2>
      </div>

      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-xl w-fit">
        <button
          onClick={() => handleTab('proximos')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            tab === 'proximos' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <TrendingUp size={15} />
          Proximos aumentos
        </button>
        <button
          onClick={() => handleTab('historial')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            tab === 'historial' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <History size={15} />
          Historial de aumentos
        </button>
      </div>

      {tab === 'proximos' && (
        loading
          ? <div className="text-center py-12 text-gray-500 text-lg">Cargando...</div>
          : <ProximosAumentos items={items} />
      )}

      {tab === 'historial' && (
        <HistorialAumentos
          items={historial}
          loading={loadingHistorial}
          inquilinos={inquilinos}
          onFiltrar={(idInq, anio, mes) => cargarHistorial(idInq, anio, mes)}
        />
      )}
    </div>
  )
}
