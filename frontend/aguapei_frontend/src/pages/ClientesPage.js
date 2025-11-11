import React, { useState, useEffect, useCallback } from 'react';
import { fetchHospedes } from '../services/api'; 
import ClienteModal from '../components/ClienteModal'; 

import './ClientesPage.css';

const ClientesPage = () => {
    const [clientes, setClientes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // ===============================================
    // LÓGICA DE CONTROLE DO MODAL
    // ===============================================
    const [showModal, setShowModal] = useState(false);
    const [clienteSelecionado, setClienteSelecionado] = useState(null); 

    // 1. ===============================================
    //    FUNÇÃO DE CARREGAR DADOS
    //    ===============================================
    const carregarClientes = useCallback(async () => {
        try {
            setLoading(true);
            const response = await fetchHospedes();
            setClientes(response.data);
            setError(null);
        } catch (err) {
            let errorMsg = 'Falha ao carregar a lista de clientes.';
            if (err.response && err.response.status === 401) {
                errorMsg = 'Sua sessão expirou. Faça login novamente.';
                // (Aqui você pode adicionar a lógica de deslogar o usuário)
            }
            setError(errorMsg);
            console.error('Erro detalhado:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    // 2. Hook de carregamento
    useEffect(() => {
        carregarClientes();
    }, [carregarClientes]);

    // 3. ===============================================
    //    HANDLERS (Ações)
    //    ===============================================
    
    // Chamado pelo "+ Novo Cliente"
    const handleShowNovoCliente = () => {
        setClienteSelecionado(null); // 'null' diz ao modal que é MODO CRIAÇÃO
        setShowModal(true);
    };

    // --- MUDANÇA 1: NOVA FUNÇÃO ---
    // Chamado pelo botão "Editar"
    const handleShowEditarCliente = (cliente) => {
        setClienteSelecionado(cliente); // Passa o objeto 'cliente' para o modal
        setShowModal(true);             // Abre o modal em MODO EDIÇÃO
    };
    // --- Fim da Mudança 1 ---

    // Chamado pelo modal (onSaveSuccess)
    const handleSaveSuccess = () => {
        setShowModal(false);
        carregarClientes(); // RECARREGA a lista (seja 'novo' ou 'edição')
    };

    // 4. ===============================================
    //    FUNÇÃO DE RENDERIZAÇÃO DE CONTEÚDO
    //    --- MUDANÇA 2: CORREÇÃO DA TABELA ---
    //    ===============================================
    const renderContent = () => {
        if (loading) return <div>Carregando clientes...</div>;
        if (error) return <div className="alert alert-danger">{error}</div>;
        if (clientes.length === 0 && !loading) return <div>Nenhum cliente cadastrado.</div>;

        return (
            <table className="table table-striped table-hover">
                {/* CORREÇÃO 2A: Descomentando o cabeçalho */}
                <thead className="thead-dark">
                    <tr>
                        <th>Nome</th>
                        <th>E-mail</th>
                        <th>Telefone</th>
                        <th>País</th>
                        <th>Documento (CPF/Passaporte)</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                
                {/* CORREÇÃO 2B: Descomentando o corpo e o botão */}
                <tbody>
                    {clientes.map(cliente => (
                        <tr key={cliente.id_hospede}>
                            <td>{cliente.nome_hospede}</td>
                            <td>{cliente.email_hospede}</td>
                            <td>{cliente.telefone}</td>
                            <td>{cliente.pais_origem}</td>
                            <td>
                                {cliente.pais_origem === 'Brasil' ? cliente.cpf : cliente.passaporte}
                            </td>
                            <td>
                                <button 
                                    className="btn btn-sm btn-secondary"
                                    // MUDANÇA 3: Ligando o onClick ao handler
                                    onClick={() => handleShowEditarCliente(cliente)}
                                >
                                    Editar
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        );
    };

    // 5. Renderização principal (sem mudanças)
    return (
        // <MainLayout>
            <div className="clientes-page">
                <div className="page-header">
                    <h1>Gerenciamento de Clientes</h1>
                    <button 
                        className="btn btn-primary"
                        onClick={handleShowNovoCliente}
                    >
                        + Novo Cliente
                    </button>
                </div>
                
                <div className="page-content">
                    {renderContent()}
                </div>

                <ClienteModal 
                    show={showModal}
                    handleClose={() => setShowModal(false)}
                    onSaveSuccess={handleSaveSuccess}
                    cliente={clienteSelecionado} // Passa 'null' (novo) ou o 'cliente' (editar)
                />
            </div>
        // </MainLayout> 
    );
};

export default ClientesPage;