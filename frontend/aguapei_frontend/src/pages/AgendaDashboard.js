/**
 * AgendaDashboard.js
 * ------------------
 * Página principal de gestão de reservas. Lida com o carregamento da
 * timeline (quartos/reservas), controle das janelas de tempo e abertura
 * dos modais de criação/edição e detalhes.
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { fetchAgendaReservas, fetchQuartos } from '../services/api';
import GanttChart from '../components/GanttChart';
import NovaReservaModal from '../components/NovaReservaModal';
import ReservaDetalhesModal from '../components/ReservaDetalhesModal';
import { Spinner, Alert, Button } from 'react-bootstrap';
import moment from 'moment';
import 'moment/locale/pt-br';
import LegendaGantt from '../components/LegendaGantt';
import { ChevronLeft, ChevronRight, HelpCircle, Plus } from 'react-feather';
import './AgendaDashboard.css';

moment.locale('pt-br');

const FILTROS_RESERVA = [
    { id: 'todas', label: 'Todas' },
    { id: 'pendentes', label: 'Pendentes' },
    { id: 'pagas', label: 'Pagas' },
    { id: 'em-partes', label: 'Em partes' },
    { id: 'ativas', label: 'Ativas' },
    { id: 'canceladas', label: 'Canceladas' },
];

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
    const [filtroReserva, setFiltroReserva] = useState('todas');

    const reservasFiltradas = useMemo(() => {
        switch (filtroReserva) {
            case 'pendentes':
                return reservas.filter((reserva) => reserva.status_pagamento === 'Pendente');
            case 'pagas':
                return reservas.filter((reserva) => reserva.status_pagamento === 'Pago');
            case 'em-partes':
                return reservas.filter((reserva) => reserva.status_pagamento === 'Em Partes');
            case 'ativas':
                return reservas.filter((reserva) => reserva.status_reserva === 'Ativa');
            case 'canceladas':
                return reservas.filter((reserva) => reserva.status_reserva === 'Cancelada');
            default:
                return reservas;
        }
    }, [reservas, filtroReserva]);

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
    const handleTimeChange = (start, end, updateScrollCanvas) => {
        if (typeof updateScrollCanvas === 'function') {
            updateScrollCanvas(start, end);
        }
        setVisibleTimeStart(start);
        setVisibleTimeEnd(end);
    };

    const handleChangeMonth = (monthMoment) => {
        setVisibleTimeStart(monthMoment.clone().startOf('month').valueOf());
        setVisibleTimeEnd(monthMoment.clone().endOf('month').valueOf());
    };

    const handlePreviousMonth = () => {
        handleChangeMonth(moment(visibleTimeStart).subtract(1, 'month'));
    };

    const handleCurrentMonth = () => {
        handleChangeMonth(moment());
    };

    const handleNextMonth = () => {
        handleChangeMonth(moment(visibleTimeStart).add(1, 'month'));
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
            <div className="agenda-timeline-shell">
                {showLegenda && <LegendaGantt />}
                <GanttChart
                    quartosData={quartos}
                    reservasData={reservasFiltradas}
                    visibleTimeStart={visibleTimeStart}
                    visibleTimeEnd={visibleTimeEnd}
                    onTimeChange={handleTimeChange}
                    onItemClick={handleItemClick}
                />
            </div>
        );
    };

    const periodoAtual = moment(visibleTimeStart).format('MMMM [de] YYYY');
    const totalReservasLabel = reservasFiltradas.length === reservas.length
        ? `${reservas.length} reservas`
        : `${reservasFiltradas.length}/${reservas.length} reservas`;

    return (
        <div className="agenda-dashboard">
            <div className="page-header">
                <div className="agenda-title-block">
                <h1>Agenda Aguapé</h1>
                    <span className="agenda-title-meta">{periodoAtual}</span>
                </div>
            </div>
            <div className="agenda-toolbar">
                <div className="agenda-actions">
                    <div className="agenda-month-nav" aria-label="Navegacao do calendario">
                        <Button
                            variant="outline-secondary"
                            className="agenda-icon-action"
                            onClick={handlePreviousMonth}
                            title="Mes anterior"
                        >
                            <ChevronLeft size={16} />
                        </Button>
                        <Button
                            variant="outline-secondary"
                            className="agenda-secondary-action"
                            onClick={handleCurrentMonth}
                        >
                            Hoje
                        </Button>
                        <Button
                            variant="outline-secondary"
                            className="agenda-icon-action"
                            onClick={handleNextMonth}
                            title="Proximo mes"
                        >
                            <ChevronRight size={16} />
                        </Button>
                    </div>

                    <Button
                        variant="outline-secondary"
                        className="agenda-secondary-action"
                        onClick={() => setShowLegenda(!showLegenda)}
                        title={showLegenda ? 'Esconder Legenda' : 'Mostrar Legenda'}
                    >
                        <HelpCircle size={16} />
                        {showLegenda ? 'Esconder' : 'Ver'} Legenda
                    </Button>

                    <Button
                        variant="primary"
                        className="agenda-primary-action"
                        onClick={handleAbrirModalCriacao}
                    >
                        <Plus size={16} />
                        Nova Reserva
                    </Button>
                </div>
                <div className="agenda-period-summary">
                    <span className="agenda-chip">{quartos.length} quartos</span>
                    <span className="agenda-chip">{totalReservasLabel}</span>
                </div>
            </div>
            <div className="agenda-filter-bar" aria-label="Filtros de reservas">
                {FILTROS_RESERVA.map((filtro) => (
                    <button
                        key={filtro.id}
                        type="button"
                        className={`agenda-filter-chip ${filtroReserva === filtro.id ? 'active' : ''}`}
                        onClick={() => setFiltroReserva(filtro.id)}
                    >
                        {filtro.label}
                    </button>
                ))}
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
