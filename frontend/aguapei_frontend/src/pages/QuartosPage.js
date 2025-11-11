import React, { useState, useEffect, useCallback } from 'react';
import { fetchQuartos } from '../services/api'; 
import QuartoModal from '../components/QuartoModal';
// import MainLayout from '../layouts/MainLayout';
// import './QuartosPage.css';

const QuartosPage = () => {
    const [quartos, setQuartos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [showModal, setShowModal] = useState(false);
    const [quartoSelecionado, setQuartoSelecionado] = useState(null);

    const carregarQuartos = useCallback(async () => {
        try {
            setLoading(true);
            const response = await fetchQuartos();
            setQuartos(response.data);
            setError(null);
        } catch (err) {
            let errorMsg = 'Falha ao carregar a lista de quartos.';
            // Adiciona verificação de erro de token
            if (err.response && err.response.status === 401) {
                errorMsg = 'Sua sessão expirou. Faça login novamente.';
            }
            setError(errorMsg);
            console.error('Erro detalhado:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        carregarQuartos();
    }, [carregarQuartos]);

    // 3. ===============================================
    //    HANDLERS (Ações)
    //    ===============================================
    
    // Chamado pelo "+ Novo Quarto"
    const handleShowNovoQuarto = () => {
        setQuartoSelecionado(null);
        setShowModal(true);
    };

    // --- MUDANÇA 1: Descomentando a função ---
    // Chamado pelo botão "Editar"
    const handleShowEditarQuarto = (quarto) => {
        setQuartoSelecionado(quarto); // Passa o objeto 'quarto' para o modal
        setShowModal(true);           // Abre o modal em MODO EDIÇÃO
    };
    // --- Fim da Mudança 1 ---

    // Chamado pelo modal (onSaveSuccess)
    const handleSaveSuccess = () => {
        setShowModal(false);
        carregarQuartos(); // Recarrega a lista
    };

    // 4. Função de renderização de conteúdo
    const renderContent = () => {
        if (loading) return <div>Carregando quartos...</div>;
        if (error) return <div className="alert alert-danger">{error}</div>;
        if (quartos.length === 0 && !loading) return <div>Nenhum quarto cadastrado.</div>;

        return (
            <table className="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>Número / Nome</th>
                        <th>Tipo (Capacidade)</th>
                        <th>Valor da Diária</th>
                        <th>Status</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
                    {quartos.map(quarto => (
                        <tr key={quarto.id_quarto}>
                            <td>{quarto.numero}</td>
                            <td>{quarto.tipo_quarto}</td>
                            <td>
                                {new Intl.NumberFormat('pt-BR', { 
                                    style: 'currency', 
                                    currency: 'BRL' 
                                }).format(quarto.valor_diaria)}
                            </td>
                            <td>{quarto.status_quarto}</td> 
                            <td>
                                {/* --- MUDANÇA 2: Adicionando o onClick --- */}
                                <button 
                                    className="btn btn-sm btn-secondary"
                                    onClick={() => handleShowEditarQuarto(quarto)}
                                >
                                    Editar
                                </button>
                                {/* --- Fim da Mudança 2 --- */}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        );
    };

    // 5. Renderização principal
    return (
        // <MainLayout>
            <div className="quartos-page">
                <div className="page-header">
                    <h1>Gerenciamento de Quartos</h1>
                    <button 
                        className="btn btn-primary"
                        onClick={handleShowNovoQuarto}
                    >
                        + Novo Quarto
                    </button>
                </div>
                
                <div className="page-content">
                    {renderContent()}
                </div>

                <QuartoModal 
                    show={showModal}
                    handleClose={() => setShowModal(false)}
                    onSaveSuccess={handleSaveSuccess}
                    quarto={quartoSelecionado}
                />
            </div>
        // </MainLayout> 
    );
};

export default QuartosPage;