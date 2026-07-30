/**
 * ClientesPage.js
 * ----------------
 * Tela responsável pelo CRUD de hóspedes. Permite filtrar por status,
 * buscar por nome/país, realizar paginação local e abrir modais de
 * cadastro/edição ou confirmação de inativação.
 */
// src/pages/ClientesPage.js
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Spinner, Alert, Button, ButtonGroup, Form, Pagination, InputGroup } from 'react-bootstrap';
import { toast } from 'react-toastify';
import { Edit2, Search, UserPlus, UserX, RotateCcw, X } from 'react-feather';

import { fetchHospedes, deleteHospede, updateHospedeStatus } from '../services/api';
import ClienteModal from '../components/ClienteModal';
import ConfirmacaoModal from '../components/ConfirmacaoModal';
import './ClientesPage.css';

/**
 * ClientesPage
 * ------------
 * Tela que consome os endpoints de hóspedes para listar, criar/editar,
 * inativar e reativar registros. Impacta o banco via `fetchHospedes`,
 * `deleteHospede` e `updateHospedeStatus`.
 */
const ClientesPage = () => {
  const [clientes, setClientes] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;
  const [viewStatus, setViewStatus] = useState('Ativo');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showClienteModal, setShowClienteModal] = useState(false);
  const [clienteSelecionado, setClienteSelecionado] = useState(null);

  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [clienteParaInativar, setClienteParaInativar] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  /**
   * Carrega clientes conforme o status selecionado.
   * Chama `fetchHospedes`, que executa a consulta no banco.
   */
  const carregarClientes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchHospedes(viewStatus);
      setClientes(data);
      setCurrentPage(1);
    } catch (err) {
      setError(err.message || 'Falha ao carregar a lista de clientes.');
    } finally {
      setLoading(false);
    }
  }, [viewStatus]);

  useEffect(() => {
    carregarClientes();
  }, [carregarClientes]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, viewStatus]);

  const handleShowNovoCliente = () => {
    setClienteSelecionado(null);
    setShowClienteModal(true);
  };

  const handleShowEditarCliente = (cliente) => {
    setClienteSelecionado(cliente);
    setShowClienteModal(true);
  };

  /**
   * Atualiza a lista quando o modal salva com sucesso.
   * O componente pai recebe o objeto retorno e atualiza em memória.
   */
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

  const handleShowInativar = (cliente) => {
    setClienteParaInativar(cliente);
    setShowConfirmModal(true);
  };

  /**
   * Confirma a inativação chamando `deleteHospede`.
   * No front, removemos o hóspede da listagem atual (status "Ativo").
   */
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

  /**
   * Reativa o cliente inativo, chamando PATCH no backend.
   * Remove o objeto da listagem de inativos para refletir a mudança.
   */
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

  /**
   * Filtra clientes no front por nome/país.
   * Retorna uma lista filtrada usada pela paginação local.
   */
  const clientesFiltrados = useMemo(() => {
    const termo = searchTerm.trim().toLowerCase();
    if (!termo) return clientes;
    return clientes.filter((cliente) => {
      const nome = (cliente.nome_hospede || '').toLowerCase();
      const pais = (cliente.pais_origem || '').toLowerCase();
      return nome.includes(termo) || pais.includes(termo);
    });
  }, [clientes, searchTerm]);

  const totalPages = Math.max(1, Math.ceil(clientesFiltrados.length / ITEMS_PER_PAGE));
  const paginaAtual = Math.min(currentPage, totalPages);
  const inicio = (paginaAtual - 1) * ITEMS_PER_PAGE;
  const clientesPagina = clientesFiltrados.slice(inicio, inicio + ITEMS_PER_PAGE);
  const clientesBrasil = clientesFiltrados.filter((cliente) => cliente.pais_origem === 'Brasil').length;
  const clientesExterior = Math.max(clientesFiltrados.length - clientesBrasil, 0);

  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  const handleClearSearch = () => {
    setSearchTerm('');
  };

  const handlePageChange = (novaPagina) => {
    if (novaPagina >= 1 && novaPagina <= totalPages) {
      setCurrentPage(novaPagina);
    }
  };

  /**
   * Renderiza o conteúdo (loading/erro/tabela com paginação).
   * Não gera novas chamadas ao backend; usa os estados atuais.
   */
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

    if (!clientesFiltrados.length) {
      return (
        <Alert variant="info" className="text-center">
          Nenhum cliente {viewStatus.toLowerCase()} encontrado para o filtro aplicado.
        </Alert>
      );
    }

    return (
      <div className="clientes-table-shell">
        <div className="table-responsive">
        <table className="table table-hover align-middle app-data-table">
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
            {clientesPagina.map((cliente) => (
              <tr key={cliente.id_hospede}>
                <td>{cliente.nome_hospede}</td>
                <td>
                  <span className="table-main-text">{cliente.email_hospede || 'Sem email'}</span>
                  <br />
                  <small className="text-muted">
                    {cliente.telefone || 'Sem telefone'}
                  </small>
                </td>
                <td>
                  <span className="table-soft-pill">{cliente.pais_origem}</span>
                </td>
                <td>
                  {cliente.pais_origem === 'Brasil'
                    ? `CPF: ${cliente.cpf || 'N/A'}`
                    : `Pass: ${cliente.passaporte || 'N/A'}`}
                </td>
                <td>
                  {viewStatus === 'Ativo' ? (
                    <>
                      <div className="table-action-group">
                        <Button
                          size="sm"
                          variant="outline-secondary"
                          onClick={() => handleShowEditarCliente(cliente)}
                        >
                          <Edit2 size={14} />
                          Editar
                        </Button>
                        <Button
                          size="sm"
                          variant="outline-danger"
                          onClick={() => handleShowInativar(cliente)}
                        >
                          <UserX size={14} />
                          Inativar
                        </Button>
                      </div>
                    </>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline-success"
                      onClick={() => handleReativar(cliente)}
                    >
                      <RotateCcw size={14} />
                      Reativar
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
        <div className="table-footer">
          <small className="text-muted">
            Mostrando {clientesPagina.length ? inicio + 1 : 0}-
            {Math.min(inicio + clientesPagina.length, clientesFiltrados.length)} de {clientesFiltrados.length}
          </small>
          <Pagination className="mb-0">
            <Pagination.Prev
              disabled={paginaAtual === 1}
              onClick={() => handlePageChange(paginaAtual - 1)}
            />
            <Pagination.Item active>
              Página {paginaAtual} de {totalPages}
            </Pagination.Item>
            <Pagination.Next
              disabled={paginaAtual === totalPages}
              onClick={() => handlePageChange(paginaAtual + 1)}
            />
          </Pagination>
        </div>
      </div>
    );
  };


  return (
    <div className="clientes-page">
      <div className="page-header">
        <div className="page-title-block">
          <h1>Gerenciamento de Clientes</h1>
          <span className="page-title-meta">Cadastro, documentos e status dos hóspedes</span>
        </div>
        <div className="clientes-toolbar">
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
            className="page-primary-action"
            onClick={handleShowNovoCliente}
            disabled={viewStatus === 'Inativo'}
          >
            <UserPlus size={16} />
            Novo Cliente
          </Button>

          <InputGroup className="clientes-search">
            <InputGroup.Text>
              <Search size={16} />
            </InputGroup.Text>
            <Form.Control
              type="text"
              placeholder="Buscar por nome ou país"
              value={searchTerm}
              onChange={handleSearchChange}
            />
            <Button
              variant="outline-secondary"
              onClick={handleClearSearch}
              disabled={!searchTerm}
            >
              <X size={14} />
              Limpar
            </Button>
          </InputGroup>
        </div>
      </div>

      <div className="page-summary-grid clientes-summary-grid">
        <div className="summary-card">
          <span className="summary-label">Visualização</span>
          <strong>{viewStatus}</strong>
        </div>
        <div className="summary-card">
          <span className="summary-label">Resultados</span>
          <strong>{clientesFiltrados.length}</strong>
        </div>
        <div className="summary-card">
          <span className="summary-label">Brasil</span>
          <strong>{clientesBrasil}</strong>
        </div>
        <div className="summary-card">
          <span className="summary-label">Exterior</span>
          <strong>{clientesExterior}</strong>
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
