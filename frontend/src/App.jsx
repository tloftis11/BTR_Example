import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Nav from './components/Layout/Nav'
import LandingPage from './pages/LandingPage'
import DashboardPage from './pages/DashboardPage'
import AboutPage from './pages/AboutPage'
import IntelPage from './pages/IntelPage'

function AppShell({ children }) {
  return (
    <div className="app-shell">
      <Nav />
      <div className="main-content">{children}</div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"          element={<LandingPage />} />
        <Route path="/dashboard" element={<AppShell><DashboardPage /></AppShell>} />
        <Route path="/intel"     element={<AppShell><IntelPage /></AppShell>} />
        <Route path="/about"     element={<AppShell><AboutPage /></AppShell>} />
      </Routes>
    </BrowserRouter>
  )
}
