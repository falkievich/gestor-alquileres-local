export interface Departamento {
  id_departamentos: number
  piso: string
  codigo: string
  direccion?: string
  esta_ocupado: boolean
}

export interface DepartamentoCreate {
  piso: string
  codigo: string
  direccion?: string
}

export interface Inquilino {
  id_inquilinos: number
  nombre_apellido: string
  telefono?: string
  es_actual: boolean
}

export interface InquilinoCreate {
  nombre_apellido: string
  telefono?: string
  es_actual?: boolean
}

export interface Contrato {
  id_contratos: number
  id_departamentos: number
  id_inquilinos: number
  fecha_inicio: string
  fecha_fin: string
  estado: string
  alquiler_base_inicial?: number
  expensa_base_inicial?: number
  alquiler_base_actual: number
  expensa_base_actual?: number
  porcentaje_aumento: number
  periodicidad_aumento_meses: number
  ultimo_aumento_anio?: number
  ultimo_aumento_mes?: number
  fecha_ultimo_aumento?: string
  cobra_expensa: boolean
  cobra_agua: boolean
  cobra_luz: boolean
  impuesto_fijo?: number
  tipo_aumento: 'MANUAL' | 'ICL'
  archivo_nombre?: string
}

export interface ContratoCreate {
  id_departamentos: number
  id_inquilinos: number
  fecha_inicio: string
  fecha_fin: string
  alquiler_base_inicial?: number
  expensa_base_inicial?: number
  alquiler_base_actual: number
  expensa_base_actual?: number
  porcentaje_aumento?: number
  periodicidad_aumento_meses?: number
  cobra_expensa?: boolean
  cobra_agua?: boolean
  cobra_luz?: boolean
  impuesto_fijo?: number
  tipo_aumento?: 'MANUAL' | 'ICL'
  fecha_ultimo_aumento?: string
}

export interface RegistroMensual {
  id_registros_mensuales: number
  id_contratos: number
  anio: number
  mes: number
  alquiler_calculado: number
  expensa_calculada?: number
  alquiler_override?: number
  expensa_override?: number
  nota_override?: string
  agua?: number
  luz?: number
  impuesto?: number
  pagado: boolean
  total: number
  porcentaje_aumento_usado?: number
}

export interface DashboardItem {
  contrato: Contrato
  registro: RegistroMensual
  departamento: Departamento
  inquilino: Inquilino
  estado_servicios: 'OK' | 'Pendiente'
  vencido: boolean
  anio: number
  mes: number
  total: number
}

export interface HistorialItem {
  contrato: Contrato
  inquilino: Inquilino
}

export interface PagoItem {
  registro: RegistroMensual
  inquilino?: Inquilino
  departamento?: Departamento
  contrato_id: number
}

export interface AumentoItem {
  contrato: Contrato
  departamento: Departamento
  inquilino: Inquilino
  proximo_aumento: {
    proximo_anio?: number
    proximo_mes?: number
    alquiler_actual: number
    alquiler_nuevo?: number
    expensa_actual?: number
    expensa_nueva?: number
    porcentaje?: number
    requires_fecha_ultimo?: boolean
    tipo_aumento?: 'MANUAL' | 'ICL'
    // campos ICL
    icl_pendiente?: boolean
    icl_error?: string
    ultima_fecha_disponible_bcra?: string
    dias_faltantes?: number
    icl_inicial?: number
    icl_final?: number
    icl_coeficiente?: number
    icl_calculado?: boolean
    icl_aplicable?: boolean
    fecha_vigencia?: string
    aumento_fuera_de_contrato?: boolean
  }
  alerta?: string
}

export interface AumentoHistorialItem {
  registro: RegistroMensual
  contrato: Contrato
  departamento: Departamento
  inquilino: Inquilino
  alquiler_anterior: number | null
  alquiler_nuevo: number
}

export const PISOS = ['Planta baja', 'Piso 1', 'Piso 2', 'Piso 3']

export const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

export function formatMes(mes: number, anio: number) {
  return `${MESES[mes - 1]} ${anio}`
}

export function formatMoneda(valor?: number) {
  if (valor == null) return '-'
  return `$${valor.toLocaleString('es-AR')}`
}

export function formatFecha(fecha?: string) {
  if (!fecha) return '-'
  const [anio, mes, dia] = fecha.split('-')
  return `${dia}/${mes}/${anio}`
}
