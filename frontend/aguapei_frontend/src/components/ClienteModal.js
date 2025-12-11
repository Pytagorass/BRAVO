/**
 * ClienteModal.js
 * ----------------
 * Formulário reutilizado para criar ou editar hóspedes (clientes).
 * Utilizado tanto na página de Clientes quanto pelo modal de reservas.
 * O componente aplica máscaras básicas (telefone/CPF/passaporte) e envia
 * os dados para os endpoints `createHospede` / `updateHospede`.
 */
import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Alert, Col, Row, Spinner } from 'react-bootstrap';
import { createHospede, updateHospede } from '../services/api';
import { toast } from 'react-toastify';

// ---------------------------
// Helpers de formatação/máscara
// ---------------------------

// Remove caracteres não numéricos, evitando persistir dados inválidos no backend.
const digitsOnly = (value = '') => value.replace(/\D/g, '');
const MAX_PHONE_LENGTH = 15;

// Valida CPF localmente (mesma lógica aplicada no backend) para dar feedback imediato ao usuário.
const isValidCPF = (value = '') => {
    const digits = digitsOnly(value);
    if (digits.length !== 11 || /^(\d)\1+$/.test(digits)) return false;

    const calculateDigit = (sliceLength) => {
        const total = digits
            .slice(0, sliceLength)
            .split('')
            .reduce((acc, curr, index) => acc + Number(curr) * (sliceLength + 1 - index), 0);
        const rest = (total * 10) % 11;
        return rest === 10 ? 0 : rest;
    };

    return (
        calculateDigit(9) === Number(digits[9]) &&
        calculateDigit(10) === Number(digits[10])
    );
};

// Formata CPF conforme padrão brasileiro sem alterar o valor bruto enviado ao servidor.
const formatCpf = (value = '') => {
    const digits = digitsOnly(value).slice(0, 11);
    if (!digits) return '';
    let formatted = digits;
    formatted = formatted.replace(/(\d{3})(\d)/, '$1.$2');
    formatted = formatted.replace(/(\d{3})(\d)/, '$1.$2');
    formatted = formatted.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
    return formatted;
};

const formatTelefone = (value = '', pais = 'Brasil') => {
    const digits = digitsOnly(value);
    if (!digits) return '';

    if (pais === 'Brasil') {
        let local = digits;
        if (local.startsWith('55') && local.length > 11) {
            local = local.slice(2);
        }
        const ddi = '+55';
        const ddd = local.slice(0, 2);
        const parte1 = local.slice(2, 7);
        const parte2 = local.slice(7, 11);

        let formatted = ddi;
        if (ddd) {
            formatted += ` (${ddd}`;
            if (ddd.length === 2) {
                formatted += ')';
            }
        }
        if (parte1) {
            formatted += ` ${parte1}`;
        }
        if (parte2) {
            formatted += `-${parte2}`;
        }
        return formatted.trim();
    }

    return `+${digits}`;
};

// Normaliza o passaporte para maiúsculas no limite de 20 caracteres.
const sanitizePassport = (value = '') =>
    value.toUpperCase().replace(/\s+/g, '').slice(0, 20);

/**
 * Modal de cadastro/edição de hóspedes.
 *
 * Objetivo:
 *   - Centralizar a criação e edição de registros da tabela `hospede`.
 * Parâmetros:
 *   - show: controla exibição.
 *   - handleClose: finaliza o modal e reseta estados externos.
 *   - onSaveSuccess: notifica o componente pai com o objeto retornado do backend.
 *   - cliente: quando definido, carrega o formulário para edição.
 * Fluxo:
 *   1. Carrega dados existentes (se houver) e aplica máscaras.
 *   2. Monta payload compatível com `createHospede`/`updateHospede`.
 *   3. Exibe toasts de sucesso ou mensagens de erro retornadas pela API.
 * Impacto no banco:
 *   - Dispara INSERT ou UPDATE na tabela `hospede` via endpoints Django.
 */
