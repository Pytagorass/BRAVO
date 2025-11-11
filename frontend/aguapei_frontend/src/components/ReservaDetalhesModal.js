// Em: frontend/src/components/ReservaDetalhesModal.js
// (Arquivo refatorado para incluir o botão "Editar" e "Pago Parcial")

import React, { useState, useEffect } from 'react';
import { Modal, Button, Spinner, Alert } from 'react-bootstrap';
import apiClient from '../services/api';
import './ReservaDetalhesModal.css';

// --- Funções Utilitárias (Corrigidas) ---

const formatCurrency = (value) => {
    const val = parseFloat(value);
    if (isNaN(val)) return "R$ 0,00";
    return val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
};

const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('pt-BR', { timeZone: 'UTC' });
};

const getStatusClass = (status) => {
    if (!status) return '';
    return 'status-' + status.toLowerCase().replace(' ', '-');
};

// --- Componente Principal Refatorado ---

// 🚀 PROP NOVA: onAbrirEditar
function ReservaDetalhesModal({ show, handleClose, reservaId, onUpdateSuccess, onAbrirEditar }) {
    const [reserva, setReserva] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [isUpdating, setIsUpdating] = useState(false);
    const [updateError, setUpdateError] = useState(null);

    // Efeito para BUSCAR os dados da reserva
    useEffect(() => {
        if (show && reservaId) {
            const fetchReservaDetalhes = async () => {
                setLoading(true);
                setError(null);
                setUpdateError(null);
                setReserva(null);
                try {
                    const response = await apiClient.get(`/agenda/detalhes/${reservaId}/`);
                    setReserva(response.data);
                } catch (err) {
                    setError('Falha ao carregar os detalhes da reserva.');
                    console.error("Erro ao buscar detalhes:", err);
                } finally {
                    setLoading(false);
                }
            };
            fetchReservaDetalhes();
        }
    }, [show, reservaId]);

    // Efeito para LIMPAR o estado
    useEffect(() => {
        if (!show) {
            setReserva(null);
            setError(null);
            setUpdateError(null);
            setLoading(false);
            setIsUpdating(false);
        }
    }, [show]);

    // Handler para Ações Rápidas (Pagar/Cancelar/Parcial)
    const handleUpdateStatus = async (statusType, newStatus) => {
        if (!reserva) return;
        setIsUpdating(true);
        setUpdateError(null);
        
        let payload = {};
        if (statusType === 'pagamento') {
            payload = { status_pagamento: newStatus };
        } else if (statusType === 'reserva') {
            payload = { status_reserva: newStatus };
        }

        try {
            const response = await apiClient.patch(
                `/agenda/update-status/${reserva.id_reserva_quarto}/`, 
                payload
            );
            setReserva(response.data);
            if (onUpdateSuccess) {
                onUpdateSuccess(response.data);
            }
            if (newStatus === 'Cancelada') {
                handleClose();
            }
        } catch (err) {
            setUpdateError('Falha ao atualizar o status.');
            console.error("Erro ao atualizar status:", err);
        } finally {
            setIsUpdating(false);
        }
    };

    // Handler para o botão "Editar"
    const handleAbrirModalEdicao = () => {
        if (onAbrirEditar) {
            onAbrirEditar(reserva); // Passa o objeto 'reserva' completo
        }
        handleClose(); // Fecha o modal de detalhes
    };


    // --- Helpers de Renderização ---
    const titularNome = reserva?.nome_titular || 'Hóspede';
    const quartoInfo = `${reserva?.numero_quarto || 'N/A'} (${reserva?.tipo_quarto || 'N/A'})`;
    const usuarioNome = reserva?.nome_usuario_criacao || 'Sistema';

    return (
        <Modal show={show} onHide={handleClose} size="lg" centered>
            <Modal.Header closeButton>
                <Modal.Title style={{ color: '#26522c' }}>
                    {loading ? 'Carregando Reserva...' : `Reserva #${reserva?.id_reserva || reservaId}`}
                </Modal.Title>
            </Modal.Header>
            
            <Modal.Body>
                {loading && (
                    <div className="text-center p-5">
                        <Spinner animation="border" variant="success" />
                        <p className="mt-2">Buscando detalhes...</p>
                    </div>
                )}
                {error && <Alert variant="danger">{error}</Alert>}
                {!loading && reserva && (
                    <>
                        {updateError && <Alert variant="warning">{updateError}</Alert>}

                        <h4 className="fw-bold" style={{ color: '#26522c' }}>
                            {quartoInfo} - {titularNome}
                        </h4>
                        <p className="text-muted mb-4">
                            Período: {formatDate(reserva.checkin)} a {formatDate(reserva.checkout)}
                        </p>
                        
                        <div className="detalhes-container">
                            {/* Coluna 1: Hóspedes */}
                            <div className="detalhes-coluna">
                                <h5>Hóspedes</h5>
                                <p>
                                    <strong>Titular:</strong> {titularNome}
                                    <br />
                                    <small className="text-muted">{reserva.email_titular || 'Sem email'}</small>
                                    <br />
                                    <small className="text-muted">{reserva.telefone_titular || 'Sem telefone'}</small>
                                </p>
                                
                                {reserva.acompanhantes?.length > 0 ? (
                                    reserva.acompanhantes.map(acomp => (
                                        <p key={acomp.id_hospede}>
                                            <strong>Acompanhante:</strong> {acomp.nome_hospede}
                                        </p>
                                    ))
                                ) : (
                                    <p><small className="text-muted">Sem acompanhantes registrados.</small></p>
                                )}
                                <hr className="d-md-none" />
                            </div>
                            
                            {/* Coluna 2: Financeiro */}
                            <div className="detalhes-coluna">
                                <h5>Resumo Financeiro</h5>
                                <p className="d-flex justify-content-between align-items-center">
                                    <span>Valor Total:</span>
                                    <span className="fw-bold fs-5 ms-2" style={{ color: '#26522c' }}>
                                        {formatCurrency(reserva.valor_total)}
                                    </span>
                                </p>
                                <p className="d-flex justify-content-between align-items-center">
                                    <span>Status Pagamento:</span>
                                    <span className={`fw-bold ms-2 ${getStatusClass(reserva.status_pagamento)}`}>
                                        {reserva.status_pagamento}
                                    </span>
                                </p>
                                <p className="d-flex justify-content-between align-items-center">
                                    <span>Status Reserva:</span>
                                    <span className={`fw-bold ms-2 ${getStatusClass(reserva.status_reserva)}`}>
                                        {reserva.status_reserva}
                                    </span>
                                </p>
                            </div>
                        </div>

                        <hr />
                        <h5>Observações</h5>
                        <p className="text-muted">
                            {reserva.observacao_reserva || 'Nenhuma observação.'}
                        </p>
                        <hr />
                        <small className="text-muted">
                            Reserva criada em {formatDate(reserva.dt_criacao)} por {usuarioNome}.
                            (Código da Reserva: {reserva.id_reserva})
                        </small>
                    </>
                )}
            </Modal.Body>

            {/* 🚀 RODAPÉ ATUALIZADO COM O BOTÃO "PAGO PARCIAL" */}
            <Modal.Footer>
                <Button 
                    variant="secondary" 
                    onClick={handleClose} 
                    disabled={isUpdating}
                >
                    Fechar
                </Button>

                {/* --- BOTÃO DE EDIÇÃO --- */}
                {!loading && reserva && reserva.status_reserva !== 'Cancelada' && (
                    <Button 
                        variant="primary" // Botão Azul
                        disabled={isUpdating}
                        onClick={handleAbrirModalEdicao}
                    >
                        Editar Reserva
                    </Button>
                )}

                {/* --- AÇÕES RÁPIDAS --- */}

                {/* 🚀 BOTÃO "PAGO PARCIAL" */}
                {/* Só aparece se a reserva for 'Pendente' e não 'Cancelada' */}
                {!loading && reserva && reserva.status_pagamento === 'Pendente' && reserva.status_reserva !== 'Cancelada' && (
                    <Button 
                        variant="info" // Cor Ciano/Azul
                        disabled={isUpdating}
                        onClick={() => handleUpdateStatus('pagamento', 'Em Partes')}
                    >
                        {isUpdating ? 
                            <Spinner as="span" animation="border" size="sm" /> 
                            : 'Pago Parcial'}
                    </Button>
                )}

                {/* Botão "Confirmar Pagamento" (Total) */}
                {/* Aparece se NÃO estiver 'Pago' e NÃO 'Cancelada' (ou seja, 'Pendente' ou 'Em partes') */}
                {!loading && reserva && reserva.status_pagamento !== 'Pago' && reserva.status_reserva !== 'Cancelada' && (
                    <Button 
                        variant="success" 
                        style={{ backgroundColor: '#26522c', border: 'none' }}
                        disabled={isUpdating}
                        onClick={() => handleUpdateStatus('pagamento', 'Pago')}
                    >
                        {isUpdating ? 
                            <Spinner as="span" animation="border" size="sm" /> 
                            : 'Confirmar Pagamento'}
                    </Button>
                )}
                
                {/* Botão "Cancelar Reserva" */}
                {!loading && reserva && reserva.status_reserva !== 'Cancelada' && (
                    <Button 
                        variant="danger" 
                        disabled={isUpdating}
                        onClick={() => handleUpdateStatus('reserva', 'Cancelada')}
                    >
                        {isUpdating ? 
                            <Spinner as="span" animation="border" size="sm" /> 
                            : 'Cancelar Reserva'}
                    </Button>
                )}
            </Modal.Footer>
        </Modal>
    );
}

export default ReservaDetalhesModal;