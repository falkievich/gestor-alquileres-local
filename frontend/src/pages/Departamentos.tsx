import { useEffect, useState } from 'react'
import api from '../lib/api'
import type { Departamento, DepartamentoCreate, HistorialItem, PagoItem } from '../lib/types'
import { PISOS, MESES, formatMoneda, formatFecha } from '../lib/types'
import { Plus, Pencil, Trash2, History, X } from 'lucide-react'

function formatDepto(piso: string | undefined, codigo: string | undefined) {
  if (!piso || !codigo) return `${piso ?? ''} ${codigo ?? ''}`.trim()
  const pisoAbrev = piso === 'Planta baja' ? 'PB' : piso.replace('Piso ', 'P')
  return `${pisoAbrev}-${codigo}`
}

type Modal = 'crear' | 'editar' | 'historial' | 'pagos' | null

export default function Departamentos() {
  const [departamentos, setDepartamentos] = useState<Departamento[]>([])
  const [modal, setModal] = useState<Modal>(null)
  const [selected, setSelected] = useState<Departamento | null>(null)
  const [historial, setHistorial] = useState<HistorialItem[]>([])
  const [pagos, setPagos] = useState<PagoItem[]>([])
  const [filtroAnio, setFiltroAnio] = useState('')
  const [filtroMes, setFiltroMes] = useState('')
  const [form, setForm] = useState<DepartamentoCreate>({ piso: PISOS[0], codigo: '', direccion: '' })
  const [errorMsg, setErrorMsg] = useState('')

  async function cargar() {
    const res = await api.get('/departamentos/')
    setDepartamentos(res.data)
  }

  useEffect(() => { cargar() }, [])

  function abrirCrear() {
    setForm({ piso: PISOS[0], codigo: '', direccion: '' })
    setErrorMsg('')
    setModal('crear')
  }

  function abrirEditar(dep: Departamento) {
    setSelected(dep)
    setForm({ piso: dep.piso, codigo: dep.codigo, direccion: dep.direccion ?? '' })
    setErrorMsg('')
    setModal('editar')
  }

  async function abrirHistorial(dep: Departamento) {
    setSelected(dep)
    const res = await api.get(`/departamentos/${dep.id_departamentos}/historial`)
    const ordenado = [...res.data].sort((a: HistorialItem, b: HistorialItem) =>
      new Date(b.contrato.fecha_inicio).getTime() - new Date(a.contrato.fecha_inicio).getTime()
    )
    setHistorial(ordenado)
    setModal('historial')
  }

  async function abrirPagos(dep: Departamento) {
    setSelected(dep)
    const params: Record<string, string> = {}
    if (filtroAnio) params.anio = filtroAnio
    if (filtroMes) params.mes = filtroMes
    const res = await api.get(`/departamentos/${dep.id_departamentos}/pagos`, { params })
    const ordenado = [...res.data].sort((a: PagoItem, b: PagoItem) => {
      if (b.registro.anio !== a.registro.anio) return b.registro.anio - a.registro.anio
      return b.registro.mes - a.registro.mes
    })
    setPagos(ordenado)
    setModal('pagos')
  }

  async function guardar() {
    setErrorMsg('')
    try {
      if (modal === 'crear') {
        await api.post('/departamentos/', form)
      } else if (modal === 'editar' && selected) {
        await api.put(`/departamentos/${selected.id_departamentos}`, form)
      }
      cargar()
      setModal(null)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al guardar'
      setErrorMsg(msg)
    }
  }

  async function eliminar(dep: Departamento) {
    if (!confirm(`¿Eliminar ${dep.piso} ${dep.codigo}?`)) return
    await api.delete(`/departamentos/${dep.id_departamentos}`)
    cargar()
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Departamentos</h2>
        <button
          onClick={abrirCrear}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm"
        >
          <Plus size={16} /> Nuevo departamento
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {departamentos.map(dep => (
          <div key={dep.id_departamentos} className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold text-gray-800 truncate">{formatDepto(dep.piso, dep.codigo)}</span>
                </div>
                {dep.direccion && <p className="text-xs text-gray-500 mt-0.5">{dep.direccion}</p>}
                <span className={`inline-block mt-2 text-xs font-semibold px-2 py-0.5 rounded-full ${dep.esta_ocupado ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-700'}`}>
                  {dep.esta_ocupado ? 'Ocupado' : 'Libre'}
                </span>
              </div>
              <div className="flex gap-1 shrink-0">
                <button onClick={() => abrirEditar(dep)} className="p-1.5 hover:bg-gray-100 rounded">
                  <Pencil size={15} className="text-gray-500" />
                </button>
                <button onClick={() => eliminar(dep)} className="p-1.5 hover:bg-gray-100 rounded">
                  <Trash2 size={15} className="text-red-400" />
                </button>
              </div>
            </div>
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => abrirHistorial(dep)}
                className="flex-1 text-xs py-1.5 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center justify-center gap-1"
              >
                <History size={13} /> Historial
              </button>
              <button
                onClick={() => abrirPagos(dep)}
                className="flex-1 text-xs py-1.5 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center justify-center gap-1"
              >
                Pagos
              </button>
            </div>
          </div>
        ))}
        {departamentos.length === 0 && (
          <div className="col-span-3 text-center py-12 text-gray-400">No hay departamentos. Creá uno.</div>
        )}
      </div>

      {/* Modal Crear/Editar */}
      {(modal === 'crear' || modal === 'editar') && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg">{modal === 'crear' ? 'Nuevo departamento' : 'Editar departamento'}</h3>
              <button onClick={() => setModal(null)}><X size={18} className="text-gray-500" /></button>
            </div>
            {errorMsg && <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-600">{errorMsg}</div>}
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Piso</label>
                <select
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.piso}
                  onChange={e => setForm(f => ({ ...f, piso: e.target.value }))}
                >
                  {PISOS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Código *</label>
                <input
                  type="text"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.codigo}
                  onChange={e => setForm(f => ({ ...f, codigo: e.target.value }))}
                  placeholder="Ej: 1A"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Dirección (opcional)</label>
                <input
                  type="text"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.direccion ?? ''}
                  onChange={e => setForm(f => ({ ...f, direccion: e.target.value }))}
                  placeholder="Ej: Av. Corrientes 1234"
                />
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-5">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100">Cancelar</button>
              <button onClick={guardar} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">Guardar</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Historial */}
      {modal === 'historial' && selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg">Historial — {formatDepto(selected.piso, selected.codigo)}</h3>
              <button onClick={() => setModal(null)}><X size={18} className="text-gray-500" /></button>
            </div>
            {historial.length === 0 ? (
              <p className="text-gray-400 text-sm">Sin historial.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-left">
                    <th className="px-3 py-2">Inquilino</th>
                    <th className="px-3 py-2">Desde</th>
                    <th className="px-3 py-2">Hasta</th>
                    <th className="px-3 py-2">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {historial.map(h => (
                    <tr key={h.contrato.id_contratos}>
                      <td className="px-3 py-2">{h.inquilino?.nombre_apellido}</td>
                      <td className="px-3 py-2">{formatFecha(h.contrato.fecha_inicio)}</td>
                      <td className="px-3 py-2">{formatFecha(h.contrato.fecha_fin)}</td>
                      <td className="px-3 py-2">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${h.contrato.estado === 'activo' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                          {h.contrato.estado}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Modal Pagos */}
      {modal === 'pagos' && selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg">Pagos — {formatDepto(selected.piso, selected.codigo)}</h3>
              <button onClick={() => setModal(null)}><X size={18} className="text-gray-500" /></button>
            </div>
            <div className="flex gap-3 mb-4">
              <select
                className="border rounded-lg px-3 py-2 text-sm"
                value={filtroAnio}
                onChange={e => setFiltroAnio(e.target.value)}
              >
                <option value="">Todos los años</option>
                {[2024, 2025, 2026, 2027, 2028, 2029, 2030].map(y => <option key={y} value={y}>{y}</option>)}
              </select>
              <select
                className="border rounded-lg px-3 py-2 text-sm"
                value={filtroMes}
                onChange={e => setFiltroMes(e.target.value)}
              >
                <option value="">Todos los meses</option>
                {MESES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
              </select>
              <button
                onClick={() => abrirPagos(selected)}
                className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Filtrar
              </button>
            </div>
            {pagos.length === 0 ? (
              <p className="text-gray-400 text-sm">Sin registros.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-left">
                    <th className="px-3 py-2">Mes</th>
                    <th className="px-3 py-2">Inquilino</th>
                    <th className="px-3 py-2 text-right">Total</th>
                    <th className="px-3 py-2 text-center">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {pagos.map(p => (
                    <tr key={p.registro.id_registros_mensuales}>
                      <td className="px-3 py-2">{MESES[p.registro.mes - 1]} {p.registro.anio}</td>
                      <td className="px-3 py-2">{p.inquilino?.nombre_apellido}</td>
                      <td className="px-3 py-2 text-right font-mono">{formatMoneda(p.registro.total)}</td>
                      <td className="px-3 py-2 text-center">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${p.registro.pagado ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                          {p.registro.pagado ? 'Pagado' : 'No pagado'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
