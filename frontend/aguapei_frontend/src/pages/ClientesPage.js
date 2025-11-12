// frontend/src/pages/ClientesPage.js

import React, { useState, useEffect, useCallback } from 'react';
import { fetchHospedes, deleteHospede, updateHospedeStatus } from '../services/api';
import { toast } from 'react-toastify';
import { Spinner, Alert, Button, ButtonGroup, Pagination } from 'react-bootstrap';
import ClienteModal from '../components/ClienteModal';
import ConfirmacaoModal from '../components/ConfirmacaoModal';

import './ClientesPage.css';

const CLIENTES_PER_PAGE = 10;

const ClientesPage = () => {
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewStatus, setViewStatus] = useState('Ativo');

  // Paginação
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const totalPages = Math.ceil(totalCount / CLIENTES_PER_PAGE);

  // Modais
  const [showClienteModal, setShowClienteModal] = useState(false);
  const [clienteSelecionado, setClienteSelecionado] = useState(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [clienteParaInativar, setClienteParaInativar] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Carrega clientes com paginação e status
  const carregarClientes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchHospedes(viewStatus, currentPage, CLIENTES_PER_PAGE);
      setClientes(data.hospedes);
      setTotalCount(data.total_count);
    } catch (err) {
      setError(err.message || 'Falha ao carregar a lista de clientes.');
    } finally {
      setLoading(false);
    }
  }, [viewStatus, currentPage]);

  useEffect(() => {
    carregarClientes();
  }, [carregarClientes]);

  // Modais
  const handleShowNovoCliente = () => {
    setClienteSelecionado(null);
    setShowClienteModal(true);
  };

  const handleShowEditarCliente = (cliente) => {
    setClienteSelecionado(cliente);
    setShowClienteModal(true);
  };

  const handleSaveSuccess = () => {
    setShowClienteModal(false);
    carregarClientes();
  };

  const handleShowInativar = (cliente) => {
    setClienteParaInativar(cliente);
    setShowConfirmModal(true);
  };

  const handleConfirmInativar = async () => {
    if (!clienteParaInativar) return;
    setIsDeleting(true);
    try {
      await deleteHospede(clienteParaInativar.id_hospede);
      toast.success(`Cliente "${clienteParaInativar.nome_hospede}" inativado com sucesso.`);
      setShowConfirmModal(false);
      setClienteParaInativar(null);

      if (clientes.length === 1 && currentPage > 1) {
        setCurrentPage(currentPage - 1);
      } else {
        carregarClientes();
      }
    } catch (err) {
      toast.error(err.message || "Erro ao inativar cliente.");
      setIsDeleting(false);
    }
  };

  const handleReativar = async (cliente) => {
    const toastId = toast.loading(`Reativando ${cliente.nome_hospede}...`);
    try {
      await updateHospedeStatus(cliente.id_hospede, 'Ativo');
      toast.update(toastId, {
        render: `${cliente.nome_hospede} reativado!`,
        type: "success",
        isLoading: false,
        autoClose: 3000
      });

      if (clientes.length === 1 && currentPage > 1) {
        setCurrentPage(currentPage - 1);
      } else {
        carregarClientes();
      }
    } catch (err) {
      toast.update(toastId, {
        render: err.message || "Erro ao reativar.",
        type: "error",
        isLoading: false,
        autoClose: 5000
      });
    }
  };

  // Paginação
  const renderPagination = () => {
    if (totalPages <= 1) return null;
    const items = [];
    for (let number = 1; number <= totalPages; number++) {
      items.push(
        <Pagination.Item
          key={number}
          active={number === currentPage}
          onClick={() => setCurrentPage(number)}
        >
          {number}
        </Pagination.Item>
      );
    }
    return (
      <Pagination>
        <Pagination.Prev
          onClick={() => setCurrentPage(p => p - 1)}
          disabled={currentPage === 1}
        />
        {items}
        <Pagination.Next
          onClick={() => setCurrentPage(p => p + 1)}
          disabled={currentPage === totalPages}
        />
      </Pagination>
    );
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="text-center p-5">
          <Spinner animation="border" variant="success" />
          <p>Carregando clientes {viewStatus.toLowerCase()}s...</p>
        </div>
      );
    }

    if (error) {
      return (
        <Alert variant="danger">
          <Alert.Heading>Erro ao Carregar Clientes</Alert.Heading>
          <p>{error}</p>
          <Button onClick={carregarClientes} variant="danger">Tentar Novamente</Button>
        </Alert>
      );
    }

    if (clientes.length === 0) {
      return <div className="text-center p-5">Nenhum cliente {viewStatus.toLowerCase()} encontrado.</div>;
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
            {clientes.map(cliente => (
              <tr key={cliente.id_hospede}>
                <td>{cliente.nome_hospede}</td>
                <td>
                  {cliente.email_hospede || 'Sem email'}<br />
                  <small className="text-muted">{cliente.telefone || 'Sem telefone'}</small>
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
                      <Button size="sm" variant="outline-secondary" onClick={() => handleShowEditarCliente(cliente)}>
                        Editar
                      </Button>
                      <Button size="sm" variant="outline-danger" className="ms-2" onClick={() => handleShowInativar(cliente)}>
                        Inativar
                      </Button>
                    </>
                  ) : (
                    <Button size="sm" variant="outline-success" onClick={() => handleReativar(cliente)}>
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
      <div className="page-header d-flex justify-content-between align-items-center">
        <h1>Gerenciamento de Clientes</h1>
      </div>
      <div className="page-actions mb-3"> 
        <ButtonGroup className="me-2">
          <Button
            variant={viewStatus === 'Ativo' ? "success" : "outline-secondary"}
            style={viewStatus === 'Ativo' ? { backgroundColor: '#26522c', borderColor: '#26522c' } : {}}
            onClick={() => { setViewStatus('Ativo'); setCurrentPage(1); }}
          >
            Ativos
          </Button>
          <Button
            variant={viewStatus === 'Inativo' ? "danger" : "outline-secondary"}
            onClick={() => { setViewStatus('Inativo'); setCurrentPage(1); }}
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

      <div className="page-content">
        {renderContent()}
      </div>

      <div className="d-flex justify-content-center">
        {renderPagination()}
      </div>

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
          body={`Tem certeza que deseja INATIVAR o cliente "${clienteParaInativar.nome_hospede}"?`}
          confirmText="Sim, Inativar"
          confirmVariant="danger"
        />
      )}
    </div>
  );
};

export default ClientesPage;
