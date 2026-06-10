import { useEffect, useState } from 'react'
import api from '../lib/api'
import type { AumentoItem, AumentoHistorialItem } from '../lib/types'
import { MESES, formatMoneda, formatFecha } from '../lib/types'
import { TrendingUp, AlertTriangle, XCircle, Clock, CheckCircle2, ChevronRight, History } from 'lucide-react'

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
  return (
    <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
      MANUAL
    </span>
  )
}

// ─────────────────────────────────────────────────────────
// Vista: Próximos aumentos
// ─────────────────────────────────────────────────────────
function ProximosAumentos({ items }: { items: AumentoItem[] }) {
  if (items.length === 0) {
    return <div className="text-center py-12 text-gray-400 text-lg">No hay contratos activos.</div>
  }
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="grid grid-cols-[2fr_1.5fr_1fr_1fr_1fr_1.5fr_1.5fr_1fr] gap-3 px-4 py-2.5 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wide">
        <span>Departamento / Inquilino</span>
        <span>Próximo aumento</span>
        <span>Tipo</span>
        <span>Periodicidad</span>
        <span>Alquiler actual</span>
        <span>Alquiler nuevo</span>
        <span>Diferencia</span>
        <span>Estado</span>
      </div>

      <div className="divide-y divide-gray-100">
        {items.map(item => {
          const p = item.proximo_aumento
          const esICL = (p.tipo_aumento ?? item.contrato.tipo_aumento) === 'ICL'
          const iclPendiente = esICL && p.icl_pendiente
          const diferencia = p.alquiler_nuevo != null ? p.alquiler_nuevo - p.alquiler_actual : null
          const porcentaje = p.porcentaje

          return (
            <div key={item.contrato.id_contratos}>
              <div className="grid grid-cols-[2fr_1.5fr_1fr_1fr_1fr_1.5fr_1.5fr_1fr] gap-3 px-4 py-3 items-center hover:bg-gray-50 transition-colors">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-gray-800 text-sm">
                      {formatDepto(item.departamento?.piso, item.departamento?.codigo)}
                    </span>
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
                  </div>
                  <div className="text-xs text-gray-500 truncate mt-0.5">
                    {item.inquilino?.nombre_apellido}
                    {item.departamento?.direccion && (
                      <span className="text-gray-400"> · {item.departamento.direccion}</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1.5 text-sm">
                  <TrendingUp size={14} className="text-blue-500 shrink-0" />
                  <span className="font-medium text-gray-700">{proximoLabel(item)}</span>
                </div>

                <div><TipoBadge tipo={p.tipo_aumento ?? item.contrato.tipo_aumento} /></div>

                <div className="text-sm text-gray-600">{item.contrato.periodicidad_aumento_meses} meses</div>

                <div className="text-sm font-mono font-medium text-gray-800">
                  {formatMoneda(p.alquiler_actual)}
                </div>

                <div className="text-sm font-mono font-semibold">
                  {iclPendiente ? (
                    <span className="text-amber-600 flex items-center gap-1"><Clock size={13} /> Pendiente</span>
                  ) : p.alquiler_nuevo != null ? (
                    <span className="text-blue-700">{formatMoneda(p.alquiler_nuevo)}</span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </div>

                <div className="text-sm font-mono">
                  {iclPendiente ? (
                    <span className="text-gray-400">-</span>
                  ) : diferencia != null ? (
                    <div>
                      <span className="text-green-600 font-semibold">+{formatMoneda(diferencia)}</span>
                      {porcentaje != null && <div className="text-xs text-gray-400">{porcentaje.toFixed(2)}%</div>}
                    </div>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </div>

                <div className="text-xs">
                  {p.requires_fecha_ultimo ? (
                    <span className="flex items-center gap-1 text-amber-600"><AlertTriangle size={12} /> Falta fecha</span>
                  ) : !p.alquiler_nuevo && !iclPendiente ? (
                    <span className="text-gray-400">Sin aumento</span>
                  ) : iclPendiente ? (
                    <span className="flex items-center gap-1 text-amber-600"><Clock size={12} /> ICL pendiente</span>
                  ) : (
                    <span className="flex items-center gap-1 text-green-600"><CheckCircle2 size={12} /> Calculado</span>
                  )}
                </div>
              </div>

              {p.requires_fecha_ultimo && (
                <div className="mx-4 mb-3 flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                  <AlertTriangle size={15} className="shrink-0 mt-0.5 text-amber-500" />
                  <span>
                    Este contrato ya lleva un tiempo en curso pero no tiene registrado el último aumento.
                    Editá el contrato e indicá la fecha del último aumento para que el sistema calcule correctamente el próximo.
                  </span>
                </div>
              )}

              {iclPendiente && (
                <div className="mx-4 mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm">
                  <div className="flex items-center gap-2 text-amber-800 font-semibold mb-1">
                    <Clock size={14} className="text-amber-500" />
                    ICL pendiente de cálculo
                  </div>
                  {p.icl_error ? (
                    <p className="text-red-600 text-xs">{p.icl_error}</p>
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
              )}

              {!iclPendiente && item.contrato.cobra_expensa && p.expensa_actual != null && p.expensa_nueva != null && (
                <div className="mx-4 mb-3 flex gap-4 text-xs text-gray-600 bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                  <span>Expensa actual: <strong>{formatMoneda(p.expensa_actual)}</strong></span>
                  <ChevronRight size={14} className="text-gray-400 self-center" />
                  <span>Expensa nueva: <strong className="text-blue-700">{formatMoneda(p.expensa_nueva)}</strong></span>
                  <span className="text-green-600">+{formatMoneda(p.expensa_nueva - p.expensa_actual)}</span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────
// Vista: Historial de aumentos
// ─────────────────────────────────────────────────────────
function HistorialAumentos({ items, loading }: { items: AumentoHistorialItem[], loading: boolean }) {
  if (loading) return <div className="text-center py-12 text-gray-500 text-lg">Cargando historial...</div>
  if (items.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <History size={40} className="mx-auto mb-3 opacity-30" />
        <p className="text-sm">Aún no hay aumentos aplicados registrados.</p>
        <p className="text-xs text-gray-300 mt-1">Los aumentos se registrarán automáticamente cuando se procesen en el dashboard.</p>
      </div>
    )
  }
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="grid grid-cols-[1fr_2fr_1fr_1fr_1fr_1fr_1fr] gap-3 px-4 py-2.5 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wide">
        <span>Mes / Año</span>
        <span>Departamento / Inquilino</span>
        <span>Tipo</span>
        <span>% Aplicado</span>
        <span>Alquiler anterior</span>
        <span>Alquiler nuevo</span>
        <span>Diferencia</span>
      </div>

      <div className="divide-y divide-gray-100">
        {items.map(item => {
          const diferencia = item.alquiler_anterior != null
            ? item.alquiler_nuevo - item.alquiler_anterior
            : null
          const dep = item.departamento
          const mesLabel = `${MESES[item.registro.mes - 1]} ${item.registro.anio}`

          return (
            <div
              key={item.registro.id_registros_mensuales}
              className="grid grid-cols-[1fr_2fr_1fr_1fr_1fr_1fr_1fr] gap-3 px-4 py-3 items-center hover:bg-gray-50 transition-colors"
            >
              {/* Mes/Año */}
              <div className="text-sm font-medium text-gray-700">{mesLabel}</div>

              {/* Depto / Inquilino */}
              <div className="min-w-0">
                <div className="font-semibold text-gray-800 text-sm truncate">
                  {formatDepto(dep?.piso, dep?.codigo)}
                </div>
                <div className="text-xs text-gray-500 truncate mt-0.5">
                  {item.inquilino?.nombre_apellido}
                  {dep?.direccion && <span className="text-gray-400"> · {dep.direccion}</span>}
                </div>
              </div>

              {/* Tipo */}
              <div><TipoBadge tipo={item.contrato.tipo_aumento} /></div>

              {/* Porcentaje */}
              <div className="text-sm font-semibold text-gray-800">
                {item.registro.porcentaje_aumento_usado != null
                  ? `${item.registro.porcentaje_aumento_usado.toFixed(2)}%`
                  : '-'}
              </div>

              {/* Alquiler anterior */}
              <div className="text-sm font-mono text-gray-600">
                {item.alquiler_anterior != null ? formatMoneda(item.alquiler_anterior) : <span className="text-gray-300 italic">N/D</span>}
              </div>

              {/* Alquiler nuevo */}
              <div className="text-sm font-mono font-semibold text-blue-700">
                {formatMoneda(item.alquiler_nuevo)}
              </div>

              {/* Diferencia */}
              <div className="text-sm font-mono">
                {diferencia != null ? (
                  <span className="text-green-600 font-semibold">+{formatMoneda(diferencia)}</span>
                ) : (
                  <span className="text-gray-300">-</span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────
// Componente principal
// ─────────────────────────────────────────────────────────
type Tab = 'proximos' | 'historial'

export default function Aumentos() {
  const [tab, setTab] = useState<Tab>('proximos')
  const [items, setItems] = useState<AumentoItem[]>([])
  const [historial, setHistorial] = useState<AumentoHistorialItem[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingHistorial, setLoadingHistorial] = useState(false)

  async function cargarProximos() {
    setLoading(true)
    const res = await api.get('/aumentos/')
    setItems(res.data)
    setLoading(false)
  }

  async function cargarHistorial() {
    setLoadingHistorial(true)
    const res = await api.get('/aumentos/historial')
    setHistorial(res.data)
    setLoadingHistorial(false)
  }

  useEffect(() => { cargarProximos() }, [])

  function handleTab(t: Tab) {
    setTab(t)
    if (t === 'historial' && historial.length === 0 && !loadingHistorial) {
      cargarHistorial()
    }
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-2xl font-bold text-gray-800">Aumentos</h2>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-xl w-fit">
        <button
          onClick={() => handleTab('proximos')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            tab === 'proximos'
              ? 'bg-white text-gray-800 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <TrendingUp size={15} />
          Próximos aumentos
        </button>
        <button
          onClick={() => handleTab('historial')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            tab === 'historial'
              ? 'bg-white text-gray-800 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <History size={15} />
          Historial de aumentos
        </button>
      </div>

      {/* Contenido */}
      {tab === 'proximos' && (
        loading
          ? <div className="text-center py-12 text-gray-500 text-lg">Cargando...</div>
          : <ProximosAumentos items={items} />
      )}

      {tab === 'historial' && (
        <HistorialAumentos items={historial} loading={loadingHistorial} />
      )}
    </div>
  )
}

