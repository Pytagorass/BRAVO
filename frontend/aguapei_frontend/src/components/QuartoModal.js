import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Alert, Col, Row, Spinner, InputGroup } from 'react-bootstrap';
// 🎓 1. Importamos as funções nomeadas do api.js e o toast
import { createQuarto, updateQuarto } from '../services/api';
import { toast } from 'react-toastify';

// 🎓 2. Alinhamos os Enums com o Banco de Dados (views.py)
const TIPOS_DE_QUARTO = ['Solteiro', 'Casal', 'Triplo'];
// O 'value' é o que o backend espera (do seu ENUM 'status_quarto_enum')
const STATUS_DO_QUARTO = [
    { value: 'Disponível', label: 'Disponível' },
    { value: 'Manutenção', label: 'Em Manutenção' },
];

function QuartoModal({ show, handleClose, onSaveSuccess, quarto }) {
    
    const getInitialState = () => ({
        numero: '',
        valor_diaria: '', 
        tipo_quarto: 'Casal', // Padrão
        status_quarto: 'Disponível' // 🎓 Padrão alinhado com o BD
    });

    const [formData, setFormData] = useState(getInitialState());
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState(null);

    const isEditMode = quarto !== null;

    useEffect(() => {
        if (isEditMode) {
            setFormData({
                numero: quarto.numero || '',
                valor_diaria: quarto.valor_diaria ? parseFloat(quarto.valor_diaria).toFixed(2) : '',
                tipo_quarto: quarto.tipo_quarto || 'Casal',
                // 🎓 Garante que o status vindo do BD seja exibido
                status_quarto: quarto.status_quarto || 'Disponível' 
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

    // (Sua lógica de 'onBlur' está perfeita e foi mantida)
    const handleValorBlur = (e) => {
        const valor = parseFloat(e.target.value) || 0;
        setFormData(prev => ({
            ...prev,
            valor_diaria: valor.toFixed(2) // Garante 2 casas decimais
        }));
    };

    // 🎓 3. 'handleSubmit' REFATORADO
    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSaving(true);
        setError(null);

        // 'dataToSubmit' agora é o 'formData' (o 'status_quarto' já está correto)
        const dataToSubmit = {
            ...formData,
            valor_diaria: parseFloat(formData.valor_diaria) || 0,
        };

        try {
            let responseData;
            if (isEditMode) {
                // 🎓 Usamos a função nomeada 'updateQuarto'
                responseData = await updateQuarto(quarto.id_quarto, dataToSubmit);
                toast.success('Quarto atualizado com sucesso!');
            } else {
                // 🎓 Usamos a função nomeada 'createQuarto'
                responseData = await createQuarto(dataToSubmit);
                toast.success('Novo quarto criado com sucesso!');
            }
            
            // 🎓 4. Passa o objeto retornado (responseData) para o pai
            onSaveSuccess(responseData);
            handleClose();

        } catch (errorData) {
            // 🎓 5. Tratamento de erro padronizado
            //    'errorData' é o objeto { code, message, details }
            console.error("Erro ao salvar quarto:", errorData);

            if (errorData.code === 'CONFLICT') {
                // Ex: "Erro: O número de quarto "101" já está cadastrado."
                setError(errorData.message);
            } else if (errorData.message) {
                // Outros erros (Validação, Servidor)
                setError(errorData.message);
            } else {
                setError('Ocorreu um erro desconhecido ao salvar.');
            }
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
                    {/* 🎓 O Alert agora exibirá a mensagem padronizada */}
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

                    {/* 🎓 6. CORREÇÃO DE LÓGICA: Alinhado com o BD */}
                     <Form.Group className="mb-3" controlId="status_quarto">
                        <Form.Label>Status Inicial *</Form.Label>
                        <div>
                            {STATUS_DO_QUARTO.map(status => (
                            <Form.Check
                                key={status.value}
                                type="radio"
                                label={status.label}
                                name="status_quarto"
                                value={status.value} // Envia 'Disponível' ou 'Manutenção'
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