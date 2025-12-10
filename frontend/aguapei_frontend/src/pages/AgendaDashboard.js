/**
 * AgendaDashboard.js
 * ------------------
 * Página principal de gestão de reservas. Lida com o carregamento da
 * timeline (quartos/reservas), controle das janelas de tempo e abertura
 * dos modais de criação/edição e detalhes.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { fetchAgendaReservas, fetchQuartos } from '../services/api';
import GanttChart from '../components/GanttChart';
import NovaReservaModal from '../components/NovaReservaModal';
import ReservaDetalhesModal from '../components/ReservaDetalhesModal';
import { Spinner, Alert, Button } from 'react-bootstrap';
import moment from 'moment';
import 'moment/locale/pt-br';
import LegendaGantt from '../components/LegendaGantt';
import { HelpCircle } from 'react-feather';

moment.locale('pt-br');

/**
 * Controle principal da Agenda. Mantém os estados relacionados ao Gantt,
 * incluindo dados das reservas/quartos e visibilidade dos modais auxiliares.
 */
/**
 * AgendaDashboard
 * ---------------
 * Página que controla a visualização da agenda (Gantt) e os modais relacionados.
 * Impacta o backend ao chamar `fetchQuartos` e `fetchAgendaReservas`; demais ações
 * são manipulações locais de estado + acionamento dos modais.
 */
