import { useEffect, useState } from 'react'
import api from '../lib/api'
import type { Contrato, ContratoCreate, Departamento, Inquilino } from '../lib/types'
import { formatMoneda, formatFecha } from '../lib/types'
import { Plus, Pencil, X, Download, Lock } from 'lucide-react'

function formatDepto(piso: string | undefined, codigo: string | undefined) {
  if (!piso || !codigo) return `${piso ?? ''} ${codigo ?? ''}`.trim()
  return `${piso} — ${codigo}`
}

type Modal = 'crear' | 'editar' | null

function estadoBadge(contrato: Contrato) {
  const hoy = new Date()
  const fin = new Date(contrato.fecha_fin)
  const mesesHastaFin = (fin.getFullYear() - hoy.getFullYear()) * 12 + (fin.getMonth() - hoy.getMonth())
  if (contrato.estado === 'activo' && fin < hoy) {
    return <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-red-100 text-red-700">Vencido</span>
  }
  if (contrato.estado === 'activo' && mesesHastaFin <= 3) {
    return <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-yellow-100 text-yellow-700">Por vencer</span>
  }
  if (contrato.estado === 'activo') {
    return <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-green-100 text-green-700">Activo</span>
  }
  return <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-gray-100 text-gray-500">Finalizado</span>
}

const emptyForm: ContratoCreate = {
  id_departamentos: 0,
  id_inquilinos: 0,
  fecha_inicio: '',
  fecha_fin: '',
  alquiler_base_actual: 0,
  expensa_base_actual: undefined,
  porcentaje_aumento: 0,
  periodicidad_aumento_meses: undefined,
  cobra_expensa: false,
  cobra_agua: false,
  cobra_luz: false,
  tipo_aumento: undefined,
  fecha_ultimo_aumento: undefined,
}

