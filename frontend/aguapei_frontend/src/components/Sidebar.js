/**
 * Sidebar.js
 * -----------
 * Componente responsável pelo menu principal da aplicação autenticada.
 * É renderizado pelo MainLayout e controla:
 *  - Navegação entre Agenda, Clientes, Quartos e Gestão (React Router).
 *  - Acesso rápido ao modal de edição de perfil.
 *  - Ação de logout disparada pelo botão "Sair".
 *
 * O estado visual (aberto/fechado) e o nome do usuário são mantidos
 * localmente para preservar a experiência entre interações.
 */

import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import './Sidebar.css';
import UsuarioModal from './UsuarioModal';

// Ícones inline utilizados nos links. Mantidos simples para evitar imports extras.
const IconAgenda = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8 2v4"></path><path d="M16 2v4"></path><rect width="18" height="18" x="3" y="4" rx="2"></rect><path d="M3 10h18"></path></svg>;
const IconClientes = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M22 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>;
const IconQuartos = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 8v11a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-9.3-5.3a2 2 0 0 0-1.4 0L2 8Z"></path><path d="m6 19 6-6 6 6"></path><path d="M4 21v-9a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9"></path></svg>;
const IconBarcos = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 17h18"></path><path d="M5 17 3 9h18l-2 8"></path><path d="M8 9V5h8v4"></path><path d="M12 5V3"></path><path d="M6 21c1.5 0 1.5-1 3-1s1.5 1 3 1 1.5-1 3-1 1.5 1 3 1"></path></svg>;
const IconGestao = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"></path><path d="m19 9-5 5-4-4-3 3"></path></svg>;
const IconMenu = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>;
const IconSair = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>;

/**
 * Sidebar component
 *
 * @param {Function} handleLogout - Função enviada pelo layout para remover token e redirecionar.
 */
function Sidebar({ handleLogout }) {
    const [isOpen, setIsOpen] = useState(true);
    const [showUsuarioModal, setShowUsuarioModal] = useState(false);
    const [nomeUsuario, setNomeUsuario] = useState('Usuário');

    useEffect(() => {
        // Obtém o nome salvo durante o login/edição de perfil.
        try {
            const usuarioJSON = localStorage.getItem('usuario');
            if (usuarioJSON) {
                const usuario = JSON.parse(usuarioJSON);
                setNomeUsuario(usuario.nome);
            }
        } catch (e) {
            console.error('Falha ao ler usuário do localStorage', e);
        }
    }, []);

    const toggleSidebar = () => setIsOpen((prev) => !prev);

    const handleProfileClick = () => setShowUsuarioModal(true);

    const handleModalClose = () => {
        setShowUsuarioModal(false);
        // Caso o nome tenha sido alterado no modal, recarregamos o localStorage.
        const usuarioJSON = localStorage.getItem('usuario');
        if (usuarioJSON) {
            const usuario = JSON.parse(usuarioJSON);
            setNomeUsuario(usuario.nome);
        }
    };

    return (
        <>
            <aside className={`sidebar ${!isOpen ? 'closed' : ''}`}>
                <div className="sidebar-header">
                    <img
                        src='/LogoBravo.ico'
                        alt='Logo Bravo'
                        className="sidebar-logo"
                    />
                    <h2 className="sidebar-title" style={{ display: isOpen ? 'block' : 'none' }}>
                        BRAVO
                    </h2>
                    <button className="sidebar-toggle-btn" onClick={toggleSidebar}>
                        <IconMenu />
                    </button>
                </div>

                <nav className="sidebar-nav">
                    <NavLink to="/agenda" title="Agenda">
                        <IconAgenda />
                        <span className="link-text">Agenda</span>
                    </NavLink>
                    <NavLink to="/clientes" title="Clientes">
                        <IconClientes />
                        <span className="link-text">Clientes</span>
                    </NavLink>
                    <NavLink to="/quartos" title="Quartos">
                        <IconQuartos />
                        <span className="link-text">Quartos</span>
                    </NavLink>
                    <NavLink to="/barcos" title="Barcos">
                        <IconBarcos />
                        <span className="link-text">Barcos</span>
                    </NavLink>
                    <NavLink to="/gestao" title="Gestão">
                        <IconGestao />
                        <span className="link-text">Gestão</span>
                    </NavLink>
                </nav>

                <div className="sidebar-footer">
                    {/* Botão de perfil abre o modal para editar nome/email/senha */}
                    <button className="user-profile-button" onClick={handleProfileClick} title="Editar Perfil">
                        <div className="user-profile">
                            <span className="user-avatar">
                                {nomeUsuario ? nomeUsuario.charAt(0).toUpperCase() : '?'}
                            </span>
                            <span className="user-name" style={{ display: isOpen ? 'block' : 'none' }}>
                                {nomeUsuario}
                            </span>
                        </div>
                    </button>

                    {/* Botão de logout delega a lógica (limpar token/navegar) ao layout */}
                    <button onClick={handleLogout} className="logout-btn" title="Sair">
                        <IconSair />
                        <span className="link-text" style={{ display: isOpen ? 'block' : 'none' }}>Sair</span>
                    </button>
                </div>
            </aside>

            {/* Modal fica sempre montado para preservar formulário; visibilidade é controlada via state */}
            <UsuarioModal show={showUsuarioModal} handleClose={handleModalClose} />
        </>
    );
}

export default Sidebar;
