import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Departamentos from './pages/Departamentos'
import Inquilinos from './pages/Inquilinos'
import Contratos from './pages/Contratos'
import Servicios from './pages/Servicios'
import Aumentos from './pages/Aumentos'
import {
  LayoutDashboard,
  Building2,
  Users,
  FileText,
  Droplets,
  TrendingUp,
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/departamentos', label: 'Departamentos', icon: Building2 },
  { to: '/inquilinos', label: 'Inquilinos', icon: Users },
  { to: '/contratos', label: 'Contratos', icon: FileText },
  { to: '/servicios', label: 'Servicios', icon: Droplets },
  { to: '/aumentos', label: 'Aumentos', icon: TrendingUp },
]

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-gray-50">
        <aside className="w-60 bg-slate-800 text-white flex flex-col shadow-lg">
          <div className="px-6 py-5 border-b border-slate-700">
            <h1 className="text-lg font-bold text-white leading-tight">
              🏠 Gestor
            </h1>
            <p className="text-slate-400 text-xs mt-0.5">Alquileres</p>
          </div>
          <nav className="flex-1 px-3 py-4 space-y-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                  }`
                }
              >
                <Icon size={18} />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="px-4 py-3 border-t border-slate-700 text-xs text-slate-500">
            Gestor de Alquileres - v1.0
          </div>
        </aside>

        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/departamentos" element={<Departamentos />} />
            <Route path="/inquilinos" element={<Inquilinos />} />
            <Route path="/contratos" element={<Contratos />} />
            <Route path="/servicios" element={<Servicios />} />
            <Route path="/aumentos" element={<Aumentos />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
