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
import MainLayout from './layouts/MainLayout';

// Gatekeeper das rotas internas: verifica token e decide se carrega o layout.
const ProtectedRoutes = () => {
  const token = localStorage.getItem('authToken');
  return token ? <MainLayout /> : <Navigate to="/" />;
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
          <Route path="/agenda" element={<AgendaDashboard />} />
          <Route path="/clientes" element={<ClientesPage />} />
          <Route path="/quartos" element={<QuartosPage />} />
          <Route path="/barcos" element={<BarcosPage />} />
          <Route path="/consumo" element={<ConsumoPage />} />
          <Route path="/gestao" element={<GestaoPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
