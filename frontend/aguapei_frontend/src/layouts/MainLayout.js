import React from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import './MainLayout.css';

function MainLayout() {
    const navigate = useNavigate();

    // A função de logout agora é passada para a Sidebar
    const handleLogout = () => {
        localStorage.removeItem('authToken');
        navigate('/');
    };

    return (
        <div className="main-layout">
            {/* O próprio Sidebar agora controla se está aberto ou fechado.
                Nós só precisamos passar a função de logout. */}
            <Sidebar handleLogout={handleLogout} />
            
            <main className="content-area">
                {/* O conteúdo (ex: Agenda) aparece aqui */}
                <Outlet />
            </main>
        </div>
    );
}

export default MainLayout;

