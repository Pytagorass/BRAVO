import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Alert, Col, Row, Spinner } from 'react-bootstrap';
import apiClient from '../services/api';

// Recebe props para funcionar:
// show: (boolean) se o modal deve ser exibido
// handleClose: (função) para fechar o modal
// onSaveSuccess: (função) para avisar a página principal que um cliente foi salvo (para atualizar a lista)
// cliente: (objeto) o cliente para editar, ou 'null' se for para criar um novo
function ClienteModal({ show, handleClose, onSaveSuccess, cliente }) {
    
    // Estado inicial do formulário
    const getInitialState = () => ({
        nome_hospede: '',
        telefone: '',
        email_hospede: '',
        pais_origem: 'Brasil', // Default 'Brasil' como no protótipo [cite: 928-930]
        passaporte: '',
        cpf: ''
    });

    const [formData, setFormData] = useState(getInitialState());
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState(null);

    // Determina se estamos no modo de edição
    const isEditMode = cliente !== null;
    
    // Lógica do protótipo (página 27-28) [cite: 928-933]
    const isBrasil = formData.pais_origem === 'Brasil';

    // Efeito para preencher o formulário quando um cliente é passado para edição
    useEffect(() => {
        if (isEditMode) {
            // Se estamos editando, preenche o formulário com os dados do cliente
            setFormData({
                nome_hospede: cliente.nome_hospede || '',
                telefone: cliente.telefone || '',
                email_hospede: cliente.email_hospede || '',
                pais_origem: cliente.pais_origem || '',
                passaporte: cliente.passaporte || '',
                cpf: cliente.cpf || ''
            });
        } else {
            // Se estamos criando, reseta o formulário
            setFormData(getInitialState());
        }
        setError(null); // Limpa erros ao abrir o modal
    }, [cliente, isEditMode, show]); // Roda sempre que o 'cliente' ou 'show' mudar

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSaving(true);
        setError(null);

        try {
            if (isEditMode) {
                // Modo Edição (PUT)
                await apiClient.put(`/hospedes/${cliente.id_hospede}/`, formData);
            } else {
                // Modo Criação (POST)
                await apiClient.post('/hospedes/', formData);
            }
            onSaveSuccess(); // Avisa a página principal para recarregar a lista
            handleClose();   // Fecha o modal
        } catch (err) {
            console.error(err.response.data);
            // Captura erros de validação do Django (ex: e-mail duplicado)
            const errorData = err.response.data;
            let errorMsg = 'Ocorreu um erro ao salvar.';
            if (errorData) {
                // Transforma os erros do Django em uma string
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
        <Modal show={show} onHide={handleClose} backdrop="static" size="lg">
            <Modal.Header closeButton>
                <Modal.Title style={{ color: '#26522c' }}>
                    {isEditMode ? 'Editar Cliente' : 'Novo Cliente'}
                </Modal.Title>
            </Modal.Header>
            <Form onSubmit={handleSubmit}>
                <Modal.Body>
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
                                />
                            </Form.Group>
                        </Col>
                    </Row>

                    {/* Linha 3: País (com lógica de seleção) */}
                    <Form.Group className="mb-3" controlId="pais_origem">
                        <Form.Label>País</Form.Label>
                        <Form.Control
                            as="select"
                            name="pais_origem"
                            value={formData.pais_origem}
                            onChange={handleChange}
                        >
                            {/* Adicione mais países se necessário */}
                            <option value="Brasil">Brasil</option>
                            <option value="Argentina">Argentina</option>
                            <option value="Estados Unidos">Estados Unidos</option>
                            <option value="Itália">Itália</option>
                            <option value="Alemanha">Alemanha</option>
                            <option value="Outro">Outro</option>
                        </Form.Control>
                    </Form.Group>

                    {/* Linha 4: CPF e Passaporte (com lógica condicional) */}
                    <Row>
                        <Col md={6}>
                            <Form.Group className="mb-3" controlId="cpf">
                                <Form.Label>CPF (Único){isBrasil && ' *'}</Form.Label>
                                <Form.Control
                                    type="text"
                                    name="cpf"
                                    value={formData.cpf}
                                    onChange={handleChange}
                                    required={isBrasil} // Obrigatório se for Brasil [cite: 928-930]
                                    disabled={!isBrasil} // Desabilitado se não for Brasil
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
                                    required={!isBrasil} // Obrigatório se NÃO for Brasil [cite: 931-933]
                                    disabled={isBrasil}  // Desabilitado se for Brasil
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
