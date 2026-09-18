import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, ButtonGroup, Form, Modal, Spinner, Table } from 'react-bootstrap';
import {
  AlertTriangle,
  Clock,
  CreditCard,
  DollarSign,
  Eye,
  RefreshCw,
  Search,
  ShoppingBag,
} from 'react-feather';

import { fetchContasEmBordoGestao } from '../services/api';
import './ContasEmBordoPage.css';

const STATUS_FILTROS = ['Todas', 'Aberta', 'Fechada', 'Sem conta'];

const formatCurrency = (value) =>
  Number(value || 0).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });

const formatNumber = (value) =>
  new Intl.NumberFormat('pt-BR').format(Number.isFinite(Number(value)) ? Number(value) : 0);

const parseDateOnly = (value) => {
  if (!value) return null;
  const datePart = String(value).split('T')[0];
  const [year, month, day] = datePart.split('-').map(Number);
  if (!year || !month || !day) return null;
  return new Date(Date.UTC(year, month - 1, day));
};

const formatDate = (value) => {
  const date = parseDateOnly(value);
  if (!date) return '-';
  return date.toLocaleDateString('pt-BR', { timeZone: 'UTC' });
};

const formatDateTime = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString('pt-BR');
};

const normalize = (value) =>
  String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();

const statusClass = (status) =>
  normalize(status).replace(/\s+/g, '-');

const checkoutText = (dias) => {
  if (dias === null || typeof dias === 'undefined') return 'Sem data';
  if (dias < 0) return `${Math.abs(dias)} dias atrasado`;
  if (dias === 0) return 'Hoje';
  if (dias === 1) return 'Amanha';
  return `${dias} dias`;
};

const checkoutClass = (dias) => {
  if (dias === null || typeof dias === 'undefined') return 'neutral';
  if (dias < 0 || dias === 0) return 'alert';
  if (dias <= 2) return 'soon';
  return 'ok';
};

const tipoLancamentoClass = (tipo) => {
  const normalized = normalize(tipo);
  if (normalized === 'bebidas') return 'bebidas';
  if (normalized === 'lojinha') return 'lojinha';
  if (normalized === 'lavanderia') return 'lavanderia';
  return 'outros';
};

