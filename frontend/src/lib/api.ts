import axios from 'axios'

// En dev (npm run dev) apunta a localhost:8000.
// En producción (build servido por FastAPI) usa rutas relativas al mismo origen.
const api = axios.create({
  baseURL: import.meta.env.DEV ? 'http://localhost:8000' : '',
})

export default api
