import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Alert, Col, Row, Spinner } from 'react-bootstrap';
// 🎓 1. Importamos as funções de API específicas e o 'toast'
import { createHospede, updateHospede } from '../services/api';
import { toast } from 'react-toastify';

function ClienteModal({ show, handleClose, onSaveSuccess, cliente }) {
    
    // Estado inicial do formulário
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
    
    // 🎓 2. O 'error' agora vai receber a MENSAGEM de erro da nossa API padronizada
    const [error, setError] = useState(null); 

    const isEditMode = cliente !== null;
    const isBrasil = formData.pais_origem === 'Brasil';

    // Efeito para preencher o formulário (Lógica original mantida, está correta)
    useEffect(() => {
        if (isEditMode) {
            setFormData({
                nome_hospede: cliente.nome_hospede || '',
                telefone: cliente.telefone || '',
                email_hospede: cliente.email_hospede || '',
                pais_origem: cliente.pais_origem || 'Brasil', // Garante 'Brasil' se for nulo
                passaporte: cliente.passaporte || '',
                cpf: cliente.cpf || ''
            });
        } else {
            setFormData(getInitialState());
        }
        setError(null); // Limpa erros ao abrir/trocar o modal
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
            let response;
            
            if (isEditMode) {
                // Modo Edição (PUT)
                // A API (views.py) retorna { status: 'ok', data: {hospede_atualizado} }
                response = await updateHospede(cliente.id_hospede, formData);
                toast.success('Cliente atualizado com sucesso!');
            } else {
                // Modo Criação (POST)
                // A API (views.py) retorna { status: 'ok', data: {novo_hospede} }
                response = await createHospede(formData);
                toast.success('Novo cliente salvo com sucesso!');
            }
            
            // 🎓 5. ATUALIZAÇÃO EFICIENTE
            //    Passamos o objeto (response.data) para o pai.
            //    O pai pode agora atualizar o estado da lista *sem*
            //    fazer um novo fetch de todos os clientes.
            onSaveSuccess(response.data); 
            handleClose();    // Fecha o modal
            
        } catch (errorData) {
            // 🎓 6. TRATAMENTO DE ERRO PADRONIZADO
            //    'errorData' já é o objeto JSON de erro (ex: { status, code, message })
            //    graças ao interceptor do 'apiClient' (services/api.js).
            
            console.error("Erro ao salvar:", errorData);

            if (errorData.code === 'VALIDATION_ERROR') {
                // Ex: "CPF é obrigatório para hóspedes do Brasil."
                setError(errorData.message);
            } 
            else if (errorData.code === 'CONFLICT') {
                // Ex: "Este e-mail já está em uso."
                setError(errorData.message);
            } 
            else if (errorData.message) {
                // Outros erros da API (ex: FK_CONSTRAINT, DB_INTEGRITY_ERROR)
                setError(errorData.message);
            }
            else {
                // Fallback para erros de rede (que o interceptor já deve ter tratado com toast)
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