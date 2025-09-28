import React, { useState, Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Login';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import ErrorBoundary from './components/ErrorBoundary';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { WebSocketProvider } from './contexts/WebSocketContext';
import './i18n/config';

// Lazy load components for code splitting
const Dashboard = lazy(() => import('./components/Dashboard'));
const Users = lazy(() => import('./components/Users'));
const Messages = lazy(() => import('./components/Messages'));
const BotControls = lazy(() => import('./components/BotControls'));
const AuditLogs = lazy(() => import('./components/AuditLogs'));
const MapView = lazy(() => import('./components/MapView'));
const ZoneManager = lazy(() => import('./components/ZoneManager'));
const UserGroups = lazy(() => import('./components/UserGroups'));
const AlertManager = lazy(() => import('./components/AlertManager'));
const AlertConfig = lazy(() => import('./components/AlertConfig'));
const Processes = lazy(() => import('./components/Processes'));
const Analytics = lazy(() => import('./components/Analytics'));
const BotResponseTemplates = lazy(() => import('./components/BotResponseTemplates'));

function AppContent() {
  const { isAuthenticated, loading } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-accent-cyan"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <div className="min-h-screen-safe bg-dark-900 text-white pt-safe-top pb-safe-bottom">
      <Header onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
      <div className="flex min-h-screen-safe">
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <main className="flex-1 p-4 md:p-6 scroll-smooth-touch">
          <Suspense fallback={
            <div className="flex items-center justify-center min-h-96">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-cyan"></div>
            </div>
          }>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/users" element={<Users />} />
              <Route path="/messages" element={<Messages />} />
              <Route path="/map" element={<MapView />} />
              <Route path="/zones" element={<ZoneManager />} />
              <Route path="/user-groups" element={<UserGroups />} />
              <Route path="/alerts" element={<AlertManager />} />
              <Route path="/alert-config" element={<AlertConfig />} />
              <Route path="/processes" element={<Processes />} />
              <Route path="/bot-controls" element={<BotControls />} />
              <Route path="/audit" element={<AuditLogs />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/bot-templates" element={<BotResponseTemplates />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <WebSocketProvider>
          <Router>
            <AppContent />
          </Router>
        </WebSocketProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;