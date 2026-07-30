/**
 * BarcosPage.js
 * --------------
 * Tela administrativa para gerenciar a frota usada nas reservas.
 * Permite filtrar, criar, editar e excluir barcos.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Button, ButtonGroup, Spinner } from 'react-bootstrap';
import { Edit2, Plus, Trash2 } from 'react-feather';
import { toast } from 'react-toastify';

import { deleteBarco, fetchBarcos } from '../services/api';
import BarcoModal from '../components/BarcoModal';
import ConfirmacaoModal from '../components/ConfirmacaoModal';
import './BarcosPage.css';

const STATUS_FILTERS = [
  { value: 'Todos', label: 'Todos' },
  { value: 'Disponível', label: 'Disponíveis' },
  { value: 'Manutenção', label: 'Manutenção' },
  { value: 'Bloqueado', label: 'Bloqueados' },
];

const getStatusClass = (status) => {
  if (status === 'Disponível') return 'success';
  if (status === 'Manutenção') return 'warning';
  return 'danger';
};

const BarcosPage = () => {
  const [barcos, setBarcos] = useState([]);
  const [viewStatus, setViewStatus] = useState('Todos');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showModal, setShowModal] = useState(false);
  const [barcoSelecionado, setBarcoSelecionado] = useState(null);

  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [barcoParaExcluir, setBarcoParaExcluir] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const resumo = useMemo(() => {
    const capacidadeTotal = barcos.reduce(
      (total, barco) => total + Number(barco.capacidade_pessoas || 0),
      0
    );
    const disponiveis = barcos.filter((barco) => barco.status_barco === 'Disponível').length;
    const indisponiveis = barcos.filter((barco) => barco.status_barco !== 'Disponível').length;

    return { capacidadeTotal, disponiveis, indisponiveis };
  }, [barcos]);

  const carregarBarcos = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchBarcos({ status: viewStatus });
      setBarcos(data || []);
    } catch (err) {
      const apiError = err?.error || err || {};
      setError(apiError.message || 'Falha ao carregar a lista de barcos.');
    } finally {
      setLoading(false);
    }
  }, [viewStatus]);

  useEffect(() => {
    carregarBarcos();
  }, [carregarBarcos]);

  const handleShowNovoBarco = () => {
    setBarcoSelecionado(null);
    setShowModal(true);
  };

  const handleShowEditarBarco = (barco) => {
    setBarcoSelecionado(barco);
    setShowModal(true);
  };

  const handleSaveSuccess = (barcoSalvo) => {
    setShowModal(false);

    if (viewStatus !== 'Todos' && barcoSalvo.status_barco !== viewStatus) {
      setBarcos((prev) => prev.filter((barco) => barco.id_barco !== barcoSalvo.id_barco));
      toast.info(`Barco movido para "${barcoSalvo.status_barco}".`);
      return;
    }

    setBarcos((prev) => {
      const existe = prev.some((barco) => barco.id_barco === barcoSalvo.id_barco);
      return existe
        ? prev.map((barco) => (barco.id_barco === barcoSalvo.id_barco ? barcoSalvo : barco))
        : [...prev, barcoSalvo].sort((a, b) => a.nome_barco.localeCompare(b.nome_barco));
    });
  };

  const handleShowExcluir = (barco) => {
    setBarcoParaExcluir(barco);
    setShowConfirmModal(true);
  };

  const handleConfirmExcluir = async () => {
    if (!barcoParaExcluir) return;
    setIsDeleting(true);

    try {
      await deleteBarco(barcoParaExcluir.id_barco);
      setBarcos((prev) => prev.filter((barco) => barco.id_barco !== barcoParaExcluir.id_barco));
      toast.success(`Barco "${barcoParaExcluir.nome_barco}" excluído com sucesso.`);
    } catch (err) {
      const apiError = err?.error || err || {};
      toast.error(apiError.message || 'Erro ao excluir barco.');
    } finally {
      setIsDeleting(false);
      setShowConfirmModal(false);
      setBarcoParaExcluir(null);
    }
  };

  const renderContent = () => {
    if (loading && barcos.length === 0) {
      return (
        <div className="text-center p-5">
          <Spinner animation="border" variant="success" />
          <p>Carregando barcos...</p>
        </div>
      );
    }

    if (error) {
      return (
        <Alert variant="danger">
          <Alert.Heading>Erro ao Carregar Barcos</Alert.Heading>
          <p>{error}</p>
          <Button onClick={carregarBarcos} variant="danger">
            Tentar Novamente
          </Button>
        </Alert>
      );
    }

    if (barcos.length === 0 && !loading) {
      return (
        <div className="text-center p-5">
          Nenhum barco encontrado para este filtro.
        </div>
      );
    }

    return (
      <div className="barcos-table-shell">
        <div className="table-responsive">
          <table className="table table-hover align-middle app-data-table">
            <thead>
              <tr>
                <th>Barco</th>
                <th>Capacidade</th>
                <th>Status</th>
                <th>Observação</th>
                <th style={{ width: '150px' }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {barcos.map((barco) => (
                <tr key={barco.id_barco}>
                  <td>
                    <span className="barco-name">{barco.nome_barco}</span>
                  </td>
                  <td>
                    <span className="table-soft-pill">
                      {barco.capacidade_pessoas} pessoas
                    </span>
                  </td>
                  <td>
                    <span className={`barco-status-pill ${getStatusClass(barco.status_barco)}`}>
                      {barco.status_barco}
                    </span>
                  </td>
                  <td className="barco-observacao">
                    {barco.observacao || 'Sem observação'}
                  </td>
                  <td>
                    <div className="table-action-group">
                      <Button
                        size="sm"
                        variant="outline-secondary"
                        onClick={() => handleShowEditarBarco(barco)}
                      >
                        <Edit2 size={14} />
                        Editar
                      </Button>

                      <Button
                        size="sm"
                        variant="outline-danger"
                        onClick={() => handleShowExcluir(barco)}
                      >
                        <Trash2 size={14} />
                        Excluir
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="barcos-page">
      <div className="page-header">
        <div className="page-title-block">
          <h1>Gerenciamento de Barcos</h1>
          <span className="page-title-meta">Frota, capacidade e status operacional</span>
        </div>

        <div className="barcos-toolbar">
          <ButtonGroup className="me-2">
            {STATUS_FILTERS.map((filter) => (
              <Button
                key={filter.value}
                variant={viewStatus === filter.value ? 'success' : 'outline-secondary'}
                onClick={() => setViewStatus(filter.value)}
                style={
                  viewStatus === filter.value
                    ? { backgroundColor: '#26522c', borderColor: '#26522c' }
                    : {}
                }
              >
                {filter.label}
              </Button>
            ))}
          </ButtonGroup>

          <Button
            variant="primary"
            className="page-primary-action"
            onClick={handleShowNovoBarco}
          >
            <Plus size={16} />
            Novo Barco
          </Button>
        </div>
      </div>

      <div className="page-summary-grid barcos-summary-grid">
        <div className="summary-card">
          <span className="summary-label">Visualização</span>
          <strong>{viewStatus}</strong>
        </div>
        <div className="summary-card">
          <span className="summary-label">Barcos</span>
          <strong>{barcos.length}</strong>
        </div>
        <div className="summary-card">
          <span className="summary-label">Capacidade total</span>
          <strong>{resumo.capacidadeTotal}</strong>
        </div>
        <div className="summary-card">
          <span className="summary-label">Disponíveis</span>
          <strong>{resumo.disponiveis}</strong>
        </div>
      </div>

      <div className="barcos-operacao-note">
        <strong>{resumo.indisponiveis}</strong> barcos fora de operação no filtro atual.
      </div>

      <div className="page-content">{renderContent()}</div>

      <BarcoModal
        show={showModal}
        handleClose={() => setShowModal(false)}
        onSaveSuccess={handleSaveSuccess}
        barco={barcoSelecionado}
      />

      {barcoParaExcluir && (
        <ConfirmacaoModal
          show={showConfirmModal}
          handleClose={() => setShowConfirmModal(false)}
          handleConfirm={handleConfirmExcluir}
          loading={isDeleting}
          title="Confirmar Exclusão"
          body={`Tem certeza que deseja excluir o barco "${barcoParaExcluir.nome_barco}"? Esta ação não pode ser desfeita e falhará se o barco estiver vinculado a uma reserva.`}
          confirmText="Sim, Excluir"
          confirmVariant="danger"
        />
      )}
    </div>
  );
};

export default BarcosPage;
