import { useEffect, useState } from 'react'
import api from '../lib/api'
import type { Inquilino, InquilinoCreate, PagoItem } from '../lib/types'
import { MESES, formatMoneda, formatFecha } from '../lib/types'
import { Plus, Pencil, Trash2, X, Filter } from 'lucide-react'
import { Label, clasesCampo, ErrorCamposModal, ModalShell, useToast } from '../lib/ui'

type Modal = 'crear' | 'editar' | 'contratos' | 'pagos' | null

export default function Inquilinos() {
  const toast = useToast()
  const [inquilinos, setInquilinos] = useState<Inquilino[]>([])
  const [modal, setModal] = useState<Modal>(null)
  const [selected, setSelected] = useState<Inquilino | null>(null)
  const [contratosInq, setContratosInq] = useState<unknown[]>([])
  const [pagos, setPagos] = useState<PagoItem[]>([])
  const [filtroAnio, setFiltroAnio] = useState('')
  const [filtroMes, setFiltroMes] = useState('')
  const [form, setForm] = useState<InquilinoCreate>({ nombre_apellido: '', telefono: '', es_actual: true })
  const [busqueda, setBusqueda] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [errores, setErrores] = useState<Record<string, string>>({})
  const [popupErrores, setPopupErrores] = useState<string[]>([])
  const [saving, setSaving] = useState(false)

  function normalizar(texto: string) {
    return texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  }

  const inquilinosFiltrados = busqueda.trim()
    ? inquilinos.filter(i => normalizar(i.nombre_apellido).includes(normalizar(busqueda.trim())))
    : inquilinos

  async function cargar() {
    const res = await api.get('/inquilinos/')
    setInquilinos(res.data)
  }

  useEffect(() => { cargar() }, [])

  function abrirCrear() {
    setForm({ nombre_apellido: '', telefono: '', es_actual: true })
    setErrorMsg('')
    setErrores({})
    setPopupErrores([])
    setModal('crear')
  }

  function abrirEditar(inq: Inquilino) {
    setSelected(inq)
    setForm({ nombre_apellido: inq.nombre_apellido, telefono: inq.telefono ?? '', es_actual: inq.es_actual })
    setErrorMsg('')
    setErrores({})
    setPopupErrores([])
    setModal('editar')
  }

  async function abrirContratos(inq: Inquilino) {
    setSelected(inq)
    const res = await api.get(`/inquilinos/${inq.id_inquilinos}/contratos`)
    const ordenado = [...res.data].sort((a: { contrato: { fecha_inicio: string } }, b: { contrato: { fecha_inicio: string } }) =>
      new Date(b.contrato.fecha_inicio).getTime() - new Date(a.contrato.fecha_inicio).getTime()
    )
    setContratosInq(ordenado)
    setModal('contratos')
  }

  async function abrirPagos(inq: Inquilino) {
    setSelected(inq)
    const params: Record<string, string> = {}
    if (filtroAnio) params.anio = filtroAnio
    if (filtroMes) params.mes = filtroMes
    const res = await api.get(`/inquilinos/${inq.id_inquilinos}/pagos`, { params })
    const ordenado = [...res.data].sort((a: PagoItem, b: PagoItem) => {
      if (b.registro.anio !== a.registro.anio) return b.registro.anio - a.registro.anio
      return b.registro.mes - a.registro.mes
    })
    setPagos(ordenado)
    setModal('pagos')
  }

  async function guardar() {
    if (saving) return
    setErrorMsg('')
    const e: Record<string, string> = {}
    if (!form.nombre_apellido.trim()) e.nombre_apellido = 'Nombre y apellido es obligatorio.'
    if (Object.keys(e).length > 0) {
      setErrores(e)
      setPopupErrores(Object.values(e))
      return
    }
    setSaving(true)
    try {
      if (modal === 'crear') {
        await api.post('/inquilinos/', form)
        toast('Se guardó el inquilino correctamente')
      } else if (modal === 'editar' && selected) {
        await api.put(`/inquilinos/${selected.id_inquilinos}`, form)
        toast('Se actualizaron los cambios correctamente')
      }
      cargar()
      setModal(null)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al guardar'
      setErrorMsg(msg)
    } finally {
      setSaving(false)
    }
  }

  function limpiarError(campo: string) {
    setErrores(prev => {
      if (!prev[campo]) return prev
      const n = { ...prev }
      delete n[campo]
      return n
    })
  }

  async function eliminar(inq: Inquilino) {
    if (!confirm(`¿Eliminar ${inq.nombre_apellido}?`)) return
    await api.delete(`/inquilinos/${inq.id_inquilinos}`)
    toast('Se eliminó el inquilino correctamente')
    cargar()
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Inquilinos</h2>
        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Buscar por nombre..."
            value={busqueda}
            onChange={e => setBusqueda(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-56 focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
          <button
            onClick={abrirCrear}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm"
          >
            <Plus size={16} /> Nuevo inquilino
          </button>
        </div>
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
            {inquilinosFiltrados.map(inq => (
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
        {inquilinosFiltrados.length === 0 && (
          <div className="py-8 text-center text-gray-400">
            {busqueda.trim() ? 'No se encontraron inquilinos con ese nombre.' : 'No hay inquilinos. Creá uno.'}
          </div>
        )}
      </div>

      {/* Modal Crear/Editar */}
      {(modal === 'crear' || modal === 'editar') && (
        <ModalShell max="max-w-lg">
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg">{modal === 'crear' ? 'Nuevo inquilino' : 'Editar inquilino'}</h3>
              <button onClick={() => setModal(null)}><X size={18} className="text-gray-500" /></button>
            </div>
            {errorMsg && <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-600">{errorMsg}</div>}
            <div className="space-y-3">
              <div>
                <Label required>Nombre y apellido</Label>
                <input
                  type="text"
                  className={clasesCampo(errores, 'nombre_apellido')}
                  value={form.nombre_apellido}
                  onChange={e => { limpiarError('nombre_apellido'); setForm(f => ({ ...f, nombre_apellido: e.target.value })) }}
                  placeholder="Juan García"
                />
              </div>
              <div>
                <Label required={false}>Teléfono</Label>
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
              <button onClick={guardar} disabled={saving} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60">
                {saving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </ModalShell>
      )}

      <ErrorCamposModal errores={popupErrores} onCerrar={() => setPopupErrores([])} />

      {/* Modal Contratos */}
      {modal === 'contratos' && selected && (
        <ModalShell max="max-w-xl">
          <div className="p-6">
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
        </ModalShell>
      )}

      {/* Modal Pagos */}
      {modal === 'pagos' && selected && (
        <ModalShell max="max-w-3xl">
          <div className="p-6">
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
              <button
                onClick={() => abrirPagos(selected)}
                className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium bg-slate-700 text-white rounded-lg hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-300 transition"
              >
                <Filter size={14} /> Filtrar
              </button>
            </div>
            {pagos.length === 0 ? (
              <p className="text-gray-400 text-sm">Sin registros.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-left">
                    <th className="px-3 py-2 text-center">Mes</th>
                    <th className="px-3 py-2">Departamento</th>
                    <th className="px-3 py-2 text-center">Total</th>
                    <th className="px-3 py-2 text-center">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {pagos.map(p => (
                    <tr key={p.registro.id_registros_mensuales}>
                      <td className="px-3 py-2 text-center">{MESES[p.registro.mes - 1]} {p.registro.anio}</td>
                      <td className="px-3 py-2">{p.departamento?.piso} {p.departamento?.codigo}</td>
                      <td className="px-3 py-2 text-center font-mono whitespace-nowrap">{formatMoneda(p.registro.total)}</td>
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
        </ModalShell>
      )}
    </div>
  )
}
