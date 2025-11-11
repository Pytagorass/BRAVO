// frontend/src/components/ReservaDetalhesModal.js
import React, { useState, useEffect } from 'react';
import { Modal, Button, Spinner, Alert } from 'react-bootstrap';
import { fetchReservaDetalhes, updateReservaStatus } from '../services/api';
import { toast } from 'react-toastify';
import ConfirmacaoModal from './ConfirmacaoModal';
import './ReservaDetalhesModal.css';

const formatCurrency = (value) => {
  const val = parseFloat(value);
  if (isNaN(val)) return 'R$ 0,00';
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

function ReservaDetalhesModal({
  show,
  handleClose,
  reservaId,
  onUpdateSuccess,
  onAbrirEditar,
}) {
  const [reserva, setReserva] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateError, setUpdateError] = useState(null);
  const [showConfirmCancel, setShowConfirmCancel] = useState(false);

  useEffect(() => {
    if (show && reservaId) {
      const fetchReserva = async () => {
        setLoading(true);
        setError(null);
        setUpdateError(null);
        setReserva(null);
        try {
          const responseData = await fetchReservaDetalhes(reservaId);
          setReserva(responseData);
        } catch (err) {
          setError(err.message || 'Falha ao carregar os detalhes da reserva.');
          console.error('Erro ao buscar detalhes:', err);
        } finally {
          setLoading(false);
        }
      };
      fetchReserva();
    }
  }, [show, reservaId]);

  useEffect(() => {
    if (!show) {
      setReserva(null);
      setError(null);
      setUpdateError(null);
      setLoading(false);
      setIsUpdating(false);
      setShowConfirmCancel(false);
    }
  }, [show]);

  const handleUpdatePagamento = async (newStatus) => {
    if (!reserva) return;
    setIsUpdating(true);
    setUpdateError(null);

    const payload = { status_pagamento: newStatus };

    try {
      const responseData = await updateReservaStatus(
        reserva.id_reserva_quarto,
        payload
      );
      setReserva(responseData);
      toast.success(`Status de pagamento atualizado para "${newStatus}"!`);
      if (onUpdateSuccess) {
        onUpdateSuccess(responseData);
      }
    } catch (err) {
      const errorMsg = err.message || 'Falha ao atualizar o status.';
      setUpdateError(errorMsg);
      toast.error(errorMsg);
      console.error('Erro ao atualizar status:', err);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleCancelClick = () => {
    setShowConfirmCancel(true);
  };

  const handleConfirmCancelamento = async () => {
    if (!reserva) return;
    setIsUpdating(true);
    setUpdateError(null);

    const payload = { status_reserva: 'Cancelada' };

    try {
      const responseData = await updateReservaStatus(
        reserva.id_reserva_quarto,
        payload
      );

      toast.success('Reserva cancelada com sucesso!');

      if (onUpdateSuccess) {
        onUpdateSuccess(responseData);
      }
      setShowConfirmCancel(false);
      handleClose();
    } catch (err) {
      const errorMsg = err.message || 'Falha ao cancelar a reserva.';
      setUpdateError(errorMsg);
      toast.error(errorMsg);
      setShowConfirmCancel(false);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleAbrirModalEdicao = () => {
    if (onAbrirEditar) {
      onAbrirEditar(reserva);
    }
    handleClose();
  };

  const titularNome = reserva?.nome_titular || 'Hóspede';
  const quartoInfo = `${reserva?.numero_quarto || 'N/A'} (${
    reserva?.tipo_quarto || 'N/A'
  })`;
  const usuarioNome = reserva?.nome_usuario_criacao || 'Sistema';

  return (
    <>
      <Modal show={show} onHide={handleClose} size="lg" centered>
        <Modal.Header closeButton>
          <Modal.Title style={{ color: '#26522c' }}>
            {loading
              ? 'Carregando Reserva...'
              : `Reserva #${reserva?.id_reserva || reservaId}`}
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
                Período: {formatDate(reserva.checkin)} a{' '}
                {formatDate(reserva.checkout)}
              </p>

              <div className="detalhes-container">
                <div className="detalhes-coluna">
                  <h5>Hóspedes</h5>
                  <p>
                    <strong>Titular:</strong> {titularNome}
                    <br />
                    <small className="text-muted">
                      {reserva.email_titular || 'Sem email'}
                    </small>
                    <br />
                    <small className="text-muted">
                      {reserva.telefone_titular || 'Sem telefone'}
                    </small>
                  </p>

                  {reserva.acompanhantes?.length > 0 ? (
                    reserva.acompanhantes.map((acomp) => (
                      <p key={acomp.id_hospede}>
                        <strong>Acompanhante:</strong> {acomp.nome_hospede}
                      </p>
                    ))
                  ) : (
                    <p>
                      <small className="text-muted">
                        Sem acompanhantes registrados.
                      </small>
                    </p>
                  )}
                  <hr className="d-md-none" />
                </div>

                <div className="detalhes-coluna">
                  <h5>Resumo Financeiro</h5>
                  <p className="d-flex justify-content-between align-items-center">
                    <span>Valor Total:</span>
                    <span
                      className="fw-bold fs-5 ms-2"
                      style={{ color: '#26522c' }}
                    >
                      {formatCurrency(reserva.valor_total)}
                    </span>
                  </p>
                  <p className="d-flex justify-content-between align-items-center">
                    <span>Status Pagamento:</span>
                    <span
                      className={`fw-bold ms-2 ${getStatusClass(
                        reserva.status_pagamento
                      )}`}
                    >
                      {reserva.status_pagamento}
                    </span>
                  </p>
                  <p className="d-flex justify-content-between align-items-center">
                    <span>Status Reserva:</span>
                    <span
                      className={`fw-bold ms-2 ${getStatusClass(
                        reserva.status_reserva
                      )}`}
                    >
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
                Reserva criada em {formatDate(reserva.dt_criacao)} por{' '}
                {usuarioNome}. (Código da Reserva: {reserva.id_reserva})
              </small>
            </>
          )}
        </Modal.Body>

        <Modal.Footer>
          <Button
            variant="secondary"
            onClick={handleClose}
            disabled={isUpdating}
          >
            Fechar
          </Button>

          {!loading && reserva && reserva.status_reserva !== 'Cancelada' && (
            <Button
              variant="primary"
              disabled={isUpdating}
              onClick={handleAbrirModalEdicao}
            >
              Editar Reserva
            </Button>
          )}

          {!loading &&
            reserva &&
            reserva.status_pagamento === 'Pendente' &&
            reserva.status_reserva !== 'Cancelada' && (
              <Button
                variant="info"
                disabled={isUpdating}
                onClick={() => handleUpdatePagamento('Em Partes')}
              >
                {isUpdating ? (
                  <Spinner as="span" animation="border" size="sm" />
                ) : (
                  'Pago Parcial'
                )}
              </Button>
            )}

          {!loading &&
            reserva &&
            reserva.status_pagamento !== 'Pago' &&
            reserva.status_reserva !== 'Cancelada' && (
              <Button
                variant="success"
                style={{ backgroundColor: '#26522c', border: 'none' }}
                disabled={isUpdating}
                onClick={() => handleUpdatePagamento('Pago')}
              >
                {isUpdating ? (
                  <Spinner as="span" animation="border" size="sm" />
                ) : (
                  'Confirmar Pagamento'
                )}
              </Button>
            )}

          {!loading && reserva && reserva.status_reserva !== 'Cancelada' && (
            <Button
              variant="danger"
              disabled={isUpdating}
              onClick={handleCancelClick}
            >
              {isUpdating ? (
                <Spinner as="span" animation="border" size="sm" />
              ) : (
                'Cancelar Reserva'
              )}
            </Button>
          )}
        </Modal.Footer>
      </Modal>

      <ConfirmacaoModal
        show={showConfirmCancel}
        handleClose={() => setShowConfirmCancel(false)}
        handleConfirm={handleConfirmCancelamento}
        loading={isUpdating}
        title="Confirmar Cancelamento"
        body={`Tem certeza que deseja cancelar a reserva #${reserva?.id_reserva} (${titularNome})? Esta ação não pode ser desfeita.`}
        confirmText="Sim, Cancelar Reserva"
      />
    </>
  );
}

export default ReservaDetalhesModal;
