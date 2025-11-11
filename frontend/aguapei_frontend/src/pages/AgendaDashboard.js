import React, { useState, useEffect, useCallback } from 'react';
import { fetchAgendaReservas, fetchQuartos } from '../services/api';

// Importa os componentes
import GanttChart from '../components/GanttChart';
import NovaReservaModal from '../components/NovaReservaModal';
import ReservaDetalhesModal from '../components/ReservaDetalhesModal';

// Importa o CSS e o Moment.js
import './AgendaDashboard.css';
import moment from 'moment';
import 'moment/locale/pt-br';
moment.locale('pt-br');

const AgendaDashboard = () => {
    // Estados de dados
    const [quartos, setQuartos] = useState([]);
    const [reservas, setReservas] = useState([]);
    
    // Estados de UI
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [visibleTimeStart, setVisibleTimeStart] = useState(moment().startOf('month').valueOf());
    const [visibleTimeEnd, setVisibleTimeEnd] = useState(moment().endOf('month').valueOf());

    // --- ESTADOS DE CONTROLE DOS MODAIS ---
    // (Inicializados explicitamente como 'false' e 'null')
    const [showReservaModal, setShowReservaModal] = useState(false);
    const [showDetalhesModal, setShowDetalhesModal] = useState(false);
    const [selectedReservaId, setSelectedReservaId] = useState(null);
    const [reservaParaEditar, setReservaParaEditar] = useState(null);


    // (Funções de carregar dados e time change - sem mudanças)
    const carregarDadosGantt = useCallback(async () => {
        try {
            setLoading(true);
            const [quartosResponse, reservasResponse] = await Promise.all([
                fetchQuartos(),
                fetchAgendaReservas()
            ]);
            setQuartos(quartosResponse.data);
            setReservas(reservasResponse.data); 
            setError(null);
        } catch (err) {
            let errorMsg = 'Falha ao carregar dados da agenda.';
            if (err.response && err.response.status === 401) {
                errorMsg = 'Sua sessão expirou. Faça login novamente.';
            }
            setError(errorMsg);
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        carregarDadosGantt();
    }, [carregarDadosGantt]);

    const handleTimeChange = (start, end, updateScroll) => {
        setVisibleTimeStart(start);
        setVisibleTimeEnd(end);
        updateScroll(start, end);
    };

    // --- 🚀 HANDLERS COM LÓGICA DE ESTADO EXPLÍCITA ---

    /**
     * Chamado quando o usuário clica em "+ Nova Reserva".
     * Força o estado para "Modo de Criação".
     */
    // const handleAbrirModalCriacao = () => {
    //     setSelectedReservaId(null);   // 🚀 CORREÇÃO EXPLÍCITA
    //     setReservaParaEditar(null);   // 🚀 CORREÇÃO EXPLÍCITA
    //     setShowDetalhesModal(false);  // 🚀 CORREÇÃO EXPLÍCITA
    //     setShowReservaModal(true);    // Abre o modal de formulário
    // };
const handleAbrirModalCriacao = () => {
    // 1. Limpa qualquer seleção anterior (que causa o "undefined")
    setSelectedReservaId(null);   
    setReservaParaEditar(null);   

    // 2. FORÇA o fechamento do modal de Detalhes
    setShowDetalhesModal(false);  

    // 3. ABRE o modal de Formulário (o correto)
    setShowReservaModal(true);    
};
    /**
     * Chamado quando o usuário clica em uma barra de reserva no Gantt.
     * Força o estado para "Modo de Detalhes".
     */
    const handleItemClick = (itemId, e) => {
        console.log("handleItemClick [DEBUG]:", { itemId, e });
        
        if (!itemId || (typeof itemId !== 'number' && typeof itemId !== 'string')) {
             console.error("handleItemClick [ERRO]: O ID da reserva não foi recebido.");
             return; 
        }
        
        setReservaParaEditar(null);     // 🚀 CORREÇÃO EXPLÍCITA
        setSelectedReservaId(itemId);   // Define o ID
        setShowReservaModal(false);     // 🚀 CORREÇÃO EXPLÍCITA
        setShowDetalhesModal(true);     // Abre o modal de detalhes
    };

    /**
     * Chamado pelo 'ReservaDetalhesModal' quando o botão "Editar Reserva" é clicado.
     * Força o estado para "Modo de Edição".
     */
    const handleAbrirModalEdicao = (reserva) => {
        if (!reserva) return;
        setSelectedReservaId(null);       // 🚀 CORREÇÃO EXPLÍCITA
        setReservaParaEditar(reserva);    // Define o objeto
        setShowDetalhesModal(false);    // Fecha o modal de detalhes
        setShowReservaModal(true);      // Abre o modal de formulário
    };

    /**
     * Chamado quando o 'NovaReservaModal' (Formulário) fecha.
     */
    const handleCloseNovaReservaModal = () => {
        setShowReservaModal(false);
        setReservaParaEditar(null); // Limpa o estado de edição
    };

    /**
     * Chamado quando o 'ReservaDetalhesModal' (Detalhes) fecha.
     */
    const handleCloseDetalhesModal = () => {
        setShowDetalhesModal(false);
        setSelectedReservaId(null); // Limpa o ID selecionado
    };

    /**
     * Função unificada de Sucesso (para Criar, Editar e Ações Rápidas)
     */
    const handleReservaUpdateSuccess = (reservaAtualizadaObj) => {
        const reservaExiste = reservas.some(
            r => r.id_reserva_quarto === reservaAtualizadaObj.id_reserva_quarto
        );

        if (reservaExiste) {
            // --- MODO EDIÇÃO / AÇÃO RÁPIDA ---
            setReservas(prevReservas => 
                prevReservas.map(reserva => 
                    reserva.id_reserva_quarto === reservaAtualizadaObj.id_reserva_quarto 
                    ? reservaAtualizadaObj
                    : reserva 
                )
            );
        } else {
            // --- MODO CRIAÇÃO ---
            setReservas(prevReservas => [...prevReservas, reservaAtualizadaObj]);
        }
        
        // Garante que TODOS os modais fechem
        setShowReservaModal(false);
        setShowDetalhesModal(false);
        // Limpa os estados
        setReservaParaEditar(null);
        setSelectedReservaId(null);
    };


    // 5. Renderização
    if (loading) {
        return <div>Carregando agenda...</div>;
    }

    return (
        <div className="agenda-dashboard">
            <div className="page-header">
                <h1>Agenda Aguapé</h1>
                <button 
                    className="btn btn-primary"
                    onClick={handleAbrirModalCriacao}
                >
                    + Nova Reserva
                </button>
            </div>
            
            {error && <div className="alert alert-danger">{error}</div>}

            <GanttChart 
                quartos={quartos}
                reservas={reservas}
                visibleTimeStart={visibleTimeStart}
                visibleTimeEnd={visibleTimeEnd}
                onTimeChange={handleTimeChange}
                onItemClick={handleItemClick}
            />

            <NovaReservaModal 
                show={showReservaModal}
                handleClose={handleCloseNovaReservaModal}
                onSaveSuccess={handleReservaUpdateSuccess}
                reservaParaEditar={reservaParaEditar}
            />

            <ReservaDetalhesModal
                show={showDetalhesModal}
                handleClose={handleCloseDetalhesModal} // 🚀 CORREÇÃO: Usa o handler correto
                reservaId={selectedReservaId}
                onUpdateSuccess={handleReservaUpdateSuccess}
                onAbrirEditar={handleAbrirModalEdicao}
            />
        </div>
    );
};

export default AgendaDashboard;