const ContasEmBordoPage = () => {
  const [dados, setDados] = useState({ resumo: {}, contas: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFiltro, setStatusFiltro] = useState('Todas');
  const [busca, setBusca] = useState('');
  const [contaSelecionada, setContaSelecionada] = useState(null);

  const carregarContas = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchContasEmBordoGestao();
      setDados({
        resumo: data?.resumo || {},
        contas: data?.contas || [],
      });
    } catch (err) {
      const apiError = err?.error || err || {};
      setError(apiError.message || 'Falha ao carregar contas em bordo.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carregarContas();
  }, [carregarContas]);

  const contasFiltradas = useMemo(() => {
    const termo = normalize(busca);
    return (dados.contas || []).filter((conta) => {
      const bateStatus = statusFiltro === 'Todas' || conta.status_conta === statusFiltro;
      const textoConta = normalize(
        `${conta.hospede} ${conta.quarto} ${conta.id_conta || ''} ${conta.id_reserva}`
      );
      const bateBusca = !termo || textoConta.includes(termo);
      return bateStatus && bateBusca;
    });
  }, [busca, dados.contas, statusFiltro]);

  const renderResumo = () => {
    const resumo = dados.resumo || {};
    return (
      <div className="contas-bordo-summary-grid">
        <div className="contas-bordo-summary-card">
          <span>Clientes em bordo</span>
          <strong>{formatNumber(resumo.clientes_em_bordo)}</strong>
        </div>
        <div className="contas-bordo-summary-card">
          <span>Contas abertas</span>
          <strong>{formatNumber(resumo.contas_abertas)}</strong>
          <small>{formatCurrency(resumo.total_aberto)} em aberto</small>
        </div>
        <div className="contas-bordo-summary-card">
          <span>Contas fechadas</span>
          <strong>{formatNumber(resumo.contas_fechadas)}</strong>
          <small>{formatCurrency(resumo.total_fechado)} fechado</small>
        </div>
        <div className="contas-bordo-summary-card urgent">
          <span>Check-outs proximos</span>
          <strong>{formatNumber(resumo.checkouts_proximos)}</strong>
          <small>{formatNumber(resumo.checkouts_hoje)} previstos para hoje</small>
        </div>
      </div>
    );
  };

  const renderTabela = () => {
    if (loading && !dados.contas.length) {
      return (
        <div className="contas-bordo-loading">
          <Spinner animation="border" variant="success" />
          <p>Carregando contas em bordo...</p>
        </div>
      );
    }

    if (error) {
      return (
        <Alert variant="danger" className="contas-bordo-error">
          <Alert.Heading>Erro ao carregar contas</Alert.Heading>
          <p>{error}</p>
          <Button variant="danger" onClick={carregarContas}>
            <RefreshCw size={16} />
            Tentar novamente
          </Button>
        </Alert>
      );
    }

    if (!contasFiltradas.length) {
      return <div className="contas-bordo-empty">Nenhuma conta encontrada para o filtro atual.</div>;
    }

    return (
      <div className="contas-bordo-table-shell">
        <Table responsive hover className="contas-bordo-table align-middle">
          <thead>
            <tr>
              <th>Cliente</th>
              <th>Conta</th>
              <th>Check-out</th>
              <th>Consumo</th>
              <th>Ultimo lancamento</th>
              <th className="text-end">Acoes</th>
            </tr>
          </thead>
          <tbody>
            {contasFiltradas.map((conta) => (
              <tr key={`${conta.id_reserva}-${conta.id_conta || 'sem-conta'}`}>
                <td>
                  <div className="conta-cliente">
                    <strong>{conta.hospede}</strong>
                    <span>
                      Quarto {conta.quarto || '--'} {conta.tipo_quarto ? `- ${conta.tipo_quarto}` : ''}
                    </span>
                    {conta.barco && <span>{conta.barco}</span>}
                  </div>
                </td>
                <td>
                  <div className="conta-status-stack">
                    <span className={`conta-status-pill ${statusClass(conta.status_conta)}`}>
                      {conta.status_conta}
                    </span>
                    <span className="conta-soft-text">
                      {conta.id_conta ? `Conta #${conta.id_conta}` : `Reserva #${conta.id_reserva}`}
                    </span>
                  </div>
                </td>
                <td>
                  <div className="checkout-cell">
                    <strong>{formatDate(conta.checkout)}</strong>
                    <span className={`checkout-pill ${checkoutClass(conta.dias_ate_checkout)}`}>
                      <Clock size={13} />
                      {checkoutText(conta.dias_ate_checkout)}
                    </span>
                  </div>
                </td>
                <td>
                  <div className="conta-total-cell">
                    <strong>{formatCurrency(conta.total_acumulado)}</strong>
                    <span>
                      {formatCurrency(conta.totais?.bebidas)} bebidas | {formatCurrency(conta.totais?.lojinha)} lojinha
                    </span>
                    <span>{formatCurrency(conta.totais?.lavanderia)} lavanderia</span>
                  </div>
                </td>
                <td>
                  {conta.ultimo_lancamento ? (
                    <div className="ultimo-lancamento">
                      <Badge className={`lancamento-badge ${tipoLancamentoClass(conta.ultimo_lancamento.tipo)}`}>
                        {conta.ultimo_lancamento.tipo}
                      </Badge>
                      <strong>{conta.ultimo_lancamento.descricao}</strong>
                      <span>{formatDateTime(conta.ultimo_lancamento.data_lancamento)}</span>
                    </div>
                  ) : (
                    <span className="conta-soft-text">Sem lancamentos</span>
                  )}
                </td>
                <td className="text-end">
                  <Button
                    variant="outline-success"
                    size="sm"
                    className="contas-bordo-action"
                    onClick={() => setContaSelecionada(conta)}
                  >
                    <Eye size={15} />
                    Detalhes
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
    );
  };

  return (
    <div className="contas-bordo-page">
      <div className="page-header">
        <div className="page-title-block">
          <h1>Contas em Bordo</h1>
          <span className="page-title-meta">Acompanhamento das contas dos clientes embarcados</span>
        </div>
        <Button
          variant="outline-secondary"
          className="contas-bordo-refresh"
          onClick={carregarContas}
          disabled={loading}
        >
          <RefreshCw size={16} />
          Atualizar
        </Button>
      </div>

      {renderResumo()}

      <section className="contas-bordo-panel">
        <div className="contas-bordo-toolbar">
          <div className="contas-bordo-search">
            <Search size={16} />
            <Form.Control
              value={busca}
              onChange={(event) => setBusca(event.target.value)}
              placeholder="Buscar por cliente, quarto ou conta"
            />
          </div>
          <ButtonGroup className="contas-bordo-status-filter">
            {STATUS_FILTROS.map((status) => (
              <Button
                key={status}
                variant={statusFiltro === status ? 'success' : 'outline-secondary'}
                onClick={() => setStatusFiltro(status)}
                style={
                  statusFiltro === status
                    ? { backgroundColor: '#26522c', borderColor: '#26522c' }
                    : {}
                }
              >
                {status}
              </Button>
            ))}
          </ButtonGroup>
        </div>

        {renderTabela()}
      </section>

      <Modal
        show={Boolean(contaSelecionada)}
        onHide={() => setContaSelecionada(null)}
        size="xl"
        centered
        className="contas-bordo-modal"
      >
        <Modal.Header closeButton>
          <Modal.Title>Detalhes da conta</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {contaSelecionada && (
            <>
              <div className="conta-detail-header">
                <div>
                  <strong>{contaSelecionada.hospede}</strong>
                  <span>
                    Quarto {contaSelecionada.quarto || '--'} | Check-out {formatDate(contaSelecionada.checkout)}
                  </span>
                </div>
                <div className="conta-detail-total">
                  <span>Total acumulado</span>
                  <strong>{formatCurrency(contaSelecionada.total_acumulado)}</strong>
                </div>
              </div>

              <div className="conta-detail-metrics">
                <div>
                  <ShoppingBag size={16} />
                  <span>Bebidas</span>
                  <strong>{formatCurrency(contaSelecionada.totais?.bebidas)}</strong>
                </div>
                <div>
                  <DollarSign size={16} />
                  <span>Lojinha</span>
                  <strong>{formatCurrency(contaSelecionada.totais?.lojinha)}</strong>
                </div>
                <div>
                  <CreditCard size={16} />
                  <span>Lavanderia</span>
                  <strong>{formatCurrency(contaSelecionada.totais?.lavanderia)}</strong>
                </div>
                <div>
                  <AlertTriangle size={16} />
                  <span>Status</span>
                  <strong>{contaSelecionada.status_conta}</strong>
                </div>
              </div>

              {contaSelecionada.lancamentos?.length ? (
                <div className="conta-detail-table-shell">
                  <Table responsive hover size="sm" className="conta-detail-table">
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Tipo</th>
                        <th>Item</th>
                        <th>Qtd.</th>
                        <th>Usuario</th>
                        <th className="text-end">Subtotal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {contaSelecionada.lancamentos.map((lancamento) => (
                        <tr key={lancamento.id}>
                          <td>{formatDateTime(lancamento.data_lancamento)}</td>
                          <td>
                            <Badge className={`lancamento-badge ${tipoLancamentoClass(lancamento.tipo)}`}>
                              {lancamento.tipo}
                            </Badge>
                          </td>
                          <td>
                            <strong>{lancamento.descricao}</strong>
                            {lancamento.observacao && <span className="item-note">{lancamento.observacao}</span>}
                          </td>
                          <td>{formatNumber(lancamento.quantidade)}</td>
                          <td>{lancamento.usuario || '-'}</td>
                          <td className="text-end fw-bold">{formatCurrency(lancamento.subtotal)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              ) : (
                <div className="contas-bordo-empty">Essa conta ainda nao possui lancamentos.</div>
              )}
            </>
          )}
        </Modal.Body>
      </Modal>
    </div>
  );
};

export default ContasEmBordoPage;
