import React, { useState, useEffect } from 'react';
// --- 1. IMPORTAÇÃO: Importamos o InputGroup ---
import { Modal, Button, Form, Alert, Col, Row, Spinner, InputGroup } from 'react-bootstrap';
import apiClient from '../services/api';

// Enums (sem mudanças)
const TIPOS_DE_QUARTO = ['Solteiro', 'Casal', 'Triplo'];
// const STATUS_DO_QUARTO = ['Vazio', 'Ocupado', 'Agendado', 'Manutenção'];

function QuartoModal({ show, handleClose, onSaveSuccess, quarto }) {
    
    const getInitialState = () => ({
        numero: '',
        valor_diaria: '', // Começa vazio
        tipo_quarto: 'Casal',
        status_quarto: 'Vazio'
    });

    const [formData, setFormData] = useState(getInitialState());
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState(null);

    const isEditMode = quarto !== null;

    useEffect(() => {
        if (isEditMode) {
            setFormData({
                numero: quarto.numero || '',
                // --- 2. FORMATAÇÃO NO 'EDIT': Formata o valor ao carregar ---
                valor_diaria: quarto.valor_diaria ? parseFloat(quarto.valor_diaria).toFixed(2) : '',
                tipo_quarto: quarto.tipo_quarto || 'Casal',
                status_quarto: quarto.status_quarto || 'Vazio'
            });
        } else {
            setFormData(getInitialState());
        }
        setError(null);
    }, [quarto, isEditMode, show]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    // --- 3. NOVA FUNÇÃO: Formata o valor quando o usuário "sai" do campo ---
    const handleValorBlur = (e) => {
        const valor = parseFloat(e.target.value) || 0;
        setFormData(prev => ({
            ...prev,
            valor_diaria: valor.toFixed(2) // Garante 2 casas decimais
        }));
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
            if (isEditMode) {
                await apiClient.put(`/quartos/${quarto.id_quarto}/`, dataToSubmit);
            } else {
                await apiClient.post('/quartos/', dataToSubmit);
            }
            onSaveSuccess();
            handleClose();
        } catch (err) {
            console.error(err.response.data);
            const errorData = err.response.data;
            let errorMsg = 'Ocorreu um erro ao salvar.';
            if (errorData) {
                errorMsg = Object.keys(errorData).map(key => 
                    `${key}: ${errorData[key].join(', ')}`
                ).join(' ');
            }
            setError(errorMsg);
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
                                {/* --- 4. MUDANÇA NO JSX: Adiciona o InputGroup --- */}
                                <InputGroup>
                                    <InputGroup.Text>R$</InputGroup.Text>
                                    <Form.Control
                                        type="number"
                                        name="valor_diaria"
                                        value={formData.valor_diaria}
                                        onChange={handleChange}
                                        onBlur={handleValorBlur} // --- 5. Adiciona o onBlur ---
                                        min="0.01"
                                        step="0.01"
                                        placeholder="0,00"
                                        required
                                    />
                                </InputGroup>
                            </Form.Group>
                        </Col>
                    </Row>
                    
                    <Form.Group className="mb-3" controlId="tipo_quarto">
                        {/* ... (resto do formulário sem mudanças) ... */}
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
                            <Form.Check
                                type="radio"
                                label="Disponível"
                                name="status_quarto"
                                value="Vazio"
                                checked={formData.status_quarto === 'Vazio'}
                                onChange={handleChange}
                                inline
                            />
                            <Form.Check
                                type="radio"
                                label="Em Manutenção"
                                name="status_quarto"
                                value="Manutenção"
                                checked={formData.status_quarto === 'Manutenção'}
                                onChange={handleChange}
                                inline
                            />
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



