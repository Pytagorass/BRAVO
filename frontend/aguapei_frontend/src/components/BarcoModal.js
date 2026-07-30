/**
 * BarcoModal.js
 * --------------
 * Modal usado para cadastrar ou editar barcos da operacao.
 * Sincroniza com os endpoints `createBarco` e `updateBarco`.
 */
import React, { useEffect, useState } from 'react';
import { Modal, Button, Form, Alert, Row, Col, Spinner, InputGroup } from 'react-bootstrap';
import { toast } from 'react-toastify';

import { createBarco, updateBarco } from '../services/api';

const STATUS_DO_BARCO = [
  { value: 'Disponível', label: 'Disponível' },
  { value: 'Manutenção', label: 'Manutenção' },
  { value: 'Bloqueado', label: 'Bloqueado' },
];

function BarcoModal({ show, handleClose, onSaveSuccess, barco }) {
  const isEditMode = Boolean(barco);

  const getInitialState = () => ({
    nome_barco: '',
    capacidade_pessoas: '',
    status_barco: 'Disponível',
    observacao: '',
  });

  const [formData, setFormData] = useState(getInitialState());
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isEditMode) {
      setFormData({
        nome_barco: barco.nome_barco || '',
        capacidade_pessoas: barco.capacidade_pessoas || '',
        status_barco: barco.status_barco || 'Disponível',
        observacao: barco.observacao || '',
      });
    } else {
      setFormData(getInitialState());
    }

    setError(null);
  }, [barco, isEditMode, show]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setError(null);

    const capacidade = Number.parseInt(formData.capacidade_pessoas, 10);
    if (!Number.isInteger(capacidade) || capacidade <= 0) {
      setError('Informe uma capacidade valida para o barco.');
      setIsSaving(false);
      return;
    }

    const dataToSubmit = {
      ...formData,
      nome_barco: formData.nome_barco.trim(),
      capacidade_pessoas: capacidade,
      observacao: formData.observacao.trim(),
    };

    try {
      const responseData = isEditMode
        ? await updateBarco(barco.id_barco, dataToSubmit)
        : await createBarco(dataToSubmit);

      toast.success(isEditMode ? 'Barco atualizado com sucesso!' : 'Novo barco criado com sucesso!');
      onSaveSuccess(responseData);
      handleClose();
    } catch (err) {
      const apiError = err?.error || err || {};
      setError(apiError.message || 'Ocorreu um erro desconhecido ao salvar.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal show={show} onHide={handleClose} backdrop="static">
      <Modal.Header closeButton>
        <Modal.Title style={{ color: '#26522c' }}>
          {isEditMode ? 'Editar Barco' : 'Novo Barco'}
        </Modal.Title>
      </Modal.Header>

      <Form onSubmit={handleSubmit}>
        <Modal.Body>
          {error && <Alert variant="danger">{error}</Alert>}

          <Row>
            <Col md={7}>
              <Form.Group className="mb-3" controlId="nome_barco">
                <Form.Label>Nome do Barco *</Form.Label>
                <Form.Control
                  type="text"
                  name="nome_barco"
                  value={formData.nome_barco}
                  onChange={handleChange}
                  maxLength={100}
                  placeholder="Ex.: Aguape I"
                  required
                />
              </Form.Group>
            </Col>

            <Col md={5}>
              <Form.Group className="mb-3" controlId="capacidade_pessoas">
                <Form.Label>Capacidade *</Form.Label>
                <InputGroup>
                  <Form.Control
                    type="number"
                    name="capacidade_pessoas"
                    value={formData.capacidade_pessoas}
                    onChange={handleChange}
                    min="1"
                    step="1"
                    required
                  />
                  <InputGroup.Text>pessoas</InputGroup.Text>
                </InputGroup>
              </Form.Group>
            </Col>
          </Row>

          <Form.Group className="mb-3" controlId="status_barco">
            <Form.Label>Status *</Form.Label>
            <div>
              {STATUS_DO_BARCO.map((status) => (
                <Form.Check
                  key={status.value}
                  type="radio"
                  label={status.label}
                  name="status_barco"
                  value={status.value}
                  checked={formData.status_barco === status.value}
                  onChange={handleChange}
                  inline
                />
              ))}
            </div>
          </Form.Group>

          <Form.Group controlId="observacao">
            <Form.Label>Observação</Form.Label>
            <Form.Control
              as="textarea"
              rows={3}
              name="observacao"
              value={formData.observacao}
              onChange={handleChange}
              placeholder="Uso recomendado, restrições, manutenção prevista..."
            />
          </Form.Group>
        </Modal.Body>

        <Modal.Footer>
          <Button variant="secondary" onClick={handleClose} disabled={isSaving}>
            Cancelar
          </Button>
          <Button variant="success" type="submit" disabled={isSaving} style={{ backgroundColor: '#26522c' }}>
            {isSaving ? <Spinner as="span" animation="border" size="sm" /> : 'Salvar Barco'}
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  );
}

export default BarcoModal;
