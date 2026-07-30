/**
 * ReservaConfirmModal.js
 * ----------------------
 * Modal intermediário usado pelo fluxo de criação/edição de reservas.
 * Exibe um resumo das informações antes de enviar o payload definitivo.
 */
import React from 'react';
import { Modal, Button, Spinner } from 'react-bootstrap';
import moment from 'moment';
import './ReservaConfirmModal.css';

// Helper para formatar a data (DD/MM/YYYY)
const formatData = (date) => {
    if (!date) return 'N/A';
    return moment(date).format('DD/MM/YYYY');
};

/**
 * Modal para confirmar os detalhes da reserva antes de salvar.
 */
function ReservaConfirmModal({ 
    show,           // boolean: se o modal está visível
    handleClose,    // função: para fechar (botão "Voltar")
    handleConfirm,  // função: para executar a ação (botão "Confirmar")
    loading,        // boolean: se está salvando (mostra spinner)
    confirmData     // objeto: { titularNome, quartoNome, checkin, checkout, status_pagamento }
}) {
    
    // Não renderiza nada se não tiver os dados
    if (!confirmData) return null; 

    return (
        // zIndex alto (1060) para sobrepor o modal de Nova Reserva
        <Modal show={show} onHide={handleClose} centered style={{ zIndex: 1060 }}>
            <Modal.Header closeButton>
                <Modal.Title style={{ color: '#26522c' }}>Confirmar Detalhes</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <p>Por favor, confirme os detalhes da reserva:</p>
                
                {/* O Sumário dos dados que você pediu */}
                <div className="resumo-reserva">
                    <div className="resumo-item">
                        <span>Titular:</span>
                        <strong>{confirmData.titularNome}</strong>
                    </div>
                    <div className="resumo-item">
                        <span>Quarto:</span>
                        <strong>{confirmData.quartoNome}</strong>
                    </div>
                    <div className="resumo-item">
                        <span>Check-in:</span>
                        <strong>{formatData(confirmData.checkin)}</strong>
                    </div>
                    <div className="resumo-item">
                        <span>Check-out:</span>
                        <strong>{formatData(confirmData.checkout)}</strong>
                    </div>
                    <div className="resumo-item">
                        <span>Barco:</span>
                        <strong>{confirmData.barcoNome || 'N/A'}</strong>
                    </div>
                    <div className="resumo-item">
                        <span>Passeio:</span>
                        <strong>{confirmData.tipoPasseioNome || 'N/A'}</strong>
                    </div>
                    <div className="resumo-item">
                        <span>Viagem:</span>
                        <strong>
                            {formatData(confirmData.data_embarque)} a {formatData(confirmData.data_desembarque)}
                            {confirmData.diasViagem ? ` (${confirmData.diasViagem} dias)` : ''}
                        </strong>
                    </div>
                    <div className="resumo-item">
                        <span>Status Pagamento:</span>
                        <strong className={`status-${confirmData.status_pagamento.toLowerCase()}`}>
                            {confirmData.status_pagamento}
                        </strong>
                    </div>
                </div>

            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleClose} disabled={loading}>
                    Voltar (Editar)
                </Button>
                <Button 
                    variant="success" 
                    onClick={handleConfirm} 
                    disabled={loading}
                    style={{ backgroundColor: '#26522c', borderColor: '#26522c' }}
                >
                    {loading ? <Spinner as="span" size="sm" /> : "Confirmar Reserva"}
                </Button>
            </Modal.Footer>
        </Modal>
    );
}

export default ReservaConfirmModal;
