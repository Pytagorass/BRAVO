/**
 * QuartoModal.js
 * --------------
 * Modal reutilizado para cadastrar ou editar quartos dentro do módulo
 * administrativo. Sincroniza-se com os endpoints `createQuarto` e
 * `updateQuarto`.
 */
import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Alert, Col, Row, Spinner, InputGroup } from 'react-bootstrap';
import { createQuarto, updateQuarto } from '../services/api';
import { toast } from 'react-toastify';

const TIPOS_DE_QUARTO = ['Solteiro', 'Casal', 'Triplo'];
const STATUS_DO_QUARTO = [
    { value: 'Disponível', label: 'Disponível' },
    { value: 'Manutenção', label: 'Em Manutenção' },
];

/**
 * Props:
 *  - show/handleClose: controle do Modal.
 *  - onSaveSuccess: devolve o quarto salvo para atualizar a lista.
 *  - quarto: quando enviado, ativa o modo edição.
 */
function QuartoModal({ show, handleClose, onSaveSuccess, quarto }) {
    const isEditMode = Boolean(quarto);

    const getInitialState = () => ({
        numero: '',
        valor_diaria: '',
        tipo_quarto: 'Casal',
        status_quarto: 'Disponível',
    });

    const [formData, setFormData] = useState(getInitialState());
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Sincroniza formulário ao abrir o modal ou trocar de quarto selecionado.
        if (isEditMode) {
            setFormData({
                numero: quarto.numero || '',
                valor_diaria: quarto.valor_diaria ? parseFloat(quarto.valor_diaria).toFixed(2) : '',
                tipo_quarto: quarto.tipo_quarto || 'Casal',
                status_quarto: quarto.status_quarto || 'Disponível',
            });
        } else {
            setFormData(getInitialState());
        }
        setError(null);
    }, [quarto, isEditMode, show]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleValorBlur = (e) => {
        const valor = parseFloat(e.target.value) || 0;
        setFormData((prev) => ({ ...prev, valor_diaria: valor.toFixed(2) }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSaving(true);
        setError(null);

        const dataToSubmit = {
            ...formData,
            valor_diaria: parseFloat(formData.valor_diaria) || 0,
        };

        try {
            const responseData = isEditMode
                ? await updateQuarto(quarto.id_quarto, dataToSubmit)
                : await createQuarto(dataToSubmit);

            toast.success(isEditMode ? 'Quarto atualizado com sucesso!' : 'Novo quarto criado com sucesso!');
            onSaveSuccess(responseData);
            handleClose();
        } catch (err) {
            console.error("Erro ao salvar quarto:", err);
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
                    {isEditMode ? 'Editar Quarto' : 'Novo Quarto'}
                </Modal.Title>
            </Modal.Header>

            <Form onSubmit={handleSubmit}>
                <Modal.Body>
                    {error && <Alert variant="danger">{error}</Alert>}

                    <Row>
                        <Col md={6}>
                            <Form.Group className="mb-3" controlId="numero">
                                <Form.Label>Nome / Número do Quarto *</Form.Label>
                                <Form.Control
                                    type="text"
                                    name="numero"
                                    value={formData.numero}
                                    onChange={handleChange}
                                    required
                                />
                            </Form.Group>
                        </Col>
                        <Col md={6}>
                            <Form.Group className="mb-3" controlId="valor_diaria">
                                <Form.Label>Valor da Diária *</Form.Label>
                                <InputGroup>
                                    <InputGroup.Text>R$</InputGroup.Text>
                                    <Form.Control
                                        type="number"
                                        name="valor_diaria"
                                        value={formData.valor_diaria}
                                        onChange={handleChange}
                                        onBlur={handleValorBlur}
                                        min="0.01"
                                        step="0.01"
                                        placeholder="0.00"
                                        required
                                    />
                                </InputGroup>
                            </Form.Group>
                        </Col>
                    </Row>

                    <Form.Group className="mb-3" controlId="tipo_quarto">
                        <Form.Label>Tipo de Quarto *</Form.Label>
                        <Form.Select
                            name="tipo_quarto"
                            value={formData.tipo_quarto}
                            onChange={handleChange}
                        >
                            {TIPOS_DE_QUARTO.map(tipo => (
                                <option key={tipo} value={tipo}>{tipo}</option>
                            ))}
                        </Form.Select>
                    </Form.Group>

                    <Form.Group className="mb-3" controlId="status_quarto">
                        <Form.Label>Status Inicial *</Form.Label>
                        <div>
                            {STATUS_DO_QUARTO.map(status => (
                                <Form.Check
                                    key={status.value}
                                    type="radio"
                                    label={status.label}
                                    name="status_quarto"
                                    value={status.value}
                                    checked={formData.status_quarto === status.value}
                                    onChange={handleChange}
                                    inline
                                />
                            ))}
                        </div>
                    </Form.Group>
                </Modal.Body>

                <Modal.Footer>
                    <Button variant="secondary" onClick={handleClose} disabled={isSaving}>
                        Cancelar
                    </Button>
                    <Button variant="success" type="submit" disabled={isSaving} style={{ backgroundColor: '#26522c' }}>
                        {isSaving ? <Spinner as="span" animation="border" size="sm" /> : 'Salvar Quarto'}
                    </Button>
                </Modal.Footer>
            </Form>
        </Modal>
    );
}

export default QuartoModal;
