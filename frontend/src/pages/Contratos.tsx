import { useEffect, useState, type ReactNode } from 'react'
import api from '../lib/api'
import type {
  Contrato, ContratoCreate, Departamento, HistorialAumentoDetalle, HistorialAumentoItem, Inquilino,
} from '../lib/types'
import { formatMoneda, formatFecha, MESES } from '../lib/types'
import { Plus, Pencil, X, Download, Lock, FileText, Archive, Eye } from 'lucide-react'
import { Label, clasesCampo, ErrorCamposModal, ModalShell, useToast } from '../lib/ui'

function formatDepto(piso: string | undefined, codigo: string | undefined) {
  if (!piso || !codigo) return `${piso ?? ''} ${codigo ?? ''}`.trim()
  return `${piso} — ${codigo}`
}

type Modal = 'crear' | 'editar' | 'ver' | null

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

function CobrosBadges({ c }: { c: Contrato }) {
  const badges: { texto: string; clase: string }[] = []
  if (c.cobra_expensa) badges.push({ texto: 'Expensa', clase: 'bg-purple-100 text-purple-700' })
  if (c.impuesto_fijo != null) badges.push({ texto: 'Impuesto', clase: 'bg-gray-200 text-gray-700' })
  if (c.cobra_agua) badges.push({ texto: 'Agua', clase: 'bg-sky-100 text-sky-700' })
  if (c.cobra_luz) badges.push({ texto: 'Luz', clase: 'bg-yellow-100 text-yellow-700' })
  if (badges.length === 0) return <span className="text-gray-300 text-sm">—</span>
  return (
    <div className="flex gap-1 justify-center flex-wrap">
      {badges.map(b => (
        <span key={b.texto} className={`text-xs px-2 py-0.5 rounded-full font-semibold ${b.clase}`}>
          {b.texto}
        </span>
      ))}
    </div>
  )
}

function Dato({ etiqueta, mono, children }: { etiqueta: string; mono?: boolean; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 py-0.5">
      <span className="text-gray-500">{etiqueta}</span>
      <span className={`text-gray-800 font-medium text-right ${mono ? 'font-mono whitespace-nowrap' : ''}`}>{children}</span>
    </div>
  )
}

function resumenAumento(c: Contrato) {
  if (c.tipo_aumento === 'SIN_AUMENTO') return 'Sin aumentos'
  const cada = `cada ${c.periodicidad_aumento_meses} meses`
  return c.tipo_aumento === 'MANUAL'
    ? `MANUAL — ${c.porcentaje_aumento} % ${cada}`
    : `ICL — ${cada}`
}

const emptyForm: ContratoCreate = {
  id_departamentos: 0,
  id_inquilinos: 0,
  fecha_inicio: '',
  fecha_fin: '',
  alquiler_base_inicial: undefined,
  expensa_base_inicial: undefined,
  alquiler_base_actual: 0,
  expensa_base_actual: undefined,
  porcentaje_aumento: 0,
  periodicidad_aumento_meses: undefined,
  cobra_expensa: false,
  cobra_agua: false,
  cobra_luz: false,
  impuesto_fijo: undefined,
  tipo_aumento: undefined,
  fecha_ultimo_aumento: undefined,
}

