// src/pages/ClientesPage.js
import React, { useState, useEffect, useCallback } from 'react';
import { Spinner, Alert, Button, ButtonGroup } from 'react-bootstrap';
import { toast } from 'react-toastify';

import { fetchHospedes, deleteHospede, updateHospedeStatus } from '../services/api';
import ClienteModal from '../components/ClienteModal';
import ConfirmacaoModal from '../components/ConfirmacaoModal';
import './ClientesPage.css';

const ClientesPage = () => {
  const [clientes, setClientes] = useState([]);
  const [viewStatus, setViewStatus] = useState('Ativo');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showClienteModal, setShowClienteModal] = useState(false);
  const [clienteSelecionado, setClienteSelecionado] = useState(null);

  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [clienteParaInativar, setClienteParaInativar] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // 🔄 Carregar clientes conforme o status atual (Ativo / Inativo)
  const carregarClientes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchHospedes(viewStatus);
      setClientes(data);
    } catch (err) {
      setError(err.message || 'Falha ao carregar a lista de clientes.');
    } finally {
      setLoading(false);
    }
  }, [viewStatus]);

  useEffect(() => {
    carregarClientes();
  }, [carregarClientes]);

  // 🧩 Ações de modal
  const handleShowNovoCliente = () => {
    setClienteSelecionado(null);
    setShowClienteModal(true);
  };

  const handleShowEditarCliente = (cliente) => {
    setClienteSelecionado(cliente);
    setShowClienteModal(true);
  };

  const handleSaveSuccess = (clienteSalvo) => {
    setShowClienteModal(false);
    setClientes((prev) => {
      const existe = prev.find((c) => c.id_hospede === clienteSalvo.id_hospede);
      return existe
        ? prev.map((c) => (c.id_hospede === clienteSalvo.id_hospede ? clienteSalvo : c))
        : [clienteSalvo, ...prev];
    });
    toast.success('Cliente salvo com sucesso!');
  };

  // 🚫 Inativar cliente (soft delete)
  const handleShowInativar = (cliente) => {
    setClienteParaInativar(cliente);
    setShowConfirmModal(true);
  };

  const handleConfirmInativar = async () => {
    if (!clienteParaInativar) return;
    setIsDeleting(true);
    try {
      await deleteHospede(clienteParaInativar.id_hospede);
      setClientes((prev) =>
        prev.filter((c) => c.id_hospede !== clienteParaInativar.id_hospede)
      );
      toast.success(`Cliente "${clienteParaInativar.nome_hospede}" inativado com sucesso.`);
    } catch (err) {
      toast.error(err.message || 'Erro ao inativar cliente.');
    } finally {
      setIsDeleting(false);
      setShowConfirmModal(false);
      setClienteParaInativar(null);
    }
  };

  // ✅ Reativar cliente
  const handleReativar = async (cliente) => {
    const toastId = toast.loading(`Reativando ${cliente.nome_hospede}...`);
    try {
      await updateHospedeStatus(cliente.id_hospede, 'Ativo');
      setClientes((prev) =>
        prev.filter((c) => c.id_hospede !== cliente.id_hospede)
      );
      toast.update(toastId, {
        render: `${cliente.nome_hospede} reativado com sucesso!`,
        type: 'success',
        isLoading: false,
        autoClose: 3000,
      });
    } catch (err) {
      toast.update(toastId, {
        render: err.message || 'Erro ao reativar cliente.',
        type: 'error',
        isLoading: false,
        autoClose: 5000,
      });
    }
  };

  // 📋 Conteúdo da tabela
  const renderContent = () => {
    if (loading && clientes.length === 0) {
      return (
        <div className="text-center p-5">
          <Spinner animation="border" variant="success" />
          <p>Carregando clientes {viewStatus.toLowerCase()}s...</p>
        </div>
      );
    }

    if (error) {
      return (
        <Alert variant="danger" className="text-center">
          {error}
        </Alert>
      );
    }

    if (clientes.length === 0 && !loading) {
      return (
        <div className="text-center p-5">
          Nenhum cliente {viewStatus.toLowerCase()} encontrado.
        </div>
      );
    }

    return (
      <div className="table-responsive">
        <table className="table table-striped table-hover align-middle">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Contato</th>
              <th>País</th>
              <th>Documento</th>
              <th style={{ width: '150px' }}>Ações</th>
            </tr>
          </thead>
          <tbody>
            {clientes.map((cliente) => (
              <tr key={cliente.id_hospede}>
                <td>{cliente.nome_hospede}</td>
                <td>
                  {cliente.email_hospede || 'Sem email'}
                  <br />
                  <small className="text-muted">
                    {cliente.telefone || 'Sem telefone'}
                  </small>
                </td>
                <td>{cliente.pais_origem}</td>
                <td>
                  {cliente.pais_origem === 'Brasil'
                    ? `CPF: ${cliente.cpf || 'N/A'}`
                    : `Pass: ${cliente.passaporte || 'N/A'}`}
                </td>
                <td>
                  {viewStatus === 'Ativo' ? (
                    <>
                      <Button
                        size="sm"
                        variant="outline-secondary"
                        onClick={() => handleShowEditarCliente(cliente)}
                      >
                        Editar
                      </Button>
                      <Button
                        size="sm"
                        variant="outline-danger"
                        className="ms-2"
                        onClick={() => handleShowInativar(cliente)}
                      >
                        Inativar
                      </Button>
                    </>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline-success"
                      onClick={() => handleReativar(cliente)}
                    >
                      Reativar
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="clientes-page">
      <div className="page-header">
        <h1>Gerenciamento de Clientes</h1>
        <div>
          <ButtonGroup className="me-2">
            <Button
              variant={viewStatus === 'Ativo' ? 'success' : 'outline-secondary'}
              onClick={() => setViewStatus('Ativo')}
              style={
                viewStatus === 'Ativo'
                  ? { backgroundColor: '#26522c', borderColor: '#26522c' }
                  : {}
              }
            >
              Ativos
            </Button>
            <Button
              variant={viewStatus === 'Inativo' ? 'danger' : 'outline-secondary'}
              onClick={() => setViewStatus('Inativo')}
            >
              Inativos
            </Button>
          </ButtonGroup>

          <Button
            variant="primary"
            style={{ backgroundColor: '#26522c', borderColor: '#26522c' }}
            onClick={handleShowNovoCliente}
            disabled={viewStatus === 'Inativo'}
          >
            + Novo Cliente
          </Button>
        </div>
      </div>

      <div className="page-content">{renderContent()}</div>

      <ClienteModal
        show={showClienteModal}
        handleClose={() => setShowClienteModal(false)}
        onSaveSuccess={handleSaveSuccess}
        cliente={clienteSelecionado}
      />

      {clienteParaInativar && (
        <ConfirmacaoModal
          show={showConfirmModal}
          handleClose={() => setShowConfirmModal(false)}
          handleConfirm={handleConfirmInativar}
          loading={isDeleting}
          title="Confirmar Inativação"
          body={`Tem certeza que deseja INATIVAR o cliente "${clienteParaInativar.nome_hospede}"? Ele não poderá ser selecionado para novas reservas.`}
          confirmText="Sim, Inativar"
          confirmVariant="danger"
        />
      )}
    </div>
  );
};

export default ClientesPage;
