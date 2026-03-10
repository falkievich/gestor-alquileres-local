import { useEffect, useState } from 'react'
import api from '../lib/api'
import type { DashboardItem } from '../lib/types'
import { MESES } from '../lib/types'
import { Save } from 'lucide-react'

interface ServicioRow {
  contrato: DashboardItem['contrato']
  registro: DashboardItem['registro']
  departamento: DashboardItem['departamento']
  inquilino: DashboardItem['inquilino']
}

export default function Servicios() {
  const [items, setItems] = useState<ServicioRow[]>([])
  const [valores, setValores] = useState<Record<number, { agua: string; luz: string }>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<number | null>(null)
  const [successMsg, setSuccessMsg] = useState('')
  const [anioMes, setAnioMes] = useState('')

  async function cargar() {
    setLoading(true)
    const res = await api.get('/servicios/pendientes')
    setItems(res.data)
    if (res.data.length > 0) {
      const item = res.data[0]
      setAnioMes(`${MESES[item.registro.mes - 1]} ${item.registro.anio}`)
    }
    // Inicializar valores
    const init: Record<number, { agua: string; luz: string }> = {}
    for (const item of res.data) {
      init[item.registro.id_registros_mensuales] = {
        agua: item.registro.agua?.toString() ?? '',
        luz: item.registro.luz?.toString() ?? '',
      }
    }
    setValores(init)
    setLoading(false)
  }

  useEffect(() => { cargar() }, [])

  async function guardarFila(idReg: number, cobra_agua: boolean, cobra_luz: boolean) {
    setSaving(idReg)
    const v = valores[idReg] ?? {}
    const params: Record<string, string> = {}
    if (cobra_agua && v.agua !== '') params.agua = v.agua
    if (cobra_luz && v.luz !== '') params.luz = v.luz
    await api.post('/servicios/guardar', null, { params: { id_registro: idReg, ...params } })
    setSuccessMsg('Guardado correctamente')
    setTimeout(() => setSuccessMsg(''), 3000)
    setSaving(null)
    cargar()
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Carga de Servicios</h2>
          {anioMes && <p className="text-gray-500 text-sm mt-1">Mes actual: {anioMes}</p>}
        </div>
      </div>

      {successMsg && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">{successMsg}</div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Cargando...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-4xl mb-3">✅</div>
          <p className="text-gray-500">No hay servicios pendientes de cargar.</p>
          <p className="text-gray-400 text-sm mt-1">Todos los contratos que cobran agua/luz ya tienen sus valores cargados.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Departamento</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Inquilino</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Agua ($)</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Luz ($)</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-600">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map(item => {
                const idReg = item.registro.id_registros_mensuales
                const v = valores[idReg] ?? { agua: '', luz: '' }
                return (
                  <tr key={idReg} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">
                      {item.departamento?.piso} {item.departamento?.codigo}
                    </td>
                    <td className="px-4 py-3 text-gray-700">{item.inquilino?.nombre_apellido}</td>
                    <td className="px-4 py-3 text-center">
                      {item.contrato.cobra_agua ? (
                        <input
                          type="number"
                          className="w-28 border rounded-lg px-3 py-1.5 text-sm text-center"
                          value={v.agua}
                          onChange={e => setValores(prev => ({
                            ...prev,
                            [idReg]: { ...prev[idReg], agua: e.target.value }
                          }))}
                          placeholder="0"
                        />
                      ) : (
                        <span className="text-gray-400">No cobra</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {item.contrato.cobra_luz ? (
                        <input
                          type="number"
                          className="w-28 border rounded-lg px-3 py-1.5 text-sm text-center"
                          value={v.luz}
                          onChange={e => setValores(prev => ({
                            ...prev,
                            [idReg]: { ...prev[idReg], luz: e.target.value }
                          }))}
                          placeholder="0"
                        />
                      ) : (
                        <span className="text-gray-400">No cobra</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => guardarFila(idReg, item.contrato.cobra_agua, item.contrato.cobra_luz)}
                        disabled={saving === idReg}
                        className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60 mx-auto"
                      >
                        <Save size={14} />
                        {saving === idReg ? 'Guardando...' : 'Guardar'}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