function ClienteModal({ show, handleClose, onSaveSuccess, cliente }) {
    /**
     * Retorna o shape padrão do formulário.
     * Não recebe parâmetros e devolve o objeto base para o hook `useState`.
     * Mantém o componente consistente entre criação e edição.
     */
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
        // Ao abrir o modal, sincroniza o formulário com os dados atuais do hóspede;
        // se não houver hóspede selecionado, restaura o estado inicial.
        if (isEditMode && cliente) {
            setFormData({
                nome_hospede: cliente.nome_hospede || '',
                telefone: digitsOnly(cliente.telefone || ''),
                email_hospede: cliente.email_hospede || '',
                pais_origem: cliente.pais_origem || 'Brasil',
                passaporte: sanitizePassport(cliente.passaporte || ''),
                cpf: digitsOnly(cliente.cpf || '')
            });
        } else {
            setFormData(getInitialState());
        }
        setError(null);
    }, [cliente, isEditMode, show]);

    /**
     * Atualiza o estado do formulário garantindo que os campos sigam
     * as regras de validação do backend:
     *  - Telefones e CPFs contêm somente dígitos.
     *  - O documento incompatível com o país selecionado é limpo.
     * Não retorna valores; apenas atualiza `formData`.
     */
    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => {
            const newState = { ...prev };

            if (name === 'telefone') {
                newState.telefone = digitsOnly(value).slice(0, MAX_PHONE_LENGTH);
            } else if (name === 'cpf') {
                newState.cpf = digitsOnly(value).slice(0, 11);
            } else if (name === 'passaporte') {
                newState.passaporte = sanitizePassport(value);
            } else {
                newState[name] = value;
            }

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

    //  4. HandleSubmit
    /**
     * Submit do formulário.
     * Fluxo:
     *  1. Normaliza telefone/CPF/passaporte (conforme país).
     *  2. Dispara `updateHospede` ou `createHospede`.
     *  3. Em caso de sucesso, fecha o modal e atualiza lista via `onSaveSuccess`.
     *  4. Exibe mensagens de erro retornadas pelo backend.
     */
    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSaving(true);
        setError(null);

        try {
            const payload = {
                ...formData,
                telefone: formData.telefone || '',
                cpf: formData.cpf || '',
                passaporte: formData.passaporte || ''
            };

            if (formData.pais_origem === 'Brasil') {
                if (!isValidCPF(formData.cpf)) {
                    setError('Informe um CPF válido.');
                    setIsSaving(false);
                    return;
                }
                payload.passaporte = '';
                if (payload.telefone && !payload.telefone.startsWith('55')) {
                    payload.telefone = `55${payload.telefone}`;
                }
            } else {
                payload.cpf = '';
            }

            let savedCliente;

            if (isEditMode) {
                savedCliente = await updateHospede(cliente.id_hospede, payload);
                toast.success('Cliente atualizado com sucesso!');
            } else {
                savedCliente = await createHospede(payload);
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

                    {/*  7. O Alert Inline exibe a 'message' da API */}
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

                    {/* Linha 2: País (com lógica de seleção) */}
                    <Form.Group className="mb-3" controlId="pais_origem">
                        <Form.Label>País</Form.Label>
                        <Form.Select //  <Form.Select> é a tag correta no Bootstrap 5
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

                    {/* Linha 3: Telefone e E-mail */}
                    <Row>
                        <Col md={6}>
                            <Form.Group className="mb-3" controlId="telefone">
                                <Form.Label>Telefone</Form.Label>
                                <Form.Control
                                    type="text"
                                    name="telefone"
                                    value={formatTelefone(formData.telefone, formData.pais_origem)}
                                    onChange={handleChange}
                                    inputMode="tel"
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

                    {/* Linha 4: CPF e Passaporte (lógica condicional mantida) */}
                    <Row>
                        <Col md={6}>
                            <Form.Group className="mb-3" controlId="cpf">
                                <Form.Label>CPF (Único){isBrasil && ' *'}</Form.Label>
                                <Form.Control
                                    type="text"
                                    name="cpf"
                                    value={isBrasil ? formatCpf(formData.cpf) : formData.cpf}
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
