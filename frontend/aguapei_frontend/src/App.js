/**
 * App.js
 * -------
 * Ponto de entrada da SPA. Define rotas públicas (login) e protegidas,
 * envolve tudo com o BrowserRouter e configura o ToastContainer global
 * usado para feedbacks vindos dos interceptors de API.
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import Login from './pages/Login';
import AgendaDashboard from './pages/AgendaDashboard';
import ClientesPage from './pages/ClientesPage';
import QuartosPage from './pages/QuartosPage';
import BarcosPage from './pages/BarcosPage';
import GestaoPage from './pages/GestaoPage';
import ConsumoPage from './pages/ConsumoPage';
import ContasEmBordoPage from './pages/ContasEmBordoPage';
import MainLayout from './layouts/MainLayout';
import {
  canAccessDesktopRoute,
  clearAuthStorage,
  getUsuarioLocal,
  isDesktopUser,
} from './services/accessControl';

// Gatekeeper das rotas internas: verifica token e decide se carrega o layout.
const ProtectedRoutes = () => {
  const token = localStorage.getItem('authToken');
  const usuario = getUsuarioLocal();

  if (!token || !isDesktopUser(usuario)) {
    clearAuthStorage();
    return <Navigate to="/" replace />;
  }

  return <MainLayout />;
};

const ProtectedPage = ({ path, children }) => {
  const usuario = getUsuarioLocal();

  if (!canAccessDesktopRoute(path, usuario)) {
    return <Navigate to="/agenda" replace />;
  }

  return children;
};

function App() {
  return (
    <BrowserRouter>
      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />
      <Routes>
        <Route path="/" element={<Login />} />
        <Route element={<ProtectedRoutes />}>
          <Route path="/agenda" element={<ProtectedPage path="/agenda"><AgendaDashboard /></ProtectedPage>} />
          <Route path="/clientes" element={<ProtectedPage path="/clientes"><ClientesPage /></ProtectedPage>} />
          <Route path="/quartos" element={<ProtectedPage path="/quartos"><QuartosPage /></ProtectedPage>} />
          <Route path="/barcos" element={<ProtectedPage path="/barcos"><BarcosPage /></ProtectedPage>} />
          <Route path="/consumo" element={<ProtectedPage path="/consumo"><ConsumoPage /></ProtectedPage>} />
          <Route path="/contas-em-bordo" element={<ProtectedPage path="/contas-em-bordo"><ContasEmBordoPage /></ProtectedPage>} />
          <Route path="/gestao" element={<ProtectedPage path="/gestao"><GestaoPage /></ProtectedPage>} />
        </Route>
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