const AgendaDashboard = () => {
    const [quartos, setQuartos] = useState([]);
    const [reservas, setReservas] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [visibleTimeStart, setVisibleTimeStart] = useState(moment().startOf('month').valueOf());
    const [visibleTimeEnd, setVisibleTimeEnd] = useState(moment().endOf('month').valueOf());
    const [showReservaModal, setShowReservaModal] = useState(false);
    const [showDetalhesModal, setShowDetalhesModal] = useState(false);
    const [selectedReservaId, setSelectedReservaId] = useState(null);
    const [reservaParaEditar, setReservaParaEditar] = useState(null);
    const [showLegenda, setShowLegenda] = useState(false);

    /**
     * Busca os dados necessários para montar o Gantt (quartos + reservas) em paralelo.
     * Em caso de erro, atualiza o alerta exibido na interface. Não retorna valores.
     */
    const carregarDadosGantt = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const [quartosResponse, reservasResponse] = await Promise.all([
                fetchQuartos(),
                fetchAgendaReservas(),
            ]);
            setQuartos(quartosResponse);
            setReservas(reservasResponse);
        } catch (err) {
            console.error('Falha ao carregar dados:', err);
            let errorMsg = err.message || 'Falha ao carregar dados da agenda.';
            if (err.code === 'INVALID_TOKEN' || err.status === 401) {
                errorMsg = 'Sua sessão expirou. Faça login novamente.';
            }
            setError(errorMsg);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        carregarDadosGantt();
    }, [carregarDadosGantt]);

    /**
     * Atualiza as janelas visíveis no timeline conforme o usuário navega.
     *
     * @param {number} start - timestamp inicial em milissegundos.
     * @param {number} end - timestamp final em milissegundos.
     */
    const handleTimeChange = (start, end) => {
        setVisibleTimeStart(start);
        setVisibleTimeEnd(end);
    };

    /**
     * Abre o modal de criação de reserva.
     * Reseta qualquer seleção anterior para garantir que o formulário esteja limpo.
     */
    const handleAbrirModalCriacao = () => {
        setSelectedReservaId(null);
        setReservaParaEditar(null);
        setShowDetalhesModal(false);
        setShowReservaModal(true);
    };

    /**
     * Handler do clique em um item do Gantt.
     * Recebe `itemId` (id_reserva_quarto) e abre o modal de detalhes.
     */
    const handleItemClick = (itemId) => {
        if (!itemId) return;
        setReservaParaEditar(null);
        setSelectedReservaId(itemId);
        setShowReservaModal(false);
        setShowDetalhesModal(true);
    };

    /**
     * Abre o modal de edição a partir do modal de detalhes.
     * Mantém o objeto completo da reserva para pré-preencher o formulário.
     */
    const handleAbrirModalEdicao = (reserva) => {
        if (!reserva) return;
        setSelectedReservaId(null);
        setReservaParaEditar(reserva);
        setShowDetalhesModal(false);
        setShowReservaModal(true);
    };

    // Fecha o modal de nova reserva e limpa a reserva em edição, se houver.
    const handleCloseNovaReservaModal = () => {
        setShowReservaModal(false);
        setReservaParaEditar(null);
    };

    // Fecha o modal de detalhes e reseta o id selecionado.
    const handleCloseDetalhesModal = () => {
        setShowDetalhesModal(false);
        setSelectedReservaId(null);
    };

    /**
     * Callback chamado após criar/editar uma reserva.
     * Atualiza o estado local para refletir o resultado retornado pelo backend.
     *
     * @param {object} reservaAtualizadaObj - reserva retornada pela API após a operação.
     */
    const handleReservaUpdateSuccess = (reservaAtualizadaObj) => {
        const reservaExiste = reservas.some(
            (r) => r.id_reserva_quarto === reservaAtualizadaObj.id_reserva_quarto
        );

        if (reservaExiste) {
            setReservas((prevReservas) =>
                prevReservas.map((reserva) =>
                    reserva.id_reserva_quarto === reservaAtualizadaObj.id_reserva_quarto
                        ? reservaAtualizadaObj
                        : reserva
                )
            );
        } else {
            setReservas((prevReservas) => [...prevReservas, reservaAtualizadaObj]);
        }

        setShowReservaModal(false);
        setShowDetalhesModal(false);
        setReservaParaEditar(null);
        setSelectedReservaId(null);
    };



    /**
     * Responsável por renderizar o conteúdo (loading, erro, Gantt + legenda).
     * Não realiza chamadas ao backend; usa apenas os estados já carregados.
     */
    const renderContent = () => {
        if (loading) {
            return (
                <div className="d-flex justify-content-center align-items-center" style={{ height: '300px' }}>
                    <Spinner animation="border" role="status">
                        <span className="visually-hidden">Carregando agenda...</span>
                    </Spinner>
                </div>
            );
        }

        if (error) {
            return (
                <Alert variant="danger">
                    <Alert.Heading>Erro ao Carregar Dados</Alert.Heading>
                    <p>{error}</p>
                    <Button onClick={carregarDadosGantt} variant="danger">
                        Tentar Novamente
                    </Button>
                </Alert>
            );
        }

        return (
            <div style={{ position: 'relative' }}>
                <GanttChart
                    quartosData={quartos}
                    reservasData={reservas}
                    visibleTimeStart={visibleTimeStart}
                    visibleTimeEnd={visibleTimeEnd}
                    onTimeChange={handleTimeChange}
                    onItemClick={handleItemClick}
                />
                {showLegenda && <LegendaGantt />}
            </div>
        );
    };

    return (
        <div className="agenda-dashboard">
            <div className="page-header d-flex justify-content-between align-items-center">
                <h1>Agenda Aguapé</h1>
            </div>
            <div className="page-actions mb-3">
                <Button
                    variant="outline-secondary"
                    className="me-2"
                    onClick={() => setShowLegenda(!showLegenda)}
                    title={showLegenda ? 'Esconder Legenda' : 'Mostrar Legenda'}
                >
                    <HelpCircle size={16} className="me-1" />
                    {showLegenda ? 'Esconder' : 'Ver'} Legenda
                </Button>

                <Button
                    variant="primary"
                    onClick={handleAbrirModalCriacao}
                    style={{ backgroundColor: '#26522c', borderColor: '#26522c' }}
                >
                    + Nova Reserva
                </Button>
            </div>

            <div className="page-content">{renderContent()}</div>

            {showReservaModal && (
                <NovaReservaModal
                    show={showReservaModal}
                    handleClose={handleCloseNovaReservaModal}
                    onSaveSuccess={handleReservaUpdateSuccess}
                    reservaParaEditar={reservaParaEditar}
                />
            )}

            {showDetalhesModal && (
                <ReservaDetalhesModal
                    show={showDetalhesModal}
                    handleClose={handleCloseDetalhesModal}
                    reservaId={selectedReservaId}
                    onUpdateSuccess={handleReservaUpdateSuccess}
                    onAbrirEditar={handleAbrirModalEdicao}
                />
            )}
        </div>
    );
};

export default AgendaDashboard;
