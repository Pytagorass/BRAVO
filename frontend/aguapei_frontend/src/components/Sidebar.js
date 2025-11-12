import React, { useState, useEffect } from 'react'; // --- 1. Importa useState e useEffect ---
import { NavLink } from 'react-router-dom';
import './Sidebar.css';
import UsuarioModal from './UsuarioModal'; // --- 2. Importa o novo modal ---

// --- (Ícones SVG - Sem mudanças) ---
const IconAgenda = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8 2v4"></path><path d="M16 2v4"></path><rect width="18" height="18" x="3" y="4" rx="2"></rect><path d="M3 10h18"></path></svg>;
const IconClientes = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M22 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>;
const IconQuartos = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 8v11a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-9.3-5.3a2 2 0 0 0-1.4 0L2 8Z"></path><path d="m6 19 6-6 6 6"></path><path d="M4 21v-9a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9"></path></svg>;
const IconGestao = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"></path><path d="m19 9-5 5-4-4-3 3"></path></svg>;
const IconMenu = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>;
const IconSair = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>;
// --- FIM DOS ÍCONES ---


function Sidebar({ handleLogout }) {
    const [isOpen, setIsOpen] = useState(true);

    // --- 3. ESTADOS para o Modal e nome do usuário ---
    const [showUsuarioModal, setShowUsuarioModal] = useState(false);
    const [nomeUsuario, setNomeUsuario] = useState('Usuário');

    // --- 4. Efeito para ler o nome do localStorage ---
    useEffect(() => {
        try {
            const usuarioJSON = localStorage.getItem('usuario');
            if (usuarioJSON) {
                const usuario = JSON.parse(usuarioJSON);
                setNomeUsuario(usuario.nome);
            }
        } catch (e) {
            console.error("Falha ao ler usuário do localStorage", e);
        }
    }, []); // Roda só uma vez, quando o sidebar carrega

    const toggleSidebar = () => {
        setIsOpen(!isOpen);
    };

    // --- 5. Handler para abrir o modal ---
    const handleProfileClick = () => {
        setShowUsuarioModal(true);
    };

    // --- 6. Handler para fechar o modal ---
    const handleModalClose = () => {
        setShowUsuarioModal(false);
        // Atualiza o nome na sidebar caso tenha sido alterado
        const usuarioJSON = localStorage.getItem('usuario');
        if (usuarioJSON) {
            const usuario = JSON.parse(usuarioJSON);
            setNomeUsuario(usuario.nome);
        }
    }

    return (
        // --- 7. Usa Fragment <> para envolver o modal e a sidebar ---
        <>
            <aside className={`sidebar ${!isOpen ? 'closed' : ''}`}>
                <div className="sidebar-header">
                    <h2 className="sidebar-title" style={{ display: isOpen ? 'block' : 'none' }}>
                        Aguapé
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
                    <NavLink to="/gestao" title="Gestão">
                        <IconGestao />
                        <span className="link-text">Gestão</span>
                    </NavLink>
                </nav>

                <div className="sidebar-footer">
                    {/* --- 8. Transforma o perfil em um botão clicável --- */}
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
                    {/* --- Fim da Mudança 8 --- */}

                    <button onClick={handleLogout} className="logout-btn" title="Sair">
                        <IconSair />
                        <span className="link-text" style={{ display: isOpen ? 'block' : 'none' }}>Sair</span>
                    </button>
                </div>
            </aside>

            {/* --- 9. Renderiza o Modal (ele fica oculto até 'showUsuarioModal' ser true) --- */}
            <UsuarioModal
                show={showUsuarioModal}
                handleClose={handleModalClose}
            />
        </>
    );
}

export default Sidebar;