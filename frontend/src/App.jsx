import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar.jsx'
import Landing from './pages/Landing.jsx'
import Dashboard from './pages/Dashboard.jsx'
import LiveDetection from './pages/LiveDetection.jsx'
import Analytics from './pages/Analytics.jsx'
import Complaints from './pages/Complaints.jsx'
import Reports from './pages/Reports.jsx'
import Settings from './pages/Settings.jsx'
import About from './pages/About.jsx'

function AppShell({ children }) {
  return (
    <div className="flex h-screen w-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-y-auto bg-grid-lines bg-grid">{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route
        path="/dashboard"
        element={
          <AppShell>
            <Dashboard />
          </AppShell>
        }
      />
      <Route
        path="/live"
        element={
          <AppShell>
            <LiveDetection />
          </AppShell>
        }
      />
      <Route
        path="/analytics"
        element={
          <AppShell>
            <Analytics />
          </AppShell>
        }
      />
      <Route
        path="/complaints"
        element={
          <AppShell>
            <Complaints />
          </AppShell>
        }
      />
      <Route
        path="/reports"
        element={
          <AppShell>
            <Reports />
          </AppShell>
        }
      />
      <Route
        path="/settings"
        element={
          <AppShell>
            <Settings />
          </AppShell>
        }
      />
      <Route
        path="/about"
        element={
          <AppShell>
            <About />
          </AppShell>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
