import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Alert, Col, Row, Spinner } from 'react-bootstrap';
import { createHospede, updateHospede } from '../services/api';
import { toast } from 'react-toastify';

function ClienteModal({ show, handleClose, onSaveSuccess, cliente }) {
    const getInitialState = () => ({
        nome_hospede: '',
        telefone: '',
        email_hospede: '',
        pais_origem: 'Brasil',
        passaporte: '',
        cpf: ''
    });

    const [formData, setFormData] = useState(getInitialState());
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState(null);

    const isEditMode = Boolean(cliente);
    const isBrasil = formData.pais_origem === 'Brasil';

    useEffect(() => {
        if (isEditMode && cliente) {
            setFormData({
                nome_hospede: cliente.nome_hospede || '',
                telefone: cliente.telefone || '',
                email_hospede: cliente.email_hospede || '',
                pais_origem: cliente.pais_origem || 'Brasil',
                passaporte: cliente.passaporte || '',
                cpf: cliente.cpf || ''
            });
        } else {
            setFormData(getInitialState());
        }
        setError(null);
    }, [cliente, isEditMode, show]);

    // 🎓 3. HandleChange APRIMORADO
    //    Limpa o campo de documento oposto ao mudar o país
    //    para evitar enviar (ex:) CPF para um 'pais_origem' != 'Brasil'
    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => {
            const newState = { ...prev, [name]: value };

            // Lógica de limpeza (baseada no protótipo e na validação do backend)
            if (name === 'pais_origem') {
                if (value === 'Brasil') {
                    newState.passaporte = ''; // Limpa passaporte se for Brasil
                } else {
                    newState.cpf = ''; // Limpa CPF se não for Brasil
                }
            }
            return newState;
        });
    };

    // 🎓 4. HandleSubmit REFATORADO
    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSaving(true);
        setError(null);

        try {
            let savedCliente;

            if (isEditMode) {
                savedCliente = await updateHospede(cliente.id_hospede, formData);
                toast.success('Cliente atualizado com sucesso!');
            } else {
                savedCliente = await createHospede(formData);
                toast.success('Novo cliente salvo com sucesso!');
            }

            onSaveSuccess(savedCliente);
            handleClose();

        } catch (errorData) {
            console.error("Erro ao salvar:", errorData);

            const apiError = errorData?.error || errorData || {};
            if (apiError.code === 'VALIDATION_ERROR' || apiError.code === 'CONFLICT') {
                setError(apiError.message);
            } else if (apiError.message) {
                setError(apiError.message);
            } else {
                setError('Ocorreu um erro ao salvar. Tente novamente.');
            }
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <Modal show={show} onHide={handleClose} backdrop="static" size="lg">
            <Modal.Header closeButton>
                <Modal.Title style={{ color: '#26522c' }}>
                    {isEditMode ? 'Editar Cliente' : 'Novo Cliente'}
                </Modal.Title>
            </Modal.Header>
            <Form onSubmit={handleSubmit}>
                <Modal.Body>

                    {/* 🎓 7. O Alert Inline agora exibe a 'message' da nossa API */}
                    {error && <Alert variant="danger">{error}</Alert>}

                    {/* Linha 1: Nome */}
                    <Form.Group className="mb-3" controlId="nome_hospede">
                        <Form.Label>Nome *</Form.Label>
                        <Form.Control
                            type="text"
                            name="nome_hospede"
                            value={formData.nome_hospede}
                            onChange={handleChange}
                            required
                        />
                    </Form.Group>

                    {/* Linha 2: Telefone e E-mail */}
                    <Row>
                        <Col md={6}>
                            <Form.Group className="mb-3" controlId="telefone">
                                <Form.Label>Telefone</Form.Label>
                                <Form.Control
                                    type="text"
                                    name="telefone"
                                    value={formData.telefone}
                                    onChange={handleChange}
                                />
                            </Form.Group>
                        </Col>
                        <Col md={6}>
                            <Form.Group className="mb-3" controlId="email_hospede">
                                <Form.Label>E-mail (Único)</Form.Label>
                                <Form.Control
                                    type="email"
                                    name="email_hospede"
                                    value={formData.email_hospede}
                                    onChange={handleChange}
                                    // 🎓 Boa prática: adicionar 'required' no e-mail
                                    required
                                />
                            </Form.Group>
                        </Col>
                    </Row>

                    {/* Linha 3: País (com lógica de seleção) */}
                    <Form.Group className="mb-3" controlId="pais_origem">
                        <Form.Label>País</Form.Label>
                        <Form.Select // 🎓 <Form.Select> é a tag correta no Bootstrap 5
                            name="pais_origem"
                            value={formData.pais_origem}
                            onChange={handleChange}
                        >
                            <option value="Brasil">Brasil</option>
                            <option value="Argentina">Argentina</option>
                            <option value="Estados Unidos">Estados Unidos</option>
                            <option value="Itália">Itália</option>
                            <option value="Alemanha">Alemanha</option>
                            <option value="Outro">Outro</option>
                        </Form.Select>
                    </Form.Group>

                    {/* Linha 4: CPF e Passaporte (lógica condicional mantida) */}
                    <Row>
                        <Col md={6}>
                            <Form.Group className="mb-3" controlId="cpf">
                                <Form.Label>CPF (Único){isBrasil && ' *'}</Form.Label>
                                <Form.Control
                                    type="text"
                                    name="cpf"
                                    value={formData.cpf}
                                    onChange={handleChange}
                                    required={isBrasil}
                                    disabled={!isBrasil}
                                    // 🎓 Limpa o campo se for desabilitado
                                    key={isBrasil ? 'cpf-br' : 'cpf-other'}
                                />
                            </Form.Group>
                        </Col>
                        <Col md={6}>
                            <Form.Group className="mb-3" controlId="passaporte">
                                <Form.Label>Passaporte {!isBrasil && ' *'}</Form.Label>
                                <Form.Control
                                    type="text"
                                    name="passaporte"
                                    value={formData.passaporte}
                                    onChange={handleChange}
                                    required={!isBrasil}
                                    disabled={isBrasil}
                                    key={isBrasil ? 'pass-br' : 'pass-other'}
                                />
                            </Form.Group>
                        </Col>
                    </Row>

                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={handleClose} disabled={isSaving}>
                        Cancelar
                    </Button>
                    <Button variant="success" type="submit" disabled={isSaving} style={{ backgroundColor: '#26522c' }}>
                        {isSaving ? <Spinner as="span" animation="border" size="sm" /> : (isEditMode ? 'Salvar Alterações' : 'Salvar Cliente')}
                    </Button>
                </Modal.Footer>
            </Form>
        </Modal>
    );
}

export default ClienteModal;
