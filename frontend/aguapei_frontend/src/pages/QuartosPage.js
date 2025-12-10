/**
 * QuartosPage.js
 * --------------
 * Tela de administração de quartos. Permite filtrar por status,
 * cadastrar/editar via modal e excluir com confirmação.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Spinner, Alert, Button, ButtonGroup } from 'react-bootstrap';
import { toast } from 'react-toastify';

import { fetchQuartos, deleteQuarto } from '../services/api';
import QuartoModal from '../components/QuartoModal';
import ConfirmacaoModal from '../components/ConfirmacaoModal';
// import './QuartosPage.css'; // Descomente se existir o arquivo de estilos

/**
 * Tela de gerenciamento de quartos.
 *
 * Responsabilidades:
 *  - Listar quartos filtrando por status (chama `fetchQuartos`, impactando SELECT no banco).
 *  - Permitir criar/editar quartos via `QuartoModal` (INSERT/UPDATE em `quarto`).
 *  - Excluir quartos quando possível (DELETE em `quarto`, sujeito a FK).
 */
const QuartosPage = () => {
  const [quartos, setQuartos] = useState([]);
  const [viewStatus, setViewStatus] = useState('Disponível');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showModal, setShowModal] = useState(false);
  const [quartoSelecionado, setQuartoSelecionado] = useState(null);

  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [quartoParaExcluir, setQuartoParaExcluir] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  /**
   * Busca os quartos de acordo com o filtro atual (`viewStatus`).
   * Impacta o banco com SELECT simples; atualiza a tabela do front.
   */
  const carregarQuartos = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchQuartos(viewStatus);
      setQuartos(data);
    } catch (err) {
      setError(err.message || 'Falha ao carregar a lista de quartos.');
    } finally {
      setLoading(false);
    }
  }, [viewStatus]);

  useEffect(() => {
    carregarQuartos();
  }, [carregarQuartos]);

  // Abre o modal em modo criação, resetando o item selecionado.
  const handleShowNovoQuarto = () => {
    setQuartoSelecionado(null);
    setShowModal(true);
  };

  // Abre o modal em modo edição com o quarto escolhido.
  const handleShowEditarQuarto = (quarto) => {
    setQuartoSelecionado(quarto);
    setShowModal(true);
  };

  /**
   * Callback disparado pelo `QuartoModal` após um save bem-sucedido.
   * Se o status mudou, removemos da lista atual (pois não corresponde ao filtro).
   * Caso contrário, atualizamos/inserimos o registro na listagem renderizada.
   */
  const handleSaveSuccess = (quartoSalvo) => {
    setShowModal(false);

    if (quartoSalvo.status_quarto !== viewStatus) {
      setQuartos((prev) =>
        prev.filter((q) => q.id_quarto !== quartoSalvo.id_quarto)
      );
      toast.info(`Quarto movido para "${quartoSalvo.status_quarto}".`);
    } else {
      setQuartos((prev) => {
        const existe = prev.some((q) => q.id_quarto === quartoSalvo.id_quarto);
        return existe
          ? prev.map((q) =>
              q.id_quarto === quartoSalvo.id_quarto ? quartoSalvo : q
            )
          : [...prev, quartoSalvo];
      });
    }
  };

  // Exibe modal de confirmação antes de deletar definitivamente.
  const handleShowExcluir = (quarto) => {
    setQuartoParaExcluir(quarto);
    setShowConfirmModal(true);
  };

  /**
   * Confirmação do modal de exclusão.
   * Chama `deleteQuarto` (DELETE no banco) e remove da UI quando sucesso.
   * Valida erros de FK para informar ao usuário sobre reservas vinculadas.
   */
  const handleConfirmExcluir = async () => {
    if (!quartoParaExcluir) return;
    setIsDeleting(true);

    try {
      await deleteQuarto(quartoParaExcluir.id_quarto);
      setQuartos((prev) =>
        prev.filter((q) => q.id_quarto !== quartoParaExcluir.id_quarto)
      );
      toast.success(`Quarto "${quartoParaExcluir.numero}" excluído com sucesso.`);
    } catch (err) {
      if (err.code === 'FK_CONSTRAINT') {
        toast.error(err.message);
      } else {
        toast.error(err.message || 'Erro ao excluir quarto.');
      }
    } finally {
      setIsDeleting(false);
      setShowConfirmModal(false);
      setQuartoParaExcluir(null);
    }
  };

  /**
   * Renderiza a tabela ou estados de loading/erro.
   * Sem impacto no banco; apenas organiza o que será mostrado.
   */
  const renderContent = () => {
    if (loading && quartos.length === 0) {
      return (
        <div className="text-center p-5">
          <Spinner animation="border" variant="success" />
          <p>Carregando quartos {viewStatus.toLowerCase()}s...</p>
        </div>
      );
    }

    if (error) {
      return (
        <Alert variant="danger">
          <Alert.Heading>Erro ao Carregar Quartos</Alert.Heading>
          <p>{error}</p>
          <Button onClick={carregarQuartos} variant="danger">
            Tentar Novamente
          </Button>
        </Alert>
      );
    }

    if (quartos.length === 0 && !loading) {
      return (
        <div className="text-center p-5">
          Nenhum quarto {viewStatus.toLowerCase()} encontrado.
        </div>
      );
    }

    return (
      <div className="table-responsive">
        <table className="table table-striped table-hover align-middle">
          <thead>
            <tr>
              <th>Número / Nome</th>
              <th>Tipo (Capacidade)</th>
              <th>Valor da Diária</th>
              <th>Status</th>
              <th style={{ width: '150px' }}>Ações</th>
            </tr>
          </thead>
          <tbody>
            {quartos.map((quarto) => (
              <tr key={quarto.id_quarto}>
                <td>{quarto.numero}</td>
                <td>{quarto.tipo_quarto}</td>
                <td>
                  {new Intl.NumberFormat('pt-BR', {
                    style: 'currency',
                    currency: 'BRL',
                  }).format(quarto.valor_diaria)}
                </td>
                <td>{quarto.status_quarto}</td>
                <td>
                  <Button
                    size="sm"
                    variant="outline-secondary"
                    onClick={() => handleShowEditarQuarto(quarto)}
                  >
                    Editar
                  </Button>

                  {viewStatus === 'Manutenção' && (
                    <Button
                      size="sm"
                      variant="outline-danger"
                      className="ms-2"
                      onClick={() => handleShowExcluir(quarto)}
                    >
                      Excluir
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
    <div className="quartos-page">
      <div className="page-header">
        <h1>Gerenciamento de Quartos</h1>
        <div className="page-actions mb-3">
          <ButtonGroup className="me-2">
            <Button
              variant={viewStatus === 'Disponível' ? 'success' : 'outline-secondary'}
              onClick={() => setViewStatus('Disponível')}
              style={
                viewStatus === 'Disponível'
                  ? { backgroundColor: '#26522c', borderColor: '#26522c' }
                  : {}
              }
            >
              Disponíveis
            </Button>
            <Button
              variant={viewStatus === 'Manutenção' ? 'warning' : 'outline-secondary'}
              onClick={() => setViewStatus('Manutenção')}
            >
              Em Manutenção
            </Button>
          </ButtonGroup>

          <Button
            variant="primary"
            style={{ backgroundColor: '#26522c', borderColor: '#26522c' }}
            onClick={handleShowNovoQuarto}
          >
            + Novo Quarto
          </Button>
        </div>
      </div>

      <div className="page-content">{renderContent()}</div>

      <QuartoModal
        show={showModal}
        handleClose={() => setShowModal(false)}
        onSaveSuccess={handleSaveSuccess}
        quarto={quartoSelecionado}
      />

      {quartoParaExcluir && (
        <ConfirmacaoModal
          show={showConfirmModal}
          handleClose={() => setShowConfirmModal(false)}
          handleConfirm={handleConfirmExcluir}
          loading={isDeleting}
          title="Confirmar Exclusão"
          body={`Tem certeza que deseja excluir o quarto "${quartoParaExcluir.numero}"? Esta ação não pode ser desfeita e falhará se o quarto estiver vinculado a uma reserva.`}
          confirmText="Sim, Excluir"
          confirmVariant="danger"
        />
      )}
    </div>
  );
};

export default QuartosPage;
