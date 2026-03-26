import { useEffect, useState } from 'react'
import api from '../lib/api'
import type { Inquilino, InquilinoCreate, PagoItem } from '../lib/types'
import { MESES, formatMoneda, formatFecha } from '../lib/types'
import { Plus, Pencil, Trash2, X } from 'lucide-react'

type Modal = 'crear' | 'editar' | 'contratos' | 'pagos' | null

export default function Inquilinos() {
  const [inquilinos, setInquilinos] = useState<Inquilino[]>([])
  const [modal, setModal] = useState<Modal>(null)
  const [selected, setSelected] = useState<Inquilino | null>(null)
  const [contratosInq, setContratosInq] = useState<unknown[]>([])
  const [pagos, setPagos] = useState<PagoItem[]>([])
  const [filtroAnio, setFiltroAnio] = useState('')
  const [filtroMes, setFiltroMes] = useState('')
  const [form, setForm] = useState<InquilinoCreate>({ nombre_apellido: '', telefono: '', es_actual: true })

  async function cargar() {
    const res = await api.get('/inquilinos/')
    setInquilinos(res.data)
  }

  useEffect(() => { cargar() }, [])

  function abrirCrear() {
    setForm({ nombre_apellido: '', telefono: '', es_actual: true })
    setModal('crear')
  }

  function abrirEditar(inq: Inquilino) {
    setSelected(inq)
    setForm({ nombre_apellido: inq.nombre_apellido, telefono: inq.telefono ?? '', es_actual: inq.es_actual })
    setModal('editar')
  }

  async function abrirContratos(inq: Inquilino) {
    setSelected(inq)
    const res = await api.get(`/inquilinos/${inq.id_inquilinos}/contratos`)
    setContratosInq(res.data)
    setModal('contratos')
  }

  async function abrirPagos(inq: Inquilino) {
    setSelected(inq)
    const params: Record<string, string> = {}
    if (filtroAnio) params.anio = filtroAnio
    if (filtroMes) params.mes = filtroMes
    const res = await api.get(`/inquilinos/${inq.id_inquilinos}/pagos`, { params })
    setPagos(res.data)
    setModal('pagos')
  }

  async function guardar() {
    if (modal === 'crear') {
      await api.post('/inquilinos/', form)
    } else if (modal === 'editar' && selected) {
      await api.put(`/inquilinos/${selected.id_inquilinos}`, form)
    }
    cargar()
    setModal(null)
  }

  async function eliminar(inq: Inquilino) {
    if (!confirm(`¿Eliminar ${inq.nombre_apellido}?`)) return
    await api.delete(`/inquilinos/${inq.id_inquilinos}`)
    cargar()
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Inquilinos</h2>
        <button
          onClick={abrirCrear}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm"
        >
          <Plus size={16} /> Nuevo inquilino
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Nombre</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Teléfono</th>
              <th className="text-center px-4 py-3 font-semibold text-gray-600">Estado</th>
              <th className="text-center px-4 py-3 font-semibold text-gray-600">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {inquilinos.map(inq => (
              <tr key={inq.id_inquilinos} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-800">{inq.nombre_apellido}</td>
                <td className="px-4 py-3 text-gray-600">{inq.telefono || '-'}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${inq.es_actual ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {inq.es_actual ? 'Actual' : 'Anterior'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1 justify-center">
                    <button onClick={() => abrirEditar(inq)} className="p-1.5 hover:bg-gray-100 rounded" title="Editar">
                      <Pencil size={14} className="text-gray-500" />
                    </button>
                    <button
                      onClick={() => abrirContratos(inq)}
                      className="text-xs px-2 py-1 bg-white border border-gray-200 text-gray-700 rounded hover:bg-gray-50"
                    >
                      Contratos
                    </button>
                    <button
                      onClick={() => abrirPagos(inq)}
                      className="text-xs px-2 py-1 bg-white border border-gray-200 text-gray-700 rounded hover:bg-gray-50"
                    >
                      Pagos
                    </button>
                    <button onClick={() => eliminar(inq)} className="p-1.5 hover:bg-gray-100 rounded" title="Eliminar">
                      <Trash2 size={14} className="text-red-400" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {inquilinos.length === 0 && (
          <div className="py-8 text-center text-gray-400">No hay inquilinos. Creá uno.</div>
        )}
      </div>

      {/* Modal Crear/Editar */}
      {(modal === 'crear' || modal === 'editar') && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg">{modal === 'crear' ? 'Nuevo inquilino' : 'Editar inquilino'}</h3>
              <button onClick={() => setModal(null)}><X size={18} className="text-gray-500" /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre y apellido *</label>
                <input
                  type="text"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.nombre_apellido}
                  onChange={e => setForm(f => ({ ...f, nombre_apellido: e.target.value }))}
                  placeholder="Juan García"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
                <input
                  type="text"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.telefono ?? ''}
                  onChange={e => setForm(f => ({ ...f, telefono: e.target.value }))}
                  placeholder="3794226712"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="es_actual"
                  checked={form.es_actual}
                  onChange={e => setForm(f => ({ ...f, es_actual: e.target.checked }))}
                  className="rounded"
                />
                <label htmlFor="es_actual" className="text-sm font-medium text-gray-700">Inquilino actual</label>
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-5">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100">Cancelar</button>
              <button onClick={guardar} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">Guardar</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Contratos */}
      {modal === 'contratos' && selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg">Contratos — {selected.nombre_apellido}</h3>
              <button onClick={() => setModal(null)}><X size={18} className="text-gray-500" /></button>
            </div>
            {contratosInq.length === 0 ? (
              <p className="text-gray-400 text-sm">Sin contratos.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-left">
                    <th className="px-3 py-2">Depto</th>
                    <th className="px-3 py-2">Desde</th>
                    <th className="px-3 py-2">Hasta</th>
                    <th className="px-3 py-2">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {(contratosInq as Array<{ contrato: { id_contratos: number; fecha_inicio: string; fecha_fin: string; estado: string }; departamento?: { piso: string; codigo: string } }>).map(c => (
                    <tr key={c.contrato.id_contratos}>
                      <td className="px-3 py-2">{c.departamento?.piso} {c.departamento?.codigo}</td>
                      <td className="px-3 py-2">{formatFecha(c.contrato.fecha_inicio)}</td>
                      <td className="px-3 py-2">{formatFecha(c.contrato.fecha_fin)}</td>
                      <td className="px-3 py-2">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${c.contrato.estado === 'activo' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                          {c.contrato.estado}
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
              <h3 className="font-bold text-lg">Pagos — {selected.nombre_apellido}</h3>
              <button onClick={() => setModal(null)}><X size={18} className="text-gray-500" /></button>
            </div>
            <div className="flex gap-3 mb-4">
              <select className="border rounded-lg px-3 py-2 text-sm" value={filtroAnio} onChange={e => setFiltroAnio(e.target.value)}>
                <option value="">Todos los años</option>
                {[2024, 2025, 2026, 2027, 2028, 2029, 2030].map(y => <option key={y} value={y}>{y}</option>)}
              </select>
              <select className="border rounded-lg px-3 py-2 text-sm" value={filtroMes} onChange={e => setFiltroMes(e.target.value)}>
                <option value="">Todos los meses</option>
                {MESES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
              </select>
              <button onClick={() => abrirPagos(selected)} className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">Filtrar</button>
            </div>
            {pagos.length === 0 ? (
              <p className="text-gray-400 text-sm">Sin registros.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-left">
                    <th className="px-3 py-2">Mes</th>
                    <th className="px-3 py-2">Departamento</th>
                    <th className="px-3 py-2 text-right">Total</th>
                    <th className="px-3 py-2 text-center">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {pagos.map(p => (
                    <tr key={p.registro.id_registros_mensuales}>
                      <td className="px-3 py-2">{MESES[p.registro.mes - 1]} {p.registro.anio}</td>
                      <td className="px-3 py-2">{p.departamento?.piso} {p.departamento?.codigo}</td>
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