export default function Contratos() {
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [departamentos, setDepartamentos] = useState<Departamento[]>([])
  const [inquilinos, setInquilinos] = useState<Inquilino[]>([])
  const [modal, setModal] = useState<Modal>(null)
  const [selected, setSelected] = useState<Contrato | null>(null)
  const [form, setForm] = useState<ContratoCreate>(emptyForm)
  const [errorMsg, setErrorMsg] = useState('')
  const [archivoFile, setArchivoFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [fechaInicioBlocked, setFechaInicioBlocked] = useState(false)
  const [contratoEnCurso, setContratoEnCurso] = useState(false)
  // Filtros
  const [filtroInq, setFiltroInq] = useState('')
  const [filtroDep, setFiltroDep] = useState('')
  const [filtroEstado, setFiltroEstado] = useState('')

  async function cargar() {
    const [cRes, dRes, iRes] = await Promise.all([
      api.get('/contratos/', { params: filtrosActivos() }),
      api.get('/departamentos/'),
      api.get('/inquilinos/'),
    ])
    setContratos(cRes.data)
    setDepartamentos(dRes.data)
    setInquilinos(iRes.data)
  }

  function filtrosActivos() {
    const p: Record<string, string> = {}
    if (filtroInq) p.id_inquilinos = filtroInq
    if (filtroDep) p.id_departamentos = filtroDep
    if (filtroEstado) p.estado = filtroEstado
    return p
  }

  useEffect(() => { cargar() }, [])

  function abrirCrear() {
    setForm(emptyForm)
    setArchivoFile(null)
    setErrorMsg('')
    setFechaInicioBlocked(false)
    setContratoEnCurso(false)
    setModal('crear')
  }

  async function abrirEditar(c: Contrato) {
    setSelected(c)
    setForm({
      id_departamentos: c.id_departamentos,
      id_inquilinos: c.id_inquilinos,
      fecha_inicio: c.fecha_inicio,
      fecha_fin: c.fecha_fin,
      alquiler_base_actual: c.alquiler_base_actual,
      expensa_base_actual: c.expensa_base_actual,
      porcentaje_aumento: c.porcentaje_aumento,
      periodicidad_aumento_meses: c.periodicidad_aumento_meses,
      cobra_expensa: c.cobra_expensa,
      cobra_agua: c.cobra_agua,
      cobra_luz: c.cobra_luz,
      tipo_aumento: c.tipo_aumento ?? 'MANUAL',
      fecha_ultimo_aumento: c.fecha_ultimo_aumento,
    })
    setContratoEnCurso(!!c.fecha_ultimo_aumento)
    setArchivoFile(null)
    setErrorMsg('')
    // Verificar si ya existen registros pagados para este contrato
    try {
      const res = await api.get(`/contratos/${c.id_contratos}/tiene-pagos`)
      setFechaInicioBlocked(res.data.tiene_pagos)
    } catch {
      setFechaInicioBlocked(false)
    }
    setModal('editar')
  }

  async function guardar() {
    setErrorMsg('')
    if (modal === 'crear') {
      const errores: string[] = []
      if (!form.id_departamentos || form.id_departamentos <= 0) errores.push('Departamento es obligatorio.')
      if (!form.id_inquilinos || form.id_inquilinos <= 0) errores.push('Inquilino es obligatorio.')
      if (!form.fecha_inicio?.trim()) errores.push('Fecha inicio es obligatoria.')
      if (!form.fecha_fin?.trim()) errores.push('Fecha vencimiento es obligatoria.')
      if (!form.alquiler_base_actual || form.alquiler_base_actual <= 0) errores.push('Alquiler base es obligatorio.')
      if (!form.tipo_aumento) errores.push('Tipo de aumento es obligatorio.')
      if (!form.periodicidad_aumento_meses || form.periodicidad_aumento_meses <= 0) {
        errores.push('Periodicidad aumento (meses) es obligatoria.')
      }
      if (errores.length > 0) {
        setErrorMsg(errores.join(' '))
        return
      }
    }
    try {
      let contratoId: number
      if (modal === 'crear') {
        const res = await api.post('/contratos/', form)
        contratoId = res.data.id_contratos
      } else if (modal === 'editar' && selected) {
        const { id_departamentos, id_inquilinos, ...editData } = form
        void id_departamentos; void id_inquilinos
        await api.put(`/contratos/${selected.id_contratos}`, editData)
        contratoId = selected.id_contratos
      } else return

      // Subir archivo si se seleccionó
      if (archivoFile) {
        setUploading(true)
        const fd = new FormData()
        fd.append('archivo', archivoFile)
        await api.post(`/contratos/${contratoId}/archivo`, fd, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        setUploading(false)
      }

      cargar()
      setModal(null)
    } catch (e: unknown) {
      setUploading(false)
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al guardar'
      setErrorMsg(msg)
    }
  }

  async function cerrar(c: Contrato) {
    if (!confirm('¿Cerrar este contrato?')) return
    await api.post(`/contratos/${c.id_contratos}/cerrar`)
    cargar()
  }

  async function descargar(c: Contrato) {
    const res = await api.get(`/contratos/${c.id_contratos}/archivo`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = c.archivo_nombre ?? 'contrato'
    a.click()
    URL.revokeObjectURL(url)
  }

  function depNombre(id: number) {
    const d = departamentos.find(d => d.id_departamentos === id)
    return d ?? null
  }

  function inqNombre(id: number) {
    const i = inquilinos.find(i => i.id_inquilinos === id)
    return i ? i.nombre_apellido : id
  }

  const activos = contratos.filter(c => c.estado === 'activo')
  const finalizados = contratos.filter(c => c.estado !== 'activo')

  // IDs de inquilinos que ya tienen contrato activo NO vencido
  const idsConContratoActivo = new Set(
    contratos
      .filter(c => c.estado === 'activo' && new Date(c.fecha_fin) >= new Date())
      .map(c => c.id_inquilinos)
  )
  // En el selector solo mostrar inquilinos sin contrato activo vigente y con es_actual = true
  const inquilinosDisponibles = inquilinos.filter(i =>
    !idsConContratoActivo.has(i.id_inquilinos) && i.es_actual
  )

  function ContratoRow({ c }: { c: Contrato }) {
    const dep = depNombre(c.id_departamentos)
    return (
      <tr className="hover:bg-gray-50">
        <td className="px-4 py-3 text-left">
          <div className="font-medium text-gray-800">
            {dep ? formatDepto(dep.piso, dep.codigo) : c.id_departamentos}
          </div>
          {dep?.direccion && (
            <div className="text-xs text-gray-400 truncate max-w-[160px]" title={dep.direccion}>
              {dep.direccion}
            </div>
          )}
        </td>
        <td className="px-4 py-3 text-left text-gray-700">{inqNombre(c.id_inquilinos)}</td>
        <td className="px-4 py-3 text-left text-gray-600 text-sm">{formatFecha(c.fecha_inicio)}</td>
        <td className="px-4 py-3 text-left text-gray-600 text-sm">{formatFecha(c.fecha_fin)}</td>
        <td className="px-4 py-3 text-left font-mono">{formatMoneda(c.alquiler_base_actual)}</td>
        <td className="px-4 py-3 text-center">{estadoBadge(c)}</td>
        <td className="px-4 py-3 text-center">
          <div className="flex gap-1 justify-center">
            {c.estado === 'activo' && (
              <>
                <button onClick={() => abrirEditar(c)} className="p-1.5 hover:bg-gray-100 rounded" title="Editar">
                  <Pencil size={14} className="text-gray-500" />
                </button>
                <button onClick={() => cerrar(c)} className="p-1.5 hover:bg-gray-100 rounded" title="Cerrar contrato">
                  <Lock size={14} className="text-orange-500" />
                </button>
              </>
            )}
            {c.archivo_nombre && (
              <button onClick={() => descargar(c)} className="p-1.5 hover:bg-gray-100 rounded" title="Descargar contrato">
                <Download size={14} className="text-blue-500" />
              </button>
            )}
          </div>
        </td>
      </tr>
    )
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Contratos</h2>
        <button
          onClick={abrirCrear}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm"
        >
          <Plus size={16} /> Nuevo contrato
        </button>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select className="border rounded-lg px-3 py-2 text-sm" value={filtroInq} onChange={e => setFiltroInq(e.target.value)}>
          <option value="">Todos los inquilinos</option>
          {inquilinos.map(i => <option key={i.id_inquilinos} value={i.id_inquilinos}>{i.nombre_apellido}</option>)}
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm" value={filtroDep} onChange={e => setFiltroDep(e.target.value)}>
          <option value="">Todos los departamentos</option>
          {departamentos.map(d => <option key={d.id_departamentos} value={d.id_departamentos}>{formatDepto(d.piso, d.codigo)}</option>)}
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm" value={filtroEstado} onChange={e => setFiltroEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          <option value="activo">Activo</option>
          <option value="finalizado">Finalizado</option>
        </select>
        <button onClick={cargar} className="px-4 py-2 text-sm bg-slate-700 text-white rounded-lg hover:bg-slate-800">Buscar</button>
      </div>

      {/* Tabla Activos */}
      <h3 className="font-semibold text-gray-700 mb-2">Contratos activos ({activos.length})</h3>
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mb-6">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Depto</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Inquilino</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Inicio</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Vence</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Alquiler</th>
              <th className="text-center px-4 py-3 font-semibold text-gray-600">Estado</th>
              <th className="text-center px-4 py-3 font-semibold text-gray-600">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {activos.map(c => <ContratoRow key={c.id_contratos} c={c} />)}
          </tbody>
        </table>
        {activos.length === 0 && <div className="py-6 text-center text-gray-400">Sin contratos activos.</div>}
      </div>

      {/* Tabla Finalizados */}
      <h3 className="font-semibold text-gray-700 mb-2">Contratos finalizados ({finalizados.length})</h3>
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Depto</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Inquilino</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Inicio</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Vencimiento</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Alquiler</th>
              <th className="text-center px-4 py-3 font-semibold text-gray-600">Estado</th>
              <th className="text-center px-4 py-3 font-semibold text-gray-600">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {finalizados.map(c => <ContratoRow key={c.id_contratos} c={c} />)}
          </tbody>
        </table>
        {finalizados.length === 0 && <div className="py-6 text-center text-gray-400">Sin contratos finalizados.</div>}
      </div>

      {/* Modal Crear/Editar */}
      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 overflow-y-auto py-6">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-2xl mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg">{modal === 'crear' ? 'Nuevo contrato' : 'Editar contrato'}</h3>
              <button onClick={() => setModal(null)}><X size={18} className="text-gray-500" /></button>
            </div>
            {errorMsg && <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-600">{errorMsg}</div>}
            <div className="grid grid-cols-2 gap-4">
              {modal === 'crear' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Departamento *</label>
                    <select
                      className="w-full border rounded-lg px-3 py-2 text-sm"
                      value={form.id_departamentos}
                      onChange={e => setForm(f => ({ ...f, id_departamentos: Number(e.target.value) }))}
                    >
                      <option value={0}>Seleccionar...</option>
                      {departamentos.filter(d => !d.esta_ocupado).map(d => (
                        <option key={d.id_departamentos} value={d.id_departamentos}>
                          {formatDepto(d.piso, d.codigo)}{d.direccion ? ` — ${d.direccion}` : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Inquilino *</label>
                    <select
                      className="w-full border rounded-lg px-3 py-2 text-sm"
                      value={form.id_inquilinos}
                      onChange={e => setForm(f => ({ ...f, id_inquilinos: Number(e.target.value) }))}
                    >
                      <option value={0}>Seleccionar...</option>
                      {inquilinosDisponibles.map(i => (
                        <option key={i.id_inquilinos} value={i.id_inquilinos}>{i.nombre_apellido}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Fecha inicio *</label>
                    <input type="date" className="w-full border rounded-lg px-3 py-2 text-sm"
                      value={form.fecha_inicio}
                      onChange={e => setForm(f => ({ ...f, fecha_inicio: e.target.value }))}
                    />
                  </div>
                </>
              )}
              {modal === 'editar' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Fecha inicio</label>
                  <input type="date" className={`w-full border rounded-lg px-3 py-2 text-sm ${fechaInicioBlocked ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''}`}
                    value={form.fecha_inicio}
                    disabled={fechaInicioBlocked}
                    onChange={e => setForm(f => ({ ...f, fecha_inicio: e.target.value }))}
                  />
                  {fechaInicioBlocked && (
                    <div className="mt-1.5 flex items-start gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                      <span className="mt-0.5 shrink-0">⚠️</span>
                      <span>
                        La fecha de inicio no puede modificarse porque este contrato ya tiene meses cobrados.
                        Cambiarla alteraría el calendario de aumentos y podría generar inconsistencias en los registros históricos.
                      </span>
                    </div>
                  )}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Fecha vencimiento *</label>
                <input type="date" className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.fecha_fin}
                  onChange={e => setForm(f => ({ ...f, fecha_fin: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Alquiler base *</label>
                <input type="number" className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.alquiler_base_actual || ''}
                  onChange={e => setForm(f => ({ ...f, alquiler_base_actual: Number(e.target.value) }))}
                  placeholder="Por ejemplo: 100000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de aumento</label>
                <select
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.tipo_aumento ?? ''}
                  onChange={e => setForm(f => ({ ...f, tipo_aumento: (e.target.value || undefined) as 'MANUAL' | 'ICL' | undefined }))}
                >
                  <option value="">Seleccionar...</option>
                  <option value="MANUAL">MANUAL — porcentaje fijo</option>
                  <option value="ICL">ICL — Índice para Contratos de Locación (BCRA)</option>
                </select>
              </div>
              {form.tipo_aumento === 'MANUAL' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">% Aumento</label>
                  <input type="number" step="0.1" className="w-full border rounded-lg px-3 py-2 text-sm"
                    value={form.porcentaje_aumento || ''}
                    onChange={e => setForm(f => ({ ...f, porcentaje_aumento: Number(e.target.value) }))}
                    placeholder="Por ejemplo: 8.0"
                  />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Periodicidad aumento (meses)</label>
                <input type="number" className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.periodicidad_aumento_meses || ''}
                  onChange={e => setForm(f => ({ ...f, periodicidad_aumento_meses: e.target.value ? Number(e.target.value) : undefined }))}
                  placeholder="Por ejemplo: 4"
                />
              </div>
            </div>

            {/* Contrato en curso */}
            <div className="mt-4 p-4 rounded-xl border border-gray-200 bg-gray-50">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={contratoEnCurso}
                  onChange={e => {
                    setContratoEnCurso(e.target.checked)
                    if (!e.target.checked) setForm(f => ({ ...f, fecha_ultimo_aumento: undefined }))
                  }}
                />
                ¿Este contrato ya lleva un tiempo en curso?
              </label>
              {contratoEnCurso && (
                <div className="mt-3">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    ¿Cuándo fue el último aumento aplicado? *
                  </label>
                  <input
                    type="date"
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    value={form.fecha_ultimo_aumento ?? ''}
                    onChange={e => setForm(f => ({ ...f, fecha_ultimo_aumento: e.target.value || undefined }))}
                  />
                  <p className="mt-1.5 text-xs text-blue-600 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2">
                    ℹ️ El sistema calculará el próximo aumento a partir de esta fecha + la periodicidad configurada.
                    El monto actual que ingresaste se usará como base sin modificarse.
                  </p>
                </div>
              )}
            </div>

            {/* Checkboxes */}
            <div className="flex flex-wrap gap-4 mt-4">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.cobra_expensa} onChange={e => setForm(f => ({ ...f, cobra_expensa: e.target.checked }))} />
                Cobra expensa
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.cobra_agua} onChange={e => setForm(f => ({ ...f, cobra_agua: e.target.checked }))} />
                Cobra agua
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.cobra_luz} onChange={e => setForm(f => ({ ...f, cobra_luz: e.target.checked }))} />
                Cobra luz
              </label>
            </div>

            {form.cobra_expensa && (
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">Expensa base</label>
                <input type="number" className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.expensa_base_actual || ''}
                  onChange={e => setForm(f => ({ ...f, expensa_base_actual: Number(e.target.value) || undefined }))}
                  placeholder="Por ejemplo: 20000"
                />
              </div>
            )}

            {/* Archivo */}
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contrato (PDF o DOCX)
                {selected?.archivo_nombre && <span className="text-blue-600 ml-2">Actual: {selected.archivo_nombre}</span>}
              </label>
              <input
                type="file"
                accept=".pdf,.docx"
                className="w-full border rounded-lg px-3 py-2 text-sm"
                onChange={e => setArchivoFile(e.target.files?.[0] ?? null)}
              />
            </div>

            <div className="flex gap-2 justify-end mt-5">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100">Cancelar</button>
              <button onClick={guardar} disabled={uploading} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60">
                {uploading ? 'Subiendo...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
