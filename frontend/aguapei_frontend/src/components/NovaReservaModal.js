/**
 * NovaReservaModal.js
 * -------------------
 * Formulário completo para criação/edição de reservas direto da Agenda.
 * Controla:
 *  - Busca de hóspedes/quartos disponíveis.
 *  - Preenchimento do payload aceito pelo backend.
 *  - Seleção de acompanhantes, cálculo automático de valor e confirmação.
 */
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
  fetchBarcos,
  fetchTiposPasseio,
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

const calcularDiasViagem = (embarque, desembarque) => {
  if (!embarque || !desembarque) return 0;
  const diff = moment(desembarque).diff(moment(embarque), 'days');
  return diff >= 0 ? diff + 1 : 0;
};

/**
 * Modal responsável por criar ou editar reservas.
 *
 * Props:
 *  - show: controla visibilidade.
 *  - handleClose: callback para fechar e limpar o formulário.
 *  - onSaveSuccess: disparado quando o backend retorna a reserva salva.
 *  - reservaParaEditar: objeto existente (quando aberto em modo edição).
 */
function NovaReservaModal({ show, handleClose, onSaveSuccess, reservaParaEditar }) {
  const isEditMode = reservaParaEditar !== null;

// Estado base usado tanto para criação quanto para resetar o formulário.
const getInitialState = () => ({
    titularId: '',
    quartoId: '',
    checkin: '',
    checkout: '',
    barcoId: '',
    tipoPasseioId: '',
    data_embarque: '',
    data_desembarque: '',
    local_embarque: '',
    local_desembarque: '',
    valor_total: 0,
    status_pagamento: 'Pendente',
    observacao_reserva: '',
    observacao_operacional: '',
  });

  const [formData, setFormData] = useState(getInitialState());
  const [acompanhantes, setAcompanhantes] = useState([]);
  const [hospedes, setHospedes] = useState([]);
  const [quartos, setQuartos] = useState([]);
  const [barcos, setBarcos] = useState([]);
  const [loadingBarcos, setLoadingBarcos] = useState(false);
  const [tiposPasseio, setTiposPasseio] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [showClienteModal, setShowClienteModal] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmData, setConfirmData] = useState(null);
  const [payload, setPayload] = useState(null);

  // Carrega hóspedes/quartos antes de abrir o formulário.
  const fetchModalData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [hospedesResponse, quartosData, barcosData, tiposPasseioData] = await Promise.all([
        fetchHospedes(),
        fetchQuartos(),
        fetchBarcos(),
        fetchTiposPasseio(),
      ]);

      console.log('DEBUG: Resposta de Hóspedes:', hospedesResponse);
      console.log('DEBUG: Resposta de Quartos:', quartosData);

      setHospedes(hospedesResponse || []);
      setQuartos(quartosData || []);
      setBarcos(barcosData || []);
      setTiposPasseio(tiposPasseioData || []);
    } catch (err) {
      console.error('DEBUG: Falha ao carregar dados:', err);
      setError(err.message || 'Falha ao carregar dados. Tente fechar e abrir o modal.');
    } finally {
      setLoading(false);
    }
  };

  // Sempre que o modal abre, carrega dados auxiliares e popula form.
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
          barcoId: reservaParaEditar.fk_barco || '',
          tipoPasseioId: reservaParaEditar.fk_tipo_passeio || '',
          data_embarque: reservaParaEditar.data_embarque
            ? moment(reservaParaEditar.data_embarque).format('YYYY-MM-DD')
            : moment(reservaParaEditar.checkin).format('YYYY-MM-DD'),
          data_desembarque: reservaParaEditar.data_desembarque
            ? moment(reservaParaEditar.data_desembarque).format('YYYY-MM-DD')
            : moment(reservaParaEditar.checkout).format('YYYY-MM-DD'),
          local_embarque: reservaParaEditar.local_embarque || '',
          local_desembarque: reservaParaEditar.local_desembarque || '',
          valor_total: reservaParaEditar.valor_total || 0,
          status_pagamento: reservaParaEditar.status_pagamento || 'Pendente',
          observacao_reserva: reservaParaEditar.observacao_reserva || '',
          observacao_operacional: reservaParaEditar.observacao_operacional || '',
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

  // Recalcula automaticamente o valor total quando datas/quarto mudam.
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

  const dataEmbarqueOperacao = formData.data_embarque;
  const dataDesembarqueOperacao = formData.data_desembarque;

  useEffect(() => {
    if (!show) return undefined;

    const periodoValido =
      dataEmbarqueOperacao &&
      dataDesembarqueOperacao &&
      !moment(dataDesembarqueOperacao).isBefore(dataEmbarqueOperacao);

    let ativo = true;

    const carregarBarcosDisponiveis = async () => {
      setLoadingBarcos(true);

      try {
        const params = periodoValido
          ? {
              data_embarque: dataEmbarqueOperacao,
              data_desembarque: dataDesembarqueOperacao,
            }
          : {};

        if (periodoValido && isEditMode && reservaParaEditar?.id_reserva) {
          params.reserva_id = reservaParaEditar.id_reserva;
        }

        const barcosData = await fetchBarcos(params);
        if (!ativo) return;

        const barcosAtualizados = barcosData || [];
        setBarcos(barcosAtualizados);

        setFormData((prev) => {
          if (
            prev.barcoId &&
            !barcosAtualizados.some((barco) => String(barco.id_barco) === String(prev.barcoId))
          ) {
            return { ...prev, barcoId: '' };
          }

          return prev;
        });
      } catch (err) {
        if (!ativo) return;
        const apiError = err?.error || err || {};
        setError(apiError.message || 'Falha ao filtrar barcos disponíveis.');
      } finally {
        if (ativo) setLoadingBarcos(false);
      }
    };

    const timeoutId = setTimeout(carregarBarcosDisponiveis, 250);

    return () => {
      ativo = false;
      clearTimeout(timeoutId);
    };
  }, [
    show,
    dataEmbarqueOperacao,
    dataDesembarqueOperacao,
    isEditMode,
    reservaParaEditar,
  ]);

  const handleChange = (e) => {
    const { name, value } = e.target;

    if (name === 'checkin' || name === 'checkout') {
      if (error === 'Data de Check-out deve ser após o Check-in.') setError(null);
    }

    setFormData((prev) => {
      const next = { ...prev, [name]: value };

      if (name === 'checkin' && (!prev.data_embarque || prev.data_embarque === prev.checkin)) {
        next.data_embarque = value;
      }

      if (name === 'checkout' && (!prev.data_desembarque || prev.data_desembarque === prev.checkout)) {
        next.data_desembarque = value;
      }

      return next;
    });
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

  // Valida payload, abre modal de confirmação e prepara request final.
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (moment(formData.checkout).isSameOrBefore(formData.checkin)) {
      setError('Data de Check-out deve ser após o Check-in.');
      return;
    }

    if (!formData.barcoId) {
      setError('Selecione um barco para a viagem.');
      return;
    }

    if (!formData.tipoPasseioId) {
      setError('Selecione o tipo de passeio.');
      return;
    }

    if (!formData.data_embarque || !formData.data_desembarque) {
      setError('Informe as datas de embarque e desembarque.');
      return;
    }

    if (moment(formData.data_desembarque).isBefore(formData.data_embarque)) {
      setError('Data de desembarque deve ser igual ou posterior ao embarque.');
      return;
    }

    const acompanhanteIds = acompanhantes.filter((id) => id);
    const finalPayload = {
      fk_hospede_id_hospede: formData.titularId,
      quartos: [formData.quartoId],
      checkin: formData.checkin,
      checkout: formData.checkout,
      fk_barco: formData.barcoId,
      fk_tipo_passeio: formData.tipoPasseioId,
      data_embarque: formData.data_embarque,
      data_desembarque: formData.data_desembarque,
      local_embarque: formData.local_embarque,
      local_desembarque: formData.local_desembarque,
      valor_total: formData.valor_total,
      status_pagamento: formData.status_pagamento,
      observacao_reserva: formData.observacao_reserva,
      observacao_operacional: formData.observacao_operacional,
      acompanhantes: acompanhanteIds,
    };

    const titular = (hospedes || []).find(
      (h) => h.id_hospede === parseInt(formData.titularId)
    );
    const quarto = (quartos || []).find(
      (q) => q.id_quarto === parseInt(formData.quartoId)
    );
    const barco = (barcos || []).find(
      (b) => b.id_barco === parseInt(formData.barcoId)
    );
    const tipoPasseio = (tiposPasseio || []).find(
      (tipo) => tipo.id_tipo_passeio === parseInt(formData.tipoPasseioId)
    );

    setConfirmData({
      titularNome: titular ? titular.nome_hospede : 'N/A',
      quartoNome: quarto ? quarto.numero : 'N/A',
      barcoNome: barco ? barco.nome_barco : 'N/A',
      tipoPasseioNome: tipoPasseio ? tipoPasseio.nome_tipo : 'N/A',
      checkin: formData.checkin,
      checkout: formData.checkout,
      data_embarque: formData.data_embarque,
      data_desembarque: formData.data_desembarque,
      diasViagem: calcularDiasViagem(formData.data_embarque, formData.data_desembarque),
      status_pagamento: formData.status_pagamento,
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

      const apiError = errorData?.error || errorData || {};
      if (apiError.code === 'OVERBOOK' && apiError.details) {
        const conflito = apiError.details;
        const checkinFmt = moment(conflito.checkin).format('DD/MM/YYYY');
        const checkoutFmt = moment(conflito.checkout).format('DD/MM/YYYY');
        setError(
          `Conflito! Quarto ja reservado por ${conflito.nome_titular_conflito} de ${checkinFmt} ate ${checkoutFmt}.`
        );
      } else if (apiError.code === 'BARCO_OVERBOOK' && apiError.details) {
        const conflito = apiError.details;
        const embarqueFmt = moment(conflito.data_embarque).format('DD/MM/YYYY');
        const desembarqueFmt = moment(conflito.data_desembarque).format('DD/MM/YYYY');
        setError(
          `Conflito! Barco ja reservado por ${conflito.nome_titular_conflito || 'outro grupo'} de ${embarqueFmt} ate ${desembarqueFmt}.`
        );
      } else {
        setError(apiError.message || 'Ocorreu um erro desconhecido.');
      }
    } finally {
      setIsSaving(false);
      setPayload(null);
    }
  };

  const hospedesDisponiveis =
    hospedes?.filter((h) => h.id_hospede !== parseInt(formData.titularId)) ?? [];
  const diasViagem = calcularDiasViagem(formData.data_embarque, formData.data_desembarque);
  const periodoOperacaoSelecionado =
    formData.data_embarque &&
    formData.data_desembarque &&
    !moment(formData.data_desembarque).isBefore(formData.data_embarque);

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

                <div className="operacao-viagem-section">
                  <div className="operacao-viagem-header">
                    <div>
                      <h5>Operação da Viagem</h5>
                      <p>Defina o barco, o tipo de passeio e o período operacional do grupo.</p>
                    </div>
                    {diasViagem > 0 && (
                      <span className="dias-viagem-pill">
                        {diasViagem} {diasViagem === 1 ? 'dia' : 'dias'}
                      </span>
                    )}
                  </div>

                  {!loadingBarcos && periodoOperacaoSelecionado && barcos.length === 0 && (
                    <Alert variant="warning" className="mb-3">
                      Nenhum barco disponível para o período selecionado. Ajuste as datas ou libere outro barco.
                    </Alert>
                  )}

                  {!loadingBarcos && !periodoOperacaoSelecionado && barcos.length === 0 && (
                    <Alert variant="warning" className="mb-3">
                      Nenhum barco disponível encontrado. Cadastre ou libere um barco antes de criar a reserva.
                    </Alert>
                  )}

                  <Row className="mb-3">
                    <Col md={6}>
                      <Form.Group controlId="formBarco">
                        <Form.Label>Barco*</Form.Label>
                        <Form.Select
                          name="barcoId"
                          value={formData.barcoId}
                          onChange={handleChange}
                          disabled={loadingBarcos}
                          required
                        >
                          <option value="">
                            {loadingBarcos ? 'Filtrando barcos...' : 'Selecione um barco'}
                          </option>
                          {(barcos || []).map((barco) => (
                            <option key={barco.id_barco} value={barco.id_barco}>
                              {barco.nome_barco} ({barco.capacidade_pessoas} pessoas)
                            </option>
                          ))}
                        </Form.Select>
                        <Form.Text muted>
                          {periodoOperacaoSelecionado
                            ? 'Lista filtrada pelo período de embarque e desembarque.'
                            : 'Informe embarque e desembarque para filtrar por disponibilidade.'}
                        </Form.Text>
                      </Form.Group>
                    </Col>

                    <Col md={6}>
                      <Form.Group controlId="formTipoPasseio">
                        <Form.Label>Tipo de Passeio*</Form.Label>
                        <Form.Select
                          name="tipoPasseioId"
                          value={formData.tipoPasseioId}
                          onChange={handleChange}
                          required
                        >
                          <option value="">Selecione o passeio</option>
                          {(tiposPasseio || []).map((tipo) => (
                            <option key={tipo.id_tipo_passeio} value={tipo.id_tipo_passeio}>
                              {tipo.nome_tipo}
                            </option>
                          ))}
                        </Form.Select>
                      </Form.Group>
                    </Col>
                  </Row>

                  <Row className="mb-3">
                    <Col md={6}>
                      <Form.Group controlId="formDataEmbarque">
                        <Form.Label>Data de Embarque*</Form.Label>
                        <Form.Control
                          type="date"
                          name="data_embarque"
                          value={formData.data_embarque}
                          onChange={handleChange}
                          required
                        />
                      </Form.Group>
                    </Col>

                    <Col md={6}>
                      <Form.Group controlId="formDataDesembarque">
                        <Form.Label>Data de Desembarque*</Form.Label>
                        <Form.Control
                          type="date"
                          name="data_desembarque"
                          value={formData.data_desembarque}
                          onChange={handleChange}
                          required
                        />
                      </Form.Group>
                    </Col>
                  </Row>

                  <Row>
                    <Col md={6}>
                      <Form.Group controlId="formLocalEmbarque">
                        <Form.Label>Local de Embarque</Form.Label>
                        <Form.Control
                          name="local_embarque"
                          value={formData.local_embarque}
                          onChange={handleChange}
                          placeholder="Ex.: Porto Aguapé"
                        />
                      </Form.Group>
                    </Col>

                    <Col md={6}>
                      <Form.Group controlId="formLocalDesembarque">
                        <Form.Label>Local de Desembarque</Form.Label>
                        <Form.Control
                          name="local_desembarque"
                          value={formData.local_desembarque}
                          onChange={handleChange}
                          placeholder="Ex.: Porto Aguapé"
                        />
                      </Form.Group>
                    </Col>
                  </Row>

                  <Form.Group controlId="formObservacaoOperacional" className="mt-3">
                    <Form.Label>Observações Operacionais</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={2}
                      name="observacao_operacional"
                      value={formData.observacao_operacional}
                      onChange={handleChange}
                      placeholder="Preferências do grupo, restrições, alimentação, roteiro combinado..."
                    />
                  </Form.Group>
                </div>

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
                        name="status_pagamento"
                        value={formData.status_pagamento}
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
          handleConfirm={handleExecuteSubmit}
          loading={isSaving}
        />
      )}
    </>
  );
}

export default NovaReservaModal;
