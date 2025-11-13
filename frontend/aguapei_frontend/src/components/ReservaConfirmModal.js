import React from 'react';
import { Modal, Button, Spinner } from 'react-bootstrap';
import moment from 'moment';
// Importe o CSS que vamos criar no próximo passo
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
    confirmData     // objeto: { titularNome, quartoNome, checkin, checkout, forma_pagamento }
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
                        <span>Status Pagamento:</span>
                        {/* Adiciona classes de cor com base no status 
                          (ex: 'status-pendente' será amarelo) 
                        */}
                        <strong className={`status-${confirmData.forma_pagamento.toLowerCase()}`}>
                            {confirmData.forma_pagamento}
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