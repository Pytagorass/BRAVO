// /frontend/src/components/ConfirmacaoModal.js
import React from 'react';
import { Modal, Button, Spinner } from 'react-bootstrap';

/**
 * Um modal de confirmação genérico e reutilizável.
 * @param {boolean} show - Controla a exibição.
 * @param {function} handleClose - Função para fechar o modal (botão "Voltar").
 * @param {function} handleConfirm - Função a ser executada ao confirmar.
 * @param {string} title - O título do modal (ex: "Atenção").
 * @param {string} body - O texto do corpo (ex: "Tem certeza?").
 * @param {string} [confirmVariant="danger"] - A cor do botão de confirmação.
 * @param {string} [confirmText="Confirmar"] - O texto do botão de confirmação.
 * @param {boolean} [loading=false] - Se deve mostrar spinner de carregamento.
 */
function ConfirmacaoModal({
  show,
  handleClose,
  handleConfirm,
  title,
  body,
  confirmVariant = "danger",
  confirmText = "Confirmar",
  loading = false
}) {
  return (
    <Modal show={show} onHide={handleClose} centered style={{ zIndex: 1060 }}>
      <Modal.Header closeButton>
        <Modal.Title>{title}</Modal.Title>
      </Modal.Header>
      <Modal.Body>{body}</Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={handleClose} disabled={loading}>
          Voltar
        </Button>
        <Button variant={confirmVariant} onClick={handleConfirm} disabled={loading}>
          {loading ? <Spinner as="span" size="sm" /> : confirmText}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}

export default ConfirmacaoModal;
