import React, { useState, useEffect, useCallback } from 'react';
import { fetchAgendaReservas, fetchQuartos } from '../services/api';
import GanttChart from '../components/GanttChart';
import NovaReservaModal from '../components/NovaReservaModal';
import ReservaDetalhesModal from '../components/ReservaDetalhesModal';
import { Spinner, Alert, Button } from 'react-bootstrap';
import moment from 'moment';
import 'moment/locale/pt-br';

moment.locale('pt-br');

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

    const handleTimeChange = (start, end) => {
        setVisibleTimeStart(start);
        setVisibleTimeEnd(end);
    };

    const handleAbrirModalCriacao = () => {
        setSelectedReservaId(null);
        setReservaParaEditar(null);
        setShowDetalhesModal(false);
        setShowReservaModal(true);
    };

    const handleItemClick = (itemId) => {
        if (!itemId) return;
        setReservaParaEditar(null);
        setSelectedReservaId(itemId);
        setShowReservaModal(false);
        setShowDetalhesModal(true);
    };

    const handleAbrirModalEdicao = (reserva) => {
        if (!reserva) return;
        setSelectedReservaId(null);
        setReservaParaEditar(reserva);
        setShowDetalhesModal(false);
        setShowReservaModal(true);
    };

    const handleCloseNovaReservaModal = () => {
        setShowReservaModal(false);
        setReservaParaEditar(null);
    };

    const handleCloseDetalhesModal = () => {
        setShowDetalhesModal(false);
        setSelectedReservaId(null);
    };

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
            <GanttChart
                quartosData={quartos}
                reservasData={reservas}
                visibleTimeStart={visibleTimeStart}
                visibleTimeEnd={visibleTimeEnd}
                onTimeChange={handleTimeChange}
                onItemClick={handleItemClick}
            />
        );
    };

    return (
        <div className="agenda-dashboard">
            <div className="page-header">
                <h1>Agenda Aguapé</h1>
                <Button
                    variant="primary"
                    onClick={handleAbrirModalCriacao}
                    style={{ backgroundColor: '#26522c', borderColor: '#26522c' }}
                >
                    + Nova Reserva
                </Button>
            </div>

            {renderContent()}

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
