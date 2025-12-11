/**
 * MainLayout.js
 * -------------
 * Layout base das rotas protegidas. Renderiza a Sidebar fixa e injeta o
 * conteúdo da rota atual através do <Outlet /> do React Router.
 */
import React from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import './MainLayout.css';

/**
 * MainLayout
 * ----------
 * Responsável por envolver todas as rotas protegidas.
 * Abre a Sidebar fixa (que precisa da função de logout) e renderiza
 * o conteúdo correspondente via `<Outlet />`. Não faz chamadas ao backend
 * diretamente, mas guarda o responsável por limpar o `authToken`.
 */
function MainLayout() {
    const navigate = useNavigate();

    /**
     * Realiza o logout no front-end.
     * Remove o token local (impacta autenticação) e redireciona para login.
     * Não há retorno; apenas efeitos colaterais.
     */
    const handleLogout = () => {
        localStorage.removeItem('authToken');
        navigate('/');
    };

    return (
        <div className="main-layout">
            <Sidebar handleLogout={handleLogout} />
            
            <main className="content-area">
                {/* As rotas filhas protegidas (Agenda, Clientes, etc.) são renderizadas aqui */}
                <Outlet />
            </main>
        </div>
    );
}

export default MainLayout;