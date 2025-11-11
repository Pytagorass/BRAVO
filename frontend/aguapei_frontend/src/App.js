import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// 🎓 Importamos o Toastify (veja Passo 3)
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import Login from './pages/Login';
import AgendaDashboard from './pages/AgendaDashboard';
import ClientesPage from './pages/ClientesPage';
import QuartosPage from './pages/QuartosPage'; 
import MainLayout from './layouts/MainLayout';
import GestaoPage from './pages/GestaoPage';



const ProtectedRoutes = () => {
    const token = localStorage.getItem('authToken');
    // Se o token existir, renderiza o MainLayout, que cuidará da página
    return token ? <MainLayout /> : <Navigate to="/" />;
};

function App() {
  return (
    <BrowserRouter>
    {/* 🎓 Container global para os TOASTS */}
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
        {/* Rota de Login (Pública) */}
        <Route path="/" element={<Login />} />
        
        {/* Rotas Protegidas (que usarão nosso MainLayout) */}
        <Route element={<ProtectedRoutes />}>
          <Route path="/agenda" element={<AgendaDashboard />} />
          <Route path="/clientes" element={<ClientesPage />} /> 
          <Route path="/quartos" element={<QuartosPage />} /> 
          <Route path="/gestao" element={<GestaoPage />} />
        </Route>
        
        {/* Redireciona qualquer rota não encontrada para a página inicial */}
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

