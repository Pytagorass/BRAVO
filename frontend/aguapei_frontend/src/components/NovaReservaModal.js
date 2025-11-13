// frontend/src/components/NovaReservaModal.js

import React, { useState, useEffect } from 'react';
import {
  Modal,
  Button,
  Form,
  Alert,
  Spinner,
  Row,
  Col,
  InputGroup,
} from 'react-bootstrap';
import {
  fetchHospedes,
  fetchQuartos,
  createReserva,
  updateReservaCompleta,
} from '../services/api';
import { toast } from 'react-toastify';
import ClienteModal from './ClienteModal';
import ReservaConfirmModal from './ReservaConfirmModal';
import './NovaReservaModal.css';
import moment from 'moment';

const MAX_ACOMPANHANTES = 2;
const PAGAMENTO_CHOICES = [
  { value: 'Pendente', label: 'Pendente' },
  { value: 'Pago', label: 'Pago' },
  { value: 'Em Partes', label: 'Em Partes' },
];

function NovaReservaModal({ show, handleClose, onSaveSuccess, reservaParaEditar }) {
  const isEditMode = reservaParaEditar !== null;

  const getInitialState = () => ({
    titularId: '',
    quartoId: '',
    checkin: '',
    checkout: '',
    valor_total: 0,
    forma_pagamento: 'Pendente',
    observacao_reserva: '',
  });

  const [formData, setFormData] = useState(getInitialState());
  const [acompanhantes, setAcompanhantes] = useState([]);
  const [hospedes, setHospedes] = useState([]);
  const [quartos, setQuartos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [showClienteModal, setShowClienteModal] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmData, setConfirmData] = useState(null);
  const [payload, setPayload] = useState(null);

  const fetchModalData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [hospedesResponse, quartosData] = await Promise.all([
        fetchHospedes(),
        fetchQuartos(),
      ]);

      console.log('DEBUG: Resposta de Hóspedes:', hospedesResponse);
      console.log('DEBUG: Resposta de Quartos:', quartosData);

      setHospedes(hospedesResponse || []);
      setQuartos(quartosData || []);
    } catch (err) {
      console.error('DEBUG: Falha ao carregar dados:', err);
      setError(err.message || 'Falha ao carregar dados. Tente fechar e abrir o modal.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (show) {
      fetchModalData();
      setError(null);

      if (isEditMode) {
        setFormData({
          titularId: reservaParaEditar.id_titular || '',
          quartoId: reservaParaEditar.id_quarto || '',
          checkin: moment(reservaParaEditar.checkin).format('YYYY-MM-DD'),
          checkout: moment(reservaParaEditar.checkout).format('YYYY-MM-DD'),
          valor_total: reservaParaEditar.valor_total || 0,
          forma_pagamento: reservaParaEditar.status_pagamento || 'Pendente',
          observacao_reserva: reservaParaEditar.observacao_reserva || '',
        });
        const acompanhanteIds = (reservaParaEditar.acompanhantes || []).map(
          (a) => a.id_hospede
        );
        setAcompanhantes(acompanhanteIds);
      } else {
        setFormData(getInitialState());
        setAcompanhantes([]);
      }
    }
  }, [show, reservaParaEditar, isEditMode]);

  useEffect(() => {
    if (formData.checkin && formData.checkout && formData.quartoId) {
      const selectedQuarto = (quartos || []).find(
        (q) => q.id_quarto === parseInt(formData.quartoId)
      );
      if (selectedQuarto) {
        const start = moment(formData.checkin);
        const end = moment(formData.checkout);
        const diffDays = end.diff(start, 'days');
        const total =
          diffDays > 0
            ? diffDays * selectedQuarto.valor_diaria
            : diffDays === 0
            ? selectedQuarto.valor_diaria
            : 0;
        setFormData((prev) => ({ ...prev, valor_total: total }));
      }
    }
  }, [formData.checkin, formData.checkout, formData.quartoId, quartos]);

  const handleChange = (e) => {
    if (e.target.name === 'checkin' || e.target.name === 'checkout') {
      if (error === 'Data de Check-out deve ser após o Check-in.') setError(null);
    }
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleAcompanhanteChange = (index, value) => {
    const novosAcompanhantes = [...acompanhantes];
    novosAcompanhantes[index] = value;
    setAcompanhantes(novosAcompanhantes);
  };

  const handleAddAcompanhante = () => {
    if (acompanhantes.length < MAX_ACOMPANHANTES) {
      setAcompanhantes([...acompanhantes, '']);
    }
  };

  const handleRemoveAcompanhante = (index) => {
    setAcompanhantes(acompanhantes.filter((_, i) => i !== index));
  };

  const handleClienteSaveSuccess = (newCliente) => {
    setShowClienteModal(false);
    setHospedes((prev) => [...prev, newCliente]);
    setFormData((prev) => ({ ...prev, titularId: newCliente.id_hospede }));
    toast.success(`${newCliente.nome_hospede} criado e selecionado.`);
  };

  const handleCloseInternal = () => {
    setIsSaving(false);
    setShowConfirm(false);
    handleClose();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (moment(formData.checkout).isSameOrBefore(formData.checkin)) {
      setError('Data de Check-out deve ser após o Check-in.');
      return;
    }

    const acompanhanteIds = acompanhantes.filter((id) => id);
    const finalPayload = {
      fk_hospede_id_hospede: formData.titularId,
      quartos: [formData.quartoId],
      checkin: formData.checkin,
      checkout: formData.checkout,
      valor_total: formData.valor_total,
      forma_pagamento: formData.forma_pagamento,
      status_pagamento: formData.forma_pagamento,
      observacao_reserva: formData.observacao_reserva,
      acompanhantes: acompanhanteIds,
    };

    const titular = (hospedes || []).find(
      (h) => h.id_hospede === parseInt(formData.titularId)
    );
    const quarto = (quartos || []).find(
      (q) => q.id_quarto === parseInt(formData.quartoId)
    );

    setConfirmData({
      titularNome: titular ? titular.nome_hospede : 'N/A',
      quartoNome: quarto ? quarto.numero : 'N/A',
      checkin: formData.checkin,
      checkout: formData.checkout,
      forma_pagamento: formData.forma_pagamento,
    });

    setPayload(finalPayload);
    setShowConfirm(true);
  };

  const handleExecuteSubmit = async () => {
    if (!payload) return;
    setIsSaving(true);

    try {
      let responseData;
      if (isEditMode) {
        responseData = await updateReservaCompleta(
          reservaParaEditar.id_reserva_quarto,
          payload
        );
        toast.success('Reserva atualizada com sucesso!');
      } else {
        responseData = await createReserva(payload);
        toast.success(`Reserva #${responseData.id_reserva} criada com sucesso!`);
      }

      onSaveSuccess(responseData);
      setShowConfirm(false);
      handleCloseInternal();
    } catch (errorData) {
      console.error('Erro ao salvar reserva:', errorData);
      setShowConfirm(false);

      if (errorData.code === 'OVERBOOK_CONFLICT') {
        const conflito = errorData.details;
        const checkinFmt = moment(conflito.checkin).format('DD/MM/YYYY');
        const checkoutFmt = moment(conflito.checkout).format('DD/MM/YYYY');
        setError(
          `Conflito! Quarto já reservado por ${conflito.nome_titular_conflito} de ${checkinFmt} até ${checkoutFmt}.`
        );
      } else {
        setError(errorData.message || 'Ocorreu um erro desconhecido.');
      }
    } finally {
      setIsSaving(false);
      setPayload(null);
    }
  };

  const hospedesDisponiveis =
    hospedes?.filter((h) => h.id_hospede !== parseInt(formData.titularId)) ?? [];

  return (
    <>
      <Modal show={show} onHide={handleCloseInternal} size="lg">
        <Form onSubmit={handleSubmit}>
          <Modal.Header closeButton>
            <Modal.Title style={{ color: '#26522c' }}>
              {isEditMode ? 'Editar Reserva' : 'Nova Reserva'}
            </Modal.Title>
          </Modal.Header>

          <Modal.Body>
            {loading && (
              <div className="text-center">
                <Spinner animation="border" variant="success" />
                <p>Carregando dados...</p>
              </div>
            )}

            {!loading && error && <Alert variant="danger">{error}</Alert>}

            {!loading && (
              <>
                <Row className="mb-3">
                  <Col md={6}>
                    <Form.Group controlId="formTitular">
                      <Form.Label>Titular da Reserva*</Form.Label>
                      <InputGroup>
                        <Form.Select
                          name="titularId"
                          value={formData.titularId}
                          onChange={handleChange}
                          required
                        >
                          <option value="">Selecione um hóspede</option>
                          {(hospedes || []).map((h) => (
                            <option key={h.id_hospede} value={h.id_hospede}>
                              {h.nome_hospede}
                            </option>
                          ))}
                        </Form.Select>
                        <Button
                          variant="outline-success"
                          onClick={() => setShowClienteModal(true)}
                        >
                          + Novo
                        </Button>
                      </InputGroup>
                    </Form.Group>
                  </Col>

                  <Col md={6}>
                    <Form.Group controlId="formQuarto">
                      <Form.Label>Quarto*</Form.Label>
                      <Form.Select
                        name="quartoId"
                        value={formData.quartoId}
                        onChange={handleChange}
                        required
                      >
                        <option value="">Selecione um quarto</option>
                        {(quartos || []).map((q) => (
                          <option key={q.id_quarto} value={q.id_quarto}>
                            {q.numero} ({q.tipo_quarto}) - R$ {q.valor_diaria}
                          </option>
                        ))}
                      </Form.Select>
                    </Form.Group>
                  </Col>
                </Row>

                {acompanhantes.map((acompId, index) => (
                  <Form.Group
                    key={index}
                    className="mb-3"
                    controlId={`formAcompanhante${index}`}
                  >
                    <Form.Label>Acompanhante {index + 1}</Form.Label>
                    <InputGroup>
                      <Form.Select
                        value={acompId}
                        onChange={(e) =>
                          handleAcompanhanteChange(index, e.target.value)
                        }
                      >
                        <option value="">Selecione um acompanhante</option>
                        {hospedesDisponiveis.map((h) => (
                          <option key={h.id_hospede} value={h.id_hospede}>
                            {h.nome_hospede}
                          </option>
                        ))}
                      </Form.Select>
                      <Button
                        variant="outline-danger"
                        onClick={() => handleRemoveAcompanhante(index)}
                      >
                        &times;
                      </Button>
                    </InputGroup>
                  </Form.Group>
                ))}

                {acompanhantes.length < MAX_ACOMPANHANTES && (
                  <Button
                    variant="link"
                    onClick={handleAddAcompanhante}
                    className="p-0 mb-3"
                  >
                    + Adicionar Acompanhante
                  </Button>
                )}

                <Row className="mb-3">
                  <Col md={6}>
                    <Form.Group controlId="formCheckin">
                      <Form.Label>Check-in*</Form.Label>
                      <Form.Control
                        type="date"
                        name="checkin"
                        value={formData.checkin}
                        onChange={handleChange}
                        required
                      />
                    </Form.Group>
                  </Col>

                  <Col md={6}>
                    <Form.Group controlId="formCheckout">
                      <Form.Label>Check-out*</Form.Label>
                      <Form.Control
                        type="date"
                        name="checkout"
                        value={formData.checkout}
                        onChange={handleChange}
                        required
                      />
                    </Form.Group>
                  </Col>
                </Row>

                <div className="valor-total-container">
                  <h3>
                    Valor Total:{' '}
                    <span className="valor-total-preco">
                      R$ {parseFloat(formData.valor_total)
                        .toFixed(2)
                        .replace('.', ',')}
                    </span>
                  </h3>
                </div>

                <hr />

                <Row>
                  <Col>
                    <Form.Group controlId="formFormaPagamento">
                      <Form.Label>Status Pagamento</Form.Label>
                      <Form.Select
                        name="forma_pagamento"
                        value={formData.forma_pagamento}
                        onChange={handleChange}
                      >
                        {PAGAMENTO_CHOICES.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </Form.Select>
                    </Form.Group>
                  </Col>
                </Row>

                <Form.Group controlId="formObservacao" className="mt-3">
                  <Form.Label>Observações</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    name="observacao_reserva"
                    value={formData.observacao_reserva}
                    onChange={handleChange}
                  />
                </Form.Group>
              </>
            )}
          </Modal.Body>

          <Modal.Footer>
            <Button variant="secondary" onClick={handleCloseInternal} disabled={isSaving}>
              Cancelar
            </Button>
            <Button
              variant="success"
              type="submit"
              style={{ backgroundColor: '#26522c', border: 'none' }}
              disabled={isSaving || loading}
            >
              {isSaving ? (
                <Spinner as="span" animation="border" size="sm" />
              ) : isEditMode ? (
                'Salvar Alterações'
              ) : (
                'Salvar Reserva'
              )}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      <ClienteModal
        show={showClienteModal}
        handleClose={() => setShowClienteModal(false)}
        onSaveSuccess={handleClienteSaveSuccess}
        cliente={null}
      />

      {showConfirm && confirmData && (
        <ReservaConfirmModal
          show={showConfirm}
          handleClose={() => setShowConfirm(false)}
          confirmData={confirmData}
          onConfirm={handleExecuteSubmit}
          isSaving={isSaving}
        />
      )}
    </>
  );
}

export default NovaReservaModal;