export default function Contratos() {
  const toast = useToast()
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [departamentos, setDepartamentos] = useState<Departamento[]>([])
  const [inquilinos, setInquilinos] = useState<Inquilino[]>([])
  const [modal, setModal] = useState<Modal>(null)
  const [selected, setSelected] = useState<Contrato | null>(null)
  const [form, setForm] = useState<ContratoCreate>(emptyForm)
  const [errorMsg, setErrorMsg] = useState('')
  const [errores, setErrores] = useState<Record<string, string>>({})
  const [popupErrores, setPopupErrores] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [archivoFile, setArchivoFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [fechaInicioBlocked, setFechaInicioBlocked] = useState(false)
  const [contratoEnCurso, setContratoEnCurso] = useState(false)
  const [contratoACerrar, setContratoACerrar] = useState<Contrato | null>(null)
  const [cerrando, setCerrando] = useState(false)
  const [aumentosPendientes, setAumentosPendientes] = useState<Record<number, HistorialAumentoDetalle>>({})
  // Tab activa
  type TabContratos = 'activos' | 'finalizados'
  const [tab, setTab] = useState<TabContratos>('activos')
  // Filtros
  const [filtroInq, setFiltroInq] = useState('')
  const [filtroDep, setFiltroDep] = useState('')

  async function cargar() {
    const [cRes, dRes, iRes, aRes] = await Promise.all([
      api.get('/contratos/', { params: filtrosActivos() }),
      api.get('/departamentos/'),
      api.get('/inquilinos/'),
      api.get('/aumentos/historial', { params: { estado: 'PENDIENTE' } }),
    ])
    setContratos(cRes.data)
    setDepartamentos(dRes.data)
    setInquilinos(iRes.data)
    // Aumento pendiente del mes en curso por contrato: al editar el alquiler,
    // ese monto pasa a ser la nueva base del aumento (lo re-calcula el backend).
    const porContrato: Record<number, HistorialAumentoDetalle> = {}
    for (const item of aRes.data as HistorialAumentoItem[]) {
      if (item.atrasado || item.se_puede_modificar === false) continue
      const id = item.historial.id_contratos
      if (!porContrato[id]) porContrato[id] = item.historial
    }
    setAumentosPendientes(porContrato)
  }

  function filtrosActivos() {
    const p: Record<string, string> = {}
    if (filtroInq) p.id_inquilinos = filtroInq
    if (filtroDep) p.id_departamentos = filtroDep
    return p
  }

  useEffect(() => { cargar() }, [])

  function abrirCrear() {
    setForm(emptyForm)
    setArchivoFile(null)
    setErrorMsg('')
    setErrores({})
    setPopupErrores([])
    setFechaInicioBlocked(false)
    setContratoEnCurso(false)
    setModal('crear')
  }

  async function abrirDetalle(c: Contrato, modo: 'editar' | 'ver') {
    setSelected(c)
    setForm({
      id_departamentos: c.id_departamentos,
      id_inquilinos: c.id_inquilinos,
      fecha_inicio: c.fecha_inicio,
      fecha_fin: c.fecha_fin,
      alquiler_base_inicial: c.alquiler_base_inicial ?? c.alquiler_base_actual,
      expensa_base_inicial: c.expensa_base_inicial ?? c.expensa_base_actual,
      alquiler_base_actual: c.alquiler_base_actual,
      expensa_base_actual: c.expensa_base_actual,
      impuesto_fijo: c.impuesto_fijo,
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
    setErrores({})
    setPopupErrores([])
    setFechaInicioBlocked(false)
    if (modo === 'editar') {
      // Verificar si ya existen registros pagados para este contrato
      try {
        const res = await api.get(`/contratos/${c.id_contratos}/tiene-pagos`)
        setFechaInicioBlocked(res.data.tiene_pagos)
      } catch {
        setFechaInicioBlocked(false)
      }
    }
    setModal(modo)
  }

  function validar(): Record<string, string> {
    const e: Record<string, string> = {}
    if (modal === 'crear') {
      if (!form.id_departamentos || form.id_departamentos <= 0) e.id_departamentos = 'Departamento es obligatorio.'
      if (!form.id_inquilinos || form.id_inquilinos <= 0) e.id_inquilinos = 'Inquilino es obligatorio.'
      if (!form.fecha_inicio?.trim()) e.fecha_inicio = 'Fecha inicio es obligatoria.'
    }
    if (!form.fecha_fin?.trim()) e.fecha_fin = 'Fecha vencimiento es obligatoria.'
    if (!form.tipo_aumento) {
      e.tipo_aumento = 'Tipo de aumento es obligatorio.'
    } else if (form.tipo_aumento === 'MANUAL' && (!form.porcentaje_aumento || form.porcentaje_aumento <= 0)) {
      e.porcentaje_aumento = '% Aumento es obligatorio cuando el tipo es MANUAL.'
    }
    if (form.tipo_aumento !== 'SIN_AUMENTO' &&
        (!form.periodicidad_aumento_meses || form.periodicidad_aumento_meses <= 0)) {
      e.periodicidad_aumento_meses = 'Periodicidad aumento (meses) es obligatoria.'
    }
    if (contratoEnCurso) {
      if (form.tipo_aumento !== 'SIN_AUMENTO' && !form.fecha_ultimo_aumento) {
        e.fecha_ultimo_aumento = 'Fecha del último aumento es obligatoria.'
      }
      if (!form.alquiler_base_inicial || form.alquiler_base_inicial <= 0) {
        e.alquiler_base_inicial = 'Alquiler inicial del contrato es obligatorio.'
      }
      if (!form.alquiler_base_actual || form.alquiler_base_actual <= 0) {
        e.alquiler_base_actual = 'Alquiler actual (último cobro) es obligatorio.'
      }
      if (form.cobra_expensa) {
        if (!form.expensa_base_inicial || form.expensa_base_inicial <= 0) {
          e.expensa_base_inicial = 'Expensa inicial del contrato es obligatoria.'
        }
        if (!form.expensa_base_actual || form.expensa_base_actual <= 0) {
          e.expensa_base_actual = 'Expensa actual (último cobro) es obligatoria.'
        }
      }
    } else {
      if (!form.alquiler_base_actual || form.alquiler_base_actual <= 0) e.alquiler_base_actual = 'Alquiler base es obligatorio.'
    }
    return e
  }

  function limpiarError(campo: string) {
    setErrores(prev => {
      if (!prev[campo]) return prev
      const n = { ...prev }
      delete n[campo]
      return n
    })
  }

  async function guardar() {
    if (saving) return
    setErrorMsg('')
    const e = validar()
    if (Object.keys(e).length > 0) {
      setErrores(e)
      setPopupErrores(Object.values(e))
      return
    }
    setSaving(true)
    try {
      let contratoId: number
      if (modal === 'crear') {
        const res = await api.post('/contratos/', form)
        contratoId = res.data.id_contratos
        toast('Se guardó el contrato correctamente')
      } else if (modal === 'editar' && selected) {
        const { id_departamentos, id_inquilinos, ...editData } = form
        void id_departamentos; void id_inquilinos
        // Los opcionales vacíos viajan como null explícito: `undefined` se
        // omite del JSON y el backend (exclude_unset) no los limpiaría nunca.
        await api.put(`/contratos/${selected.id_contratos}`, {
          ...editData,
          impuesto_fijo: form.impuesto_fijo ?? null,
          expensa_base_actual: form.cobra_expensa ? (form.expensa_base_actual ?? null) : null,
          fecha_ultimo_aumento: form.fecha_ultimo_aumento ?? null,
        })
        contratoId = selected.id_contratos
        toast('Se actualizaron los cambios correctamente')
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
    } catch (err: unknown) {
      setUploading(false)
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al guardar'
      setErrorMsg(msg)
    } finally {
      setSaving(false)
    }
  }

  async function confirmarCierre() {
    if (!contratoACerrar || cerrando) return
    setCerrando(true)
    try {
      await api.post(`/contratos/${contratoACerrar.id_contratos}/cerrar`)
      toast('El contrato se cerró correctamente')
      setContratoACerrar(null)
      cargar()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al cerrar el contrato'
      toast(msg, 'error')
    } finally {
      setCerrando(false)
    }
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

  function depLabel(id: number) {
    const d = depNombre(id)
    return d ? formatDepto(d.piso, d.codigo) : String(id)
  }

  function inqNombre(id: number) {
    const i = inquilinos.find(i => i.id_inquilinos === id)
    return i ? i.nombre_apellido : id
  }

  const activos = contratos.filter(c => c.estado === 'activo')
  const finalizados = contratos.filter(c => c.estado !== 'activo')
  // Contratos finalizados: el modal muestra los mismos campos que la edición,
  // pero ningún dato puede alterarse.
  const soloLectura = modal === 'ver'
  const aumentoPendiente = modal === 'editar' && selected
    ? aumentosPendientes[selected.id_contratos]
    : undefined
  const alquilerConAumento = aumentoPendiente
    ? Math.round((form.alquiler_base_actual || 0) * (1 + aumentoPendiente.porcentaje_alquiler_propuesto / 100))
    : 0

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
        <td className="px-4 py-3 text-center text-gray-600 text-sm">{formatFecha(c.fecha_inicio)}</td>
        <td className="px-4 py-3 text-center text-gray-600 text-sm">{formatFecha(c.fecha_fin)}</td>
        <td className="px-4 py-3 text-left font-mono whitespace-nowrap">{formatMoneda(c.alquiler_base_actual)}</td>
        <td className="px-4 py-3 text-center"><CobrosBadges c={c} /></td>
        <td className="px-4 py-3 text-center">{estadoBadge(c)}</td>
        <td className="px-4 py-3 text-center">
          <div className="flex gap-1 justify-center whitespace-nowrap">
            {c.estado === 'activo' ? (
              <>
                <button onClick={() => abrirDetalle(c, 'editar')} className="p-1.5 hover:bg-gray-100 rounded" title="Editar">
                  <Pencil size={14} className="text-gray-500" />
                </button>
                <button onClick={() => setContratoACerrar(c)} className="p-1.5 hover:bg-gray-100 rounded" title="Cerrar contrato">
                  <Lock size={14} className="text-orange-500" />
                </button>
              </>
            ) : (
              <button onClick={() => abrirDetalle(c, 'ver')} className="p-1.5 hover:bg-gray-100 rounded" title="Ver datos del contrato">
                <Eye size={14} className="text-gray-500" />
              </button>
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

      {/* Tabs */}
      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-xl w-fit">
        <button
          onClick={() => setTab('activos')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            tab === 'activos' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <FileText size={15} />
          Contratos activos
          <span className={`text-xs px-1.5 py-0.5 rounded-full font-semibold ${
            tab === 'activos' ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-500'
          }`}>{activos.length}</span>
        </button>
        <button
          onClick={() => setTab('finalizados')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            tab === 'finalizados' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Archive size={15} />
          Contratos finalizados
          <span className={`text-xs px-1.5 py-0.5 rounded-full font-semibold ${
            tab === 'finalizados' ? 'bg-gray-700 text-white' : 'bg-gray-200 text-gray-500'
          }`}>{finalizados.length}</span>
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
        <button
          onClick={cargar}
          className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium bg-slate-700 text-white rounded-lg hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-300 transition"
        >
          Buscar
        </button>
      </div>

      {/* Tabla según tab activa */}
      {tab === 'activos' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-x-auto">
          <table className="w-full text-sm min-w-[760px]">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Depto</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Inquilino</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Inicio</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Vence</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Alquiler</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Incluye</th>
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
      )}

      {tab === 'finalizados' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-x-auto">
          <table className="w-full text-sm min-w-[760px]">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Depto</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Inquilino</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Inicio</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Vencimiento</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Alquiler</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Incluye</th>
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
      )}

      {/* Modal Crear / Editar / Ver (finalizados, solo lectura) */}
      {modal && (
        <ModalShell max="max-w-3xl">
          <div className="p-6">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <h3 className="font-bold text-lg">
                  {modal === 'crear'
                    ? 'Nuevo contrato'
                    : `${soloLectura ? 'Detalle del contrato' : 'Editar contrato'} — ${selected ? inqNombre(selected.id_inquilinos) : ''}`}
                </h3>
                {soloLectura && selected && (
                  <p className="text-sm text-gray-500 mt-0.5">
                    {depLabel(selected.id_departamentos)} · contrato finalizado: los datos no pueden modificarse.
                  </p>
                )}
              </div>
              <button onClick={() => setModal(null)}><X size={18} className="text-gray-500" /></button>
            </div>
            {errorMsg && <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-600">{errorMsg}</div>}
            <div className="grid grid-cols-2 gap-4">
              {modal === 'crear' && (
                <>
                  <div>
                    <Label required>Departamento</Label>
                    <select
                      className={clasesCampo(errores, 'id_departamentos')}
                      value={form.id_departamentos}
                      onChange={e => { limpiarError('id_departamentos'); setForm(f => ({ ...f, id_departamentos: Number(e.target.value) })) }}
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
                    <Label required>Inquilino</Label>
                    <select
                      className={clasesCampo(errores, 'id_inquilinos')}
                      value={form.id_inquilinos}
                      onChange={e => { limpiarError('id_inquilinos'); setForm(f => ({ ...f, id_inquilinos: Number(e.target.value) })) }}
                    >
                      <option value={0}>Seleccionar...</option>
                      {inquilinosDisponibles.map(i => (
                        <option key={i.id_inquilinos} value={i.id_inquilinos}>{i.nombre_apellido}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <Label required>Fecha inicio</Label>
                    <input type="date" className={clasesCampo(errores, 'fecha_inicio')}
                      value={form.fecha_inicio}
                      onChange={e => { limpiarError('fecha_inicio'); setForm(f => ({ ...f, fecha_inicio: e.target.value })) }}
                    />
                  </div>
                </>
              )}
              {modal !== 'crear' && (
                <div>
                  <Label>Fecha inicio</Label>
                  <input type="date" className={clasesCampo(errores, 'fecha_inicio')}
                    value={form.fecha_inicio}
                    disabled={fechaInicioBlocked || soloLectura}
                    onChange={e => setForm(f => ({ ...f, fecha_inicio: e.target.value }))}
                  />
                  {fechaInicioBlocked && !soloLectura && (
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
                <Label required>Fecha vencimiento</Label>
                <input type="date" className={clasesCampo(errores, 'fecha_fin')}
                  value={form.fecha_fin}
                  disabled={soloLectura}
                  onChange={e => { limpiarError('fecha_fin'); setForm(f => ({ ...f, fecha_fin: e.target.value })) }}
                />
              </div>
              {!contratoEnCurso && (
                <div>
                  <Label required>Alquiler base</Label>
                  <input type="number" className={clasesCampo(errores, 'alquiler_base_actual')}
                    value={form.alquiler_base_actual || ''}
                    disabled={soloLectura}
                    onChange={e => { limpiarError('alquiler_base_actual'); setForm(f => ({ ...f, alquiler_base_actual: Number(e.target.value) })) }}
                    placeholder="Por ejemplo: 100000"
                  />
                </div>
              )}
              <div>
                <Label required={false}>Impuesto ($)</Label>
                <input type="number" className={clasesCampo(errores, 'impuesto_fijo')}
                  value={form.impuesto_fijo || ''}
                  disabled={soloLectura}
                  onChange={e => setForm(f => ({ ...f, impuesto_fijo: Number(e.target.value) || undefined }))}
                  placeholder="Opcional. Ej: 5000"
                />
                <p className="mt-1 text-xs text-gray-400">Monto fijo mensual. No recibe aumentos.</p>
              </div>
              <div>
                <Label required>Tipo de aumento</Label>
                <select
                  className={clasesCampo(errores, 'tipo_aumento')}
                  value={form.tipo_aumento ?? ''}
                  disabled={soloLectura}
                  onChange={e => {
                    limpiarError('tipo_aumento')
                    if (e.target.value !== 'MANUAL') limpiarError('porcentaje_aumento')
                    if (e.target.value === 'SIN_AUMENTO') {
                      limpiarError('periodicidad_aumento_meses')
                      // Con SIN_AUMENTO, porcentaje y periodicidad no intervienen
                      setForm(f => ({
                        ...f,
                        tipo_aumento: 'SIN_AUMENTO',
                        porcentaje_aumento: 0,
                        periodicidad_aumento_meses: 0,
                      }))
                    } else {
                      setForm(f => ({
                        ...f,
                        tipo_aumento: (e.target.value || undefined) as 'MANUAL' | 'ICL' | undefined,
                        periodicidad_aumento_meses: f.periodicidad_aumento_meses === 0 ? undefined : f.periodicidad_aumento_meses,
                      }))
                    }
                  }}
                >
                  <option value="">Seleccionar...</option>
                  <option value="MANUAL">MANUAL — porcentaje fijo</option>
                  <option value="ICL">ICL — Índice para Contratos de Locación (BCRA)</option>
                  <option value="SIN_AUMENTO">SIN_AUMENTO — contrato sin aumentos</option>
                </select>
                {form.tipo_aumento === 'SIN_AUMENTO' && (
                  <p className="mt-1 text-xs text-gray-400">
                    Este contrato no recibirá aumentos automáticos.
                  </p>
                )}
              </div>
              {form.tipo_aumento === 'MANUAL' && (
                <div>
                  <Label required>% Aumento</Label>
                  <input type="number" step="0.1" className={clasesCampo(errores, 'porcentaje_aumento')}
                    value={form.porcentaje_aumento || ''}
                    disabled={soloLectura}
                    onChange={e => { limpiarError('porcentaje_aumento'); setForm(f => ({ ...f, porcentaje_aumento: Number(e.target.value) })) }}
                    placeholder="Por ejemplo: 8.0"
                  />
                </div>
              )}
              {form.tipo_aumento !== 'SIN_AUMENTO' && (
                <div>
                  <Label required>Periodicidad aumento (meses)</Label>
                  <input type="number" className={clasesCampo(errores, 'periodicidad_aumento_meses')}
                    value={form.periodicidad_aumento_meses || ''}
                    disabled={soloLectura}
                    onChange={e => { limpiarError('periodicidad_aumento_meses'); setForm(f => ({ ...f, periodicidad_aumento_meses: e.target.value ? Number(e.target.value) : undefined })) }}
                    placeholder="Por ejemplo: 4"
                  />
                </div>
              )}
            </div>

            {aumentoPendiente && (
              <div className="mt-4 flex items-start gap-2 px-3 py-2 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-700">
                <span className="mt-0.5 shrink-0">ℹ️</span>
                <span>
                  Este contrato tiene un aumento pendiente de{' '}
                  <strong>{aumentoPendiente.porcentaje_alquiler_propuesto.toFixed(2)} %</strong> para{' '}
                  <strong>{MESES[aumentoPendiente.mes - 1]} {aumentoPendiente.anio}</strong>.
                  El alquiler que cargues acá se toma como base y el aumento se recalcula sobre él:
                  se cobrará <strong className="font-mono">{formatMoneda(alquilerConAumento)}</strong>.
                </span>
              </div>
            )}

            {/* Contrato en curso */}
            <div className="mt-4 p-4 rounded-xl border border-gray-200 bg-gray-50">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={contratoEnCurso}
                  disabled={soloLectura}
                  onChange={e => {
                    setContratoEnCurso(e.target.checked)
                    if (!e.target.checked) {
                      setForm(f => ({
                        ...f,
                        fecha_ultimo_aumento: undefined,
                        alquiler_base_inicial: undefined,
                        expensa_base_inicial: undefined,
                      }))
                      setErrores({})
                    } else {
                      setForm(f => ({
                        ...f,
                        alquiler_base_inicial: f.alquiler_base_inicial ?? f.alquiler_base_actual,
                        expensa_base_inicial: f.expensa_base_inicial ?? f.expensa_base_actual,
                      }))
                    }
                  }}
                />
                ¿Este contrato ya lleva un tiempo en curso?
              </label>
              {contratoEnCurso && (
                <div className="mt-3 grid grid-cols-2 gap-4">
                  <div>
                    <Label required>Alquiler inicial del contrato</Label>
                    <input type="number" className={clasesCampo(errores, 'alquiler_base_inicial')}
                      value={form.alquiler_base_inicial || ''}
                      disabled={soloLectura}
                      onChange={e => { limpiarError('alquiler_base_inicial'); setForm(f => ({ ...f, alquiler_base_inicial: Number(e.target.value) })) }}
                      placeholder="Monto con el que comenzó"
                    />
                  </div>
                  <div>
                    <Label required>Alquiler actual (último cobro)</Label>
                    <input type="number" className={clasesCampo(errores, 'alquiler_base_actual')}
                      value={form.alquiler_base_actual || ''}
                      disabled={soloLectura}
                      onChange={e => { limpiarError('alquiler_base_actual'); setForm(f => ({ ...f, alquiler_base_actual: Number(e.target.value) })) }}
                      placeholder="Lo que se le cobra hoy"
                    />
                  </div>
                  <div className="col-span-2">
                    <Label required>¿Cuándo fue el último aumento aplicado?</Label>
                    <input
                      type="date"
                      className={clasesCampo(errores, 'fecha_ultimo_aumento')}
                      value={form.fecha_ultimo_aumento ?? ''}
                      disabled={soloLectura}
                      onChange={e => { limpiarError('fecha_ultimo_aumento'); setForm(f => ({ ...f, fecha_ultimo_aumento: e.target.value || undefined })) }}
                    />
                  </div>
                  {form.cobra_expensa && (
                    <>
                      <div>
                        <Label required>Expensa inicial del contrato</Label>
                        <input type="number" className={clasesCampo(errores, 'expensa_base_inicial')}
                          value={form.expensa_base_inicial || ''}
                          disabled={soloLectura}
                          onChange={e => { limpiarError('expensa_base_inicial'); setForm(f => ({ ...f, expensa_base_inicial: Number(e.target.value) || undefined })) }}
                          placeholder="Expensa con la que comenzó"
                        />
                      </div>
                      <div>
                        <Label required>Expensa actual (último cobro)</Label>
                        <input type="number" className={clasesCampo(errores, 'expensa_base_actual')}
                          value={form.expensa_base_actual || ''}
                          disabled={soloLectura}
                          onChange={e => { limpiarError('expensa_base_actual'); setForm(f => ({ ...f, expensa_base_actual: Number(e.target.value) || undefined })) }}
                          placeholder="La que se le cobra hoy"
                        />
                      </div>
                    </>
                  )}
                  <div className="col-span-2">
                    <p className="text-xs text-blue-600 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2">
                      ℹ️ El sistema calculará el próximo aumento a partir de esta fecha + la periodicidad configurada,
                      tomando como base el <strong>Alquiler actual</strong>. El monto inicial se conserva como dato histórico del contrato.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Checkboxes */}
            <div className="flex flex-wrap gap-4 mt-4">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.cobra_expensa} disabled={soloLectura} onChange={e => setForm(f => ({ ...f, cobra_expensa: e.target.checked }))} />
                Cobra expensa
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.cobra_agua} disabled={soloLectura} onChange={e => setForm(f => ({ ...f, cobra_agua: e.target.checked }))} />
                Cobra agua
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.cobra_luz} disabled={soloLectura} onChange={e => setForm(f => ({ ...f, cobra_luz: e.target.checked }))} />
                Cobra luz
              </label>
            </div>

            {form.cobra_expensa && !contratoEnCurso && (
              <div className="mt-3">
                <Label required={false}>Expensa base</Label>
                <input type="number" className={clasesCampo(errores, 'expensa_base')}
                  value={form.expensa_base_actual || ''}
                  disabled={soloLectura}
                  onChange={e => setForm(f => ({ ...f, expensa_base_actual: Number(e.target.value) || undefined }))}
                  placeholder="Por ejemplo: 20000"
                />
              </div>
            )}

            {/* Archivo */}
            <div className="mt-4">
              <Label required={false}>
                Contrato (PDF o DOCX)
              </Label>
              {soloLectura ? (
                selected?.archivo_nombre ? (
                  <button
                    onClick={() => selected && descargar(selected)}
                    className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-gray-300 text-blue-600 rounded-lg hover:bg-gray-100"
                  >
                    <Download size={14} /> {selected.archivo_nombre}
                  </button>
                ) : (
                  <p className="text-sm text-gray-400">Sin archivo adjunto.</p>
                )
              ) : (
                <>
                  {selected?.archivo_nombre && <span className="text-blue-600 text-sm ml-2">Actual: {selected.archivo_nombre}</span>}
                  <input
                    type="file"
                    accept=".pdf,.docx"
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    onChange={e => setArchivoFile(e.target.files?.[0] ?? null)}
                  />
                </>
              )}
            </div>

            <div className="flex gap-2 justify-end mt-5">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100">
                {soloLectura ? 'Cerrar' : 'Cancelar'}
              </button>
              {!soloLectura && (
                <button onClick={guardar} disabled={saving || uploading} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60">
                  {saving ? 'Guardando...' : uploading ? 'Subiendo...' : 'Guardar'}
                </button>
              )}
            </div>
          </div>
        </ModalShell>
      )}

      {/* Modal confirmación de cierre de contrato */}
      {contratoACerrar && (() => {
        const c = contratoACerrar
        const dep = depNombre(c.id_departamentos)
        return (
          <ModalShell max="max-w-lg">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center">
                  <Lock size={20} className="text-orange-600" />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-gray-800">Cerrar contrato</h3>
                  <p className="text-sm text-gray-500">Revisá los datos antes de confirmar.</p>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg px-4 py-3 mb-4 text-sm">
                <Dato etiqueta="Departamento">
                  {depLabel(c.id_departamentos)}
                  {dep?.direccion && <span className="block text-xs text-gray-400 font-normal">{dep.direccion}</span>}
                </Dato>
                <Dato etiqueta="Inquilino">{inqNombre(c.id_inquilinos)}</Dato>
                <Dato etiqueta="Inicio">{formatFecha(c.fecha_inicio)}</Dato>
                <Dato etiqueta="Vencimiento">{formatFecha(c.fecha_fin)}</Dato>
                <Dato etiqueta="Alquiler actual" mono>{formatMoneda(c.alquiler_base_actual)}</Dato>
                {c.cobra_expensa && <Dato etiqueta="Expensa actual" mono>{formatMoneda(c.expensa_base_actual)}</Dato>}
                {c.impuesto_fijo != null && <Dato etiqueta="Impuesto" mono>{formatMoneda(c.impuesto_fijo)}</Dato>}
                <Dato etiqueta="Aumento">{resumenAumento(c)}</Dato>
                <div className="flex justify-between gap-4 py-0.5 items-center">
                  <span className="text-gray-500">Incluye</span>
                  <CobrosBadges c={c} />
                </div>
                <div className="flex justify-between gap-4 py-0.5 items-center">
                  <span className="text-gray-500">Estado</span>
                  {estadoBadge(c)}
                </div>
              </div>

              <div className="flex items-start gap-2 p-3 mb-5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
                <span className="mt-0.5 shrink-0">⚠️</span>
                <span>
                  El contrato pasa a <strong>Finalizado</strong>: se libera el departamento si no le queda otro
                  contrato activo, el inquilino queda como <strong>Anterior</strong> si no tiene otros contratos y
                  no se generan más registros ni aumentos para este contrato.
                </span>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setContratoACerrar(null)}
                  disabled={cerrando}
                  className="flex-1 px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 active:bg-red-800 disabled:opacity-60 transition font-medium"
                >
                  No, cancelar
                </button>
                <button
                  onClick={confirmarCierre}
                  disabled={cerrando}
                  className="flex-1 px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 disabled:opacity-60 transition font-semibold"
                >
                  {cerrando ? 'Cerrando...' : 'Sí, cerrar contrato'}
                </button>
              </div>
            </div>
          </ModalShell>
        )
      })()}

      <ErrorCamposModal errores={popupErrores} onCerrar={() => setPopupErrores([])} />
    </div>
  )
}
