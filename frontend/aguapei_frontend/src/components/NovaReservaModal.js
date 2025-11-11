import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Alert, Spinner, Row, Col, InputGroup } from 'react-bootstrap';
import apiClient from '../services/api';
import ClienteModal from './ClienteModal'; // Importa o modal de cliente
import './NovaReservaModal.css'; // Para estilizar o "Valor Total"

// Limite de pessoas (1 Titular + 2 Acompanhantes)
const MAX_ACOMPANHANTES = 2;

// --- MUDANÇA 1: Definir as opções de pagamento ---
// Estas opções vêm do seu ENUM 'pagamento' no banco de dados
const PAGAMENTO_CHOICES = [
    { value: 'Pendente', label: 'Pendente' },
    { value: 'Pago', label: 'Pago' },
    { value: 'Em Partes', label: 'Em Partes' },
    { value: 'Cancelado', label: 'Cancelado' },
];
// --- FIM DA MUDANÇA 1 ---

function NovaReservaModal({ show, handleClose, onSaveSuccess }) {
    // Estados do formulário
    const [formData, setFormData] = useState({
        titularId: '',
        quartoId: '',
        checkin: '',
        checkout: '',
        valor_total: 0,
        // --- MUDANÇA 2: Definir 'Pendente' como valor padrão ---
        forma_pagamento: 'Pendente',
        observacao_reserva: ''
    });
    // Armazena os IDs dos acompanhantes
    const [acompanhantes, setAcompanhantes] = useState([]); 

    // Estados de controle
    const [hospedes, setHospedes] = useState([]);
    const [quartos, setQuartos] = useState([]);
    const [loading, setLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState(null);
    
    // Controla a visibilidade do modal de "Novo Cliente"
    const [showClienteModal, setShowClienteModal] = useState(false);

    // Efeito para buscar dados quando o modal abre
    const fetchModalData = async () => {
        setLoading(true);
        setError(null);
        try {
            const [hospedesRes, quartosRes] = await Promise.all([
                apiClient.get('/hospedes/'),
                apiClient.get('/quartos/')
            ]);
            setHospedes(hospedesRes.data);
            setQuartos(quartosRes.data);
        } catch (err) {
            setError('Falha ao carregar dados. Tente fechar e abrir o modal.');
        } finally {
            setLoading(false);
        }
    };
    
    useEffect(() => {
        if (show) {
            fetchModalData();
        } else {
            // Limpa o formulário quando o modal é fechado
            setFormData({
                titularId: '', quartoId: '', checkin: '', checkout: '',
                valor_total: 0, 
                // --- MUDANÇA 3: Resetar para 'Pendente' ---
                forma_pagamento: 'Pendente',
                observacao_reserva: ''
            });
            setAcompanhantes([]); // Limpa acompanhantes
            setError(null);
        }
    }, [show]);

    // Efeito para calcular o valor total
    useEffect(() => {
        if (formData.checkin && formData.checkout && formData.quartoId) {
            const selectedQuarto = quartos.find(q => q.id_quarto === parseInt(formData.quartoId));
            if (selectedQuarto) {
                const date1 = new Date(formData.checkin);
                const date2 = new Date(formData.checkout);
                const diffTime = Math.abs(date2 - date1);
                // Calcula a diferença em dias. Adiciona 1 para incluir o dia do check-in.
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 
                
                if (diffDays > 0) {
                    const total = diffDays * selectedQuarto.valor_diaria;
                    setFormData(prev => ({ ...prev, valor_total: total }));
                } else {
                    // Se checkin e checkout forem no mesmo dia, cobra 1 diária
                    const total = selectedQuarto.valor_diaria;
                     setFormData(prev => ({ ...prev, valor_total: total > 0 ? total : 0 }));
                }
            }
        }
    }, [formData.checkin, formData.checkout, formData.quartoId, quartos]);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    // Funções para gerenciar acompanhantes
    const handleAcompanhanteChange = (index, value) => {
        const novosAcompanhantes = [...acompanhantes];
        novosAcompanhantes[index] = value;
        setAcompanhantes(novosAcompanhantes);
    };

    const handleAddAcompanhante = () => {
        if (acompanhantes.length < MAX_ACOMPANHANTES) {
            setAcompanhantes([...acompanhantes, '']); // Adiciona um slot vazio
        }
    };

    const handleRemoveAcompanhante = (index) => {
        setAcompanhantes(acompanhantes.filter((_, i) => i !== index));
    };

    // Callback para quando um novo cliente é salvo
    const handleClienteSaveSuccess = (newCliente) => {
        setShowClienteModal(false); // Fecha o modal de cliente
        fetchModalData(); // Recarrega a lista de hóspedes
        // Auto-seleciona o cliente recém-criado como titular
        setFormData(prev => ({...prev, titularId: newCliente.id_hospede})); 
    };

    const handleCloseInternal = () => {
        setIsSaving(false);
        handleClose();
    };

    const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setError(null);

    // Filtra IDs vazios (ex: "Selecione...")
    const acompanhanteIds = acompanhantes.filter(id => id); 

    // Prepara o payload para a API (sem mudanças aqui)
    const payload = {
        fk_hospede_id_hospede: formData.titularId,
        quartos: [formData.quartoId], 
        checkin: formData.checkin,
        checkout: formData.checkout,
        valor_total: formData.valor_total,
        forma_pagamento: formData.forma_pagamento,
        observacao_reserva: formData.observacao_reserva,
        acompanhantes: acompanhanteIds
    };

    try {
        // --- MUDANÇA: Capturamos a resposta da API ---
        const response = await apiClient.post('/reservas/', payload);
        
        // 'response.data' agora é o nosso 'nova_reserva_obj' do Django
        onSaveSuccess(response.data); // <-- PASSAMOS o novo objeto para o pai
        
        handleCloseInternal(); // Fecha o modal
    
    } catch (err) {
        // ... (o resto da sua lógica de 'catch' continua igual) ...
        const errorData = err.response ? err.response.data : null;
        let errorMsg = 'Ocorreu um erro ao salvar.';
        
        // Se for erro de Overbooking, mostramos a mensagem do back-end
        if (err.response && err.response.data && err.response.data.detail) {
             errorMsg = err.response.data.detail;
        } 
        // Lógica de erro genérico
        else if (errorData) {
            let messages = [];
            for (const key in errorData) {
                const value = errorData[key];
                if (Array.isArray(value)) {
                    messages.push(`${key}: ${value.join(', ')}`);
                } else {
                    messages.push(`${key}: ${String(value)}`);
                }
            }
            errorMsg = messages.join(' | ');
        }
        
        setError(errorMsg);
    } finally {
        setIsSaving(false);
    }
};
    // Lista de hóspedes disponíveis (não inclui o titular já selecionado)
    const hospedesDisponiveis = hospedes.filter(
        h => h.id_hospede !== parseInt(formData.titularId)
    );

    return (
        <>
            <Modal show={show} onHide={handleCloseInternal} size="lg">
                <Form onSubmit={handleSubmit}>
                    <Modal.Header closeButton>
                        <Modal.Title style={{ color: '#26522c' }}>Nova Reserva</Modal.Title>
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
                                    <Form.Group as={Col} controlId="formTitular">
                                        <Form.Label>Titular da Reserva*</Form.Label>
                                        <InputGroup>
                                            <Form.Select name="titularId" value={formData.titularId} onChange={handleChange} required>
                                                <option value="">Selecione um hóspede</option>
                                                {hospedes.map(h => (
                                                    <option key={h.id_hospede} value={h.id_hospede}>
                                                        {h.nome_hospede}
                                                    </option>
                                                ))}
                                            </Form.Select>
                                            {/* Botão "+ Novo" para abrir o modal de cliente */}
                                            <Button variant="outline-success" onClick={() => setShowClienteModal(true)}>
                                                + Novo
                                            </Button>
                                        </InputGroup>
                                    </Form.Group>
                                    <Form.Group as={Col} controlId="formQuarto">
                                        <Form.Label>Quarto*</Form.Label>
                                        <Form.Select name="quartoId" value={formData.quartoId} onChange={handleChange} required>
                                            <option value="">Selecione um quarto</option>
                                            {quartos.map(q => (
                                                <option key={q.id_quarto} value={q.id_quarto}>
                                                    {q.numero} ({q.tipo_quarto}) - R$ {q.valor_diaria}
                                                </option>
                                            ))}
                                        </Form.Select>
                                    </Form.Group>
                                </Row>

                                {/* Campos de Acompanhantes Dinâmicos */}
                                {acompanhantes.map((acompId, index) => (
                                    <Form.Group key={index} className="mb-3" controlId={`formAcompanhante${index}`}>
                                        <Form.Label>Acompanhante {index + 1}</Form.Label>
                                        <InputGroup>
                                            <Form.Select
                                                value={acompId}
                                                onChange={(e) => handleAcompanhanteChange(index, e.target.value)}
                                            >
                                                <option value="">Selecione um acompanhante</option>
                                                {hospedesDisponiveis.map(h => (
                                                    <option key={h.id_hospede} value={h.id_hospede}>
                                                        {h.nome_hospede}
                                                    </option>
                                                ))}
                                            </Form.Select>
                                            <Button variant="outline-danger" onClick={() => handleRemoveAcompanhante(index)}>
                                                &times;
                                            </Button>
                                        </InputGroup>
                                    </Form.Group>
                                ))}

                                {acompanhantes.length < MAX_ACOMPANHANTES && (
                                    <Button variant="link" onClick={handleAddAcompanhante} className="p-0 mb-3">
                                        + Adicionar Acompanhante
                                    </Button>
                                )}
                                {/* Fim dos Campos de Acompanhantes */}

                                <Row className="mb-3">
                                    <Form.Group as={Col} controlId="formCheckin">
                                        <Form.Label>Check-in*</Form.Label>
                                        <Form.Control type="date" name="checkin" value={formData.checkin} onChange={handleChange} required />
                                    </Form.Group>
                                    <Form.Group as={Col} controlId="formCheckout">
                                        <Form.Label>Check-out*</Form.Label>
                                        <Form.Control type="date" name="checkout" value={formData.checkout} onChange={handleChange} required />
                                    </Form.Group>
                                </Row>
                                
                                <div className="valor-total-container">
                                    <h3>
                                        Valor Total:
                                        <span className="valor-total-preco">
                                            R$ {parseFloat(formData.valor_total).toFixed(2).replace('.', ',')}
                                        </span>
                                    </h3>
                                </div>
                                
                                <hr />

                                <Row>
                                    {/* --- MUDANÇA 4: Substituir Form.Control por Form.Select --- */}
                                    <Form.Group as={Col} controlId="formFormaPagamento">
                                        <Form.Label>Forma de Pagamento</Form.Label>
                                        <Form.Select 
                                            name="forma_pagamento" 
                                            value={formData.forma_pagamento} 
                                            onChange={handleChange}
                                        >
                                            {PAGAMENTO_CHOICES.map(opt => (
                                                <option key={opt.value} value={opt.value}>
                                                    {opt.label}
                                                </option>
                                            ))}
                                        </Form.Select>
                                    </Form.Group>
                                    {/* --- FIM DA MUDANÇA 4 --- */}
                                </Row>

                                <Form.Group controlId="formObservacao" className="mt-3">
                                    <Form.Label>Observações</Form.Label>
                                    <Form.Control as="textarea" rows={3} name="observacao_reserva" value={formData.observacao_reserva} onChange={handleChange} />
                                </Form.Group>
                            </>
                        )}
                    </Modal.Body>

                    <Modal.Footer>
                        <Button variant="secondary" onClick={handleCloseInternal}>
                            Cancelar
                        </Button>
                        <Button 
                            variant="success" 
                            type="submit" 
                            style={{ backgroundColor: '#26522c', border: 'none' }} 
                            disabled={isSaving || loading}
                        >
                            {isSaving ? <Spinner as="span" animation="border" size="sm" /> : 'Salvar Reserva'}
                        </Button>
                    </Modal.Footer>
                </Form>
            </Modal>

            {/* Renderiza o Modal de Cliente (que está no canvas) */}
            <ClienteModal 
                show={showClienteModal}
                handleClose={() => setShowClienteModal(false)}
                onSaveSuccess={handleClienteSaveSuccess}
                cliente={null} // Sempre abre em modo "Novo Cliente"
            />
        </>
    );
}

export default NovaReservaModal;




