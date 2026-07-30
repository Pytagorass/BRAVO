/**
 * GestaoPage.js
 * -------------
 * Página de Business Intelligence. Carrega indicadores consolidados,
 * gráficos e listas de reservas pendentes para apoiar decisões.
 */
import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchIndicadoresGestao, fetchReservasPendentesGestao, fetchAgendaReservas } from '../services/api';
import { Row, Col, Spinner, Alert, Button, Form, Card, Badge, Modal, Table } from 'react-bootstrap';
import { AlertTriangle, BarChart2, FileText, RefreshCw } from 'react-feather';
import './GestaoPage.css';

import { Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { toast } from 'react-toastify';

Chart.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

// Formata valores numéricos como moeda brasileira para exibição nos gráficos/cartões.
const formatCurrency = (value) => {
  const numberValue = parseFloat(value) || 0;
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(numberValue);
};

// Formata números inteiros com separador pt-BR para contadores.
const formatNumber = (value) =>
  new Intl.NumberFormat('pt-BR').format(Number.isFinite(Number(value)) ? Number(value) : 0);

// Converte número em string decimal com a quantidade de casas informada.
const formatDecimal = (value, digits = 2) => (Number(value) || 0).toFixed(digits);

const STATUS_BADGE_VARIANT = {
  Agendada: 'warning',
  Ativa: 'success',
  Concluída: 'secondary',
  Cancelada: 'danger',
};

const PAGAMENTO_BADGE_VARIANT = {
  Pendente: 'warning',
  'Em Partes': 'info',
  Pago: 'success',
  Cancelado: 'secondary',
};

// Converte datas ISO do backend em data pt-BR; usado em tabelas e PDFs.
const formatDate = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('pt-BR', { timeZone: 'UTC' });
};

// Converte o formato YYYY-MM usado no SQL para rótulos "Mai/25".
const formatChartLabel = (mes_ano) => {
  try {
    const [ano, mes] = mes_ano.split('-');
    const data = new Date(ano, mes - 1);
    const mesFmt = data.toLocaleString('pt-BR', { month: 'short' });
    const anoFmt = ano.substring(2);
    return `${mesFmt.charAt(0).toUpperCase() + mesFmt.slice(1)}/${anoFmt}`;
  } catch {
    return mes_ano;
  }
};

/**
 * Página de Gestão (BI).
 *
 * Responsabilidades:
 *  - Buscar KPIs agregados no backend (impacta consultas pesadas no banco).
 *  - Renderizar gráficos, cards e tabelas para o front-end administrativo.
 *  - Disponibilizar exportação mensal em PDF usando os dados já carregados.
 */
const GestaoPage = () => {
  const navigate = useNavigate();
  const [indicadores, setIndicadores] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [anoSelecionado, setAnoSelecionado] = useState(new Date().getFullYear());
  const [showPendentesModal, setShowPendentesModal] = useState(false);
  const [loadingPendentes, setLoadingPendentes] = useState(false);
  const [reservasPendentesLista, setReservasPendentesLista] = useState([]);
  const [erroPendentes, setErroPendentes] = useState(null);
  const [confirmRelatorio, setConfirmRelatorio] = useState({ visible: false, mesInfo: null });
  const [gerandoRelatorio, setGerandoRelatorio] = useState(false);
  const anosDisponiveis = [0, 1, 2, 3].map((i) => new Date().getFullYear() - i);

  /**
   * Busca indicadores do ano selecionado sempre que `anoSelecionado` muda.
   * Consome o endpoint `/gestao/indicadores/`, que executa queries consolidadas
   * (impacto direto no banco). Em caso de falha, mostra alerta na interface.
   */
  const carregarIndicadores = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchIndicadoresGestao(anoSelecionado);
      setIndicadores(data);
    } catch (err) {
      setError(err.message || 'Falha ao carregar os indicadores de gestão.');
    } finally {
      setLoading(false);
    }
  }, [anoSelecionado]);

  useEffect(() => {
    carregarIndicadores();
  }, [carregarIndicadores]);

  /**
   * Carrega reservas com pagamento pendente para o modal específico.
   * Chama `/gestao/reservas-pendentes/` e armazena o resultado na tabela.
   */
  const carregarReservasPendentes = async () => {
    try {
      setErroPendentes(null);
      setLoadingPendentes(true);
      const data = await fetchReservasPendentesGestao();
      setReservasPendentesLista(data?.reservas || []);
    } catch (err) {
      setErroPendentes(err?.error?.message || err.message || 'Falha ao carregar reservas pendentes.');
    } finally {
      setLoadingPendentes(false);
    }
  };

  const handleAbrirPendentesModal = () => {
    setShowPendentesModal(true);
    carregarReservasPendentes();
  };

  const handleFecharPendentesModal = () => {
    setShowPendentesModal(false);
    setReservasPendentesLista([]);
    setErroPendentes(null);
  };

  /**
   * Gera o PDF com os dados resumidos + reservas do mês selecionado.
   *
   * @param {object} mesInfo - registro do array `faturamento_mensal`.
   * @param {Array} reservasDoMes - reservas filtradas via `/agenda/`.
   * Fluxo:
   *   1. Monta cabeçalho com indicadores (sem alterar o banco).
   *   2. Renderiza tabela de reservas referente ao mês.
   * Retorno: nenhum (dispara download local via jsPDF).
   */
  const gerarRelatorioMensalPDF = (mesInfo, reservasDoMes) => {
    if (!mesInfo) return;
    const doc = new jsPDF({ orientation: 'portrait', unit: 'pt' });
    const tituloMes = formatChartLabel(mesInfo.mes_ano);

    doc.setFontSize(16);
    doc.text(`Relatório Mensal - ${tituloMes}`, 40, 40);

    autoTable(doc, {
      startY: 70,
      head: [['Indicador', 'Valor']],
      body: [
        ['Faturamento Mensal', formatCurrency(mesInfo.faturamento_mensal)],
        ['Taxa de Ocupação', `${formatDecimal(mesInfo.taxa_ocupacao_percent)}%`],
        ['Quartos Ocupados', formatNumber(mesInfo.dias_ocupados || 0)],
        ['Quartos Disponíveis', formatNumber(mesInfo.dias_disponiveis_mes || 0)],
      ],
    });

    const startYReservas = doc.lastAutoTable?.finalY
      ? doc.lastAutoTable.finalY + 20
      : 120;

    if (reservasDoMes?.length) {
      autoTable(doc, {
        startY: startYReservas,
        head: [['Reserva', 'Quarto', 'Titular', 'Check-in', 'Check-out', 'Status']],
        body: reservasDoMes.map((r) => [
          r.id_reserva,
          r.numero_quarto || r.id_quarto,
          r.nome_titular || 'N/A',
          formatDate(r.checkin),
          formatDate(r.checkout),
          r.status_reserva,
        ]),
      });
    } else {
      doc.text('Nenhuma reserva localizada para este mês.', 40, startYReservas);
    }

    doc.save(`relatorio-${mesInfo.mes_ano}.pdf`);
  };

  /**
   * Confirmação do modal de exportação.
   * Busca as reservas via `/agenda/`, filtra pelo mês clicado e
   * chama `gerarRelatorioMensalPDF`. Impacta o banco apenas no SELECT.
   */
  const confirmarExportacao = async () => {
    if (!confirmRelatorio.mesInfo) return;
    setGerandoRelatorio(true);
    try {
      const reservasAgenda = await fetchAgendaReservas();
      const reservasDoMes = (reservasAgenda || []).filter((reserva) => {
        if (!reserva?.checkin) return false;
        const checkinDate = new Date(reserva.checkin);
        const chaveMes = `${checkinDate.getFullYear()}-${String(
          checkinDate.getMonth() + 1
        ).padStart(2, '0')}`;
        return chaveMes === confirmRelatorio.mesInfo.mes_ano;
      });
      gerarRelatorioMensalPDF(confirmRelatorio.mesInfo, reservasDoMes);
    } catch (err) {
      console.error('Falha ao gerar relatório mensal:', err);
      toast.error('Não foi possível gerar o relatório para este mês.');
    } finally {
      setGerandoRelatorio(false);
      setConfirmRelatorio({ visible: false, mesInfo: null });
    }
  };

  /**
   * Renderiza todo o conteúdo da página (cards + gráficos + modais).
   * Trata estados de carregamento/erro antes de exibir os dados.
   */
  const renderContent = () => {
    if (loading)
      return (
        <div className="gestao-loading-grid" aria-live="polite">
          <div className="gestao-loading-card" />
          <div className="gestao-loading-card" />
          <div className="gestao-loading-card" />
          <div className="gestao-loading-card" />
          <div className="gestao-loading-chart gestao-loading-chart-wide" />
          <div className="gestao-loading-chart" />
        </div>
      );

    if (error)
      return (
        <Alert variant="danger" className="gestao-error-alert">
          <Alert.Heading>Erro ao Carregar Indicadores</Alert.Heading>
          <p>{error}</p>
          <Button onClick={carregarIndicadores} variant="danger">
            <RefreshCw size={16} aria-hidden="true" />
            Tentar Novamente
          </Button>
        </Alert>
      );

    if (!indicadores) return <Alert variant="warning">Nenhum dado encontrado.</Alert>;

    const {
      kpis,
      taxa_ocupacao,
      faturamento_mensal,
      faturamento_por_tipo,
      pagamentos_pendentes = {},
      ano_filtrado,
    } = indicadores;
    const pagamentosValor = Number(pagamentos_pendentes?.valor_pendente || 0);
    const reservasPendentes = Number(pagamentos_pendentes?.reservas_em_aberto || 0);
    const temPendencias = pagamentosValor > 0 || reservasPendentes > 0;
    const diasVendidosFmt = formatNumber(taxa_ocupacao?.total_dias_vendidos || 0);
    const diasBaseFmt = formatNumber(taxa_ocupacao?.total_dias_base || 0);
    const barChartLabels = faturamento_mensal.map((item) => formatChartLabel(item.mes_ano));
    const barChartDataPoints = faturamento_mensal.map(
      (item) => parseFloat(item.faturamento_mensal) || 0
    );
    const ocupacaoMensal = faturamento_mensal.map(
      (item) => parseFloat(item.taxa_ocupacao_percent) || 0
    );
    /**
     * Handler do clique na barra de faturamento.
     * Abre o modal de confirmação, sem gerar PDF imediatamente.
     */
    const handleBarChartClick = (event, elements) => {
      if (!elements?.length) return;
      const clickedIndex = elements[0].index;
      setConfirmRelatorio({ visible: true, mesInfo: faturamento_mensal[clickedIndex] });
    };

    const barChartData = {
      labels: barChartLabels,
      datasets: [
        {
          label: 'Faturamento Mensal',
          data: barChartDataPoints,
          backgroundColor: 'rgba(38, 82, 44, 0.6)',
          borderColor: 'rgba(38, 82, 44, 1)',
          borderWidth: 1,
        },
        {
          type: 'line',
          label: 'Ocupação (%)',
          data: ocupacaoMensal,
          borderColor: '#F59F00',
          backgroundColor: 'rgba(245, 159, 0, 0.25)',
          fill: false,
          tension: 0.35,
          yAxisID: 'y1',
        },
      ],
    };

    const barChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      // Clique na barra => dispara geração do PDF daquele mês.
      onClick: handleBarChartClick,
      plugins: {
        legend: { position: 'bottom' },
        title: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => {
              const parsedValue =
                typeof context.parsed?.y !== 'undefined' ? context.parsed.y : context.parsed;
              if (context.dataset?.yAxisID === 'y1') {
                return `${context.dataset.label}: ${formatDecimal(parsedValue)}%`;
              }
              return `${context.dataset.label || ''}: ${formatCurrency(parsedValue)}`;
            },
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: (value) => formatCurrency(value),
          },
        },
        y1: {
          beginAtZero: true,
          position: 'right',
          grid: { drawOnChartArea: false },
          ticks: {
            callback: (value) => `${formatDecimal(value)}%`,
          },
          suggestedMax: 100,
        },
      },
    };

    const pieChartLabels = faturamento_por_tipo.map((item) => item.tipo_quarto);
    const pieChartDataPoints = faturamento_por_tipo.map((item) => item.faturamento_por_tipo);
    const pieChartData = {
      labels: pieChartLabels,
      datasets: [
        {
          label: 'Faturamento',
          data: pieChartDataPoints,
          backgroundColor: [
            'rgba(38, 82, 44, 0.7)',
            'rgba(98, 141, 56, 0.7)',
            'rgba(48, 51, 46, 0.7)',
          ],
          borderColor: '#ffffff',
          borderWidth: 1,
        },
      ],
    };

    const pieChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' },
        title: { display: false },
        tooltip: {
          callbacks: {
            label: (context) =>
              `${context.label}: ${formatCurrency(context.parsed || 0)}`,
          },
        },
      },
    };

    return (
      <>

        <Row className="gestao-kpi-row mb-4">
          <Col lg={3} md={6} className="mb-3">
            <Card className="kpi-card">
              <Card.Body>
                <Card.Title className="kpi-card-title">
                  Faturamento Total ({ano_filtrado})
                </Card.Title>
                <Card.Text className="kpi-card-value">
                  {formatCurrency(kpis.faturamento_total)}
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>

          <Col lg={3} md={6} className="mb-3">
            <Card className="kpi-card">
              <Card.Body>
                <Card.Title className="kpi-card-title">
                  Total de Reservas ({ano_filtrado})
                </Card.Title>
                <Card.Text className="kpi-card-value">{formatNumber(kpis.total_reservas)}</Card.Text>
              </Card.Body>
            </Card>
          </Col>

          <Col lg={3} md={6} className="mb-3">
            <Card className="kpi-card">
              <Card.Body>
                <Card.Title className="kpi-card-title">
                  Taxa de Ocupação ({ano_filtrado})
                </Card.Title>
                <Card.Text className="kpi-card-value">
                  {formatDecimal(taxa_ocupacao.taxa_ocupacao_percent)}%
                </Card.Text>
                <small className="kpi-subtext text-muted">
                  {diasVendidosFmt} dias vendidos de {diasBaseFmt} disponi­veis
                </small>
              </Card.Body>
            </Card>
          </Col>

          <Col lg={3} md={6} className="mb-3">
            <Card className={temPendencias ? 'kpi-card kpi-alert-card' : 'kpi-card'}>
              <Card.Body>
                <Card.Title className="kpi-card-title kpi-card-title-row">
                  <span>Pagamentos Pendentes</span>
                  {temPendencias && (
                    <Badge bg="danger" className="kpi-badge">
                      Atenção
                    </Badge>
                  )}
                </Card.Title>
                <Card.Text className="kpi-card-value">
                  {formatCurrency(pagamentosValor)}
                </Card.Text>
                <small className="kpi-subtext text-muted">
                  {reservasPendentes} reservas com cobrança aberta
                </small>
                <Button
                  variant="outline-danger"
                  size="sm"
                  className="kpi-action-button"
                  onClick={handleAbrirPendentesModal}
                  disabled={loadingPendentes}
                >
                  <AlertTriangle size={15} aria-hidden="true" />
                  Ver reservas em atraso
                </Button>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        <Row className="gestao-chart-row">
          <Col lg={8} className="mb-3 mb-lg-0">
            <Card className="financial-panel">
              <Card.Body>
                <div className="chart-panel-header">
                  <div>
                    <h2 className="chart-panel-title">
                      <BarChart2 size={18} aria-hidden="true" />
                      Faturamento e ocupação
                    </h2>
                    <p className="chart-panel-meta">
                      Últimos 12 meses com linha de ocupação por período.
                    </p>
                  </div>
                  <span className="chart-panel-hint">
                    <FileText size={15} aria-hidden="true" />
                    Clique em uma barra para exportar o mês
                  </span>
                </div>
                <div className="chart-container chart-container-primary">
                  {barChartDataPoints.length > 0 ? (
                    <Bar options={barChartOptions} data={barChartData} />
                  ) : (
                    <div className="chart-empty-state">
                      <BarChart2 size={22} aria-hidden="true" />
                      Nenhum faturamento para exibir.
                    </div>
                  )}
                </div>
              </Card.Body>
            </Card>
          </Col>

          <Col lg={4}>
            <Card className="financial-panel">
              <Card.Body>
                <div className="chart-panel-header chart-panel-header-compact">
                  <div>
                    <h2 className="chart-panel-title">
                      <BarChart2 size={18} aria-hidden="true" />
                      Receita por tipo
                    </h2>
                    <p className="chart-panel-meta">
                      Distribuição do faturamento em {ano_filtrado}.
                    </p>
                  </div>
                </div>
                <div className="chart-container chart-container-secondary">
                  {pieChartDataPoints.length > 0 ? (
                    <Doughnut options={pieChartOptions} data={pieChartData} />
                  ) : (
                    <div className="chart-empty-state">
                      <BarChart2 size={22} aria-hidden="true" />
                      Nenhum faturamento para agrupar.
                    </div>
                  )}
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        <Modal show={showPendentesModal} onHide={handleFecharPendentesModal} size="lg" centered>
          <Modal.Header closeButton>
            <Modal.Title>Reservas com pagamento pendente</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {loadingPendentes ? (
              <div className="text-center my-4">
                <Spinner animation="border" variant="danger" />
                <p className="mt-2">Carregando reservas em atraso...</p>
              </div>
            ) : erroPendentes ? (
              <Alert variant="danger">{erroPendentes}</Alert>
            ) : reservasPendentesLista.length === 0 ? (
              <p className="mb-0">Nenhuma reserva pendente encontrada neste momento.</p>
            ) : (
              <Table responsive hover size="sm" className="gestao-pendencias-table">
                <thead>
                  <tr>
                    <th>Reserva</th>
                    <th>Titular</th>
                    <th>Período</th>
                    <th>Status</th>
                    <th>Atraso</th>
                    <th>Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {reservasPendentesLista.map((reserva) => (
                    <tr key={reserva.id_reserva_quarto}>
                      <td>
                        <div className="pendencia-main">#{reserva.id_reserva}</div>
                        <div className="text-muted small">
                          Quarto {reserva.numero_quarto || '--'} {reserva.tipo_quarto || ''}
                        </div>
                      </td>
                      <td>
                        <div className="fw-semibold">{reserva.titular || '--'}</div>
                        <div className="text-muted small">{reserva.email_hospede || ''}</div>
                      </td>
                      <td>
                        <div className="pendencia-period">
                          <span>{formatDate(reserva.checkin)}</span>
                          <span>{formatDate(reserva.checkout)}</span>
                        </div>
                      </td>
                      <td>
                        <div className="pendencia-status-stack">
                          <Badge bg={STATUS_BADGE_VARIANT[reserva.status_reserva] || 'secondary'}>
                            {reserva.status_reserva}
                          </Badge>
                          <Badge bg={PAGAMENTO_BADGE_VARIANT[reserva.status_pagamento] || 'secondary'}>
                            {reserva.status_pagamento}
                          </Badge>
                        </div>
                      </td>
                      <td>
                        <span className="delay-pill">
                          {formatNumber(reserva.dias_desde_checkin)} dias
                        </span>
                      </td>
                      <td className="pendencia-value">{formatCurrency(reserva.valor_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={handleFecharPendentesModal}>
              Fechar
            </Button>
            <Button variant="danger" onClick={() => navigate('/agenda?status_pagamento=Pendente')}>
              Ir para Agenda
            </Button>
          </Modal.Footer>
        </Modal>
        <Modal
          show={confirmRelatorio.visible}
          onHide={() => setConfirmRelatorio({ visible: false, mesInfo: null })}
          centered
        >
          <Modal.Header closeButton>
            <Modal.Title>Exportar relatório mensal</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {confirmRelatorio.mesInfo && (
              <>
                <p className="mb-3">
                  Deseja gerar o relatório mensal para{' '}
                  <strong>{formatChartLabel(confirmRelatorio.mesInfo.mes_ano)}</strong>?
                </p>
                <p className="text-muted small">
                  O arquivo PDF incluirá os indicadores resumidos e a lista de reservas do mês.
                </p>
              </>
            )}
          </Modal.Body>
          <Modal.Footer>
            <Button
              variant="secondary"
              onClick={() => setConfirmRelatorio({ visible: false, mesInfo: null })}
              disabled={gerandoRelatorio}
            >
              Cancelar
            </Button>
            <Button
              variant="success"
              className="modal-primary-action"
              onClick={confirmarExportacao}
              disabled={gerandoRelatorio}
            >
              {gerandoRelatorio ? (
                <>
                  <Spinner size="sm" animation="border" aria-hidden="true" />
                  Gerando...
                </>
              ) : (
                <>
                  <FileText size={16} aria-hidden="true" />
                  Gerar Relatório
                </>
              )}
            </Button>
          </Modal.Footer>
        </Modal>
      </>
    );
  };

  return (
    <div className="gestao-page">
      <div className="page-header">
        <div className="page-title-block">
          <h1>Gestão Aguapé</h1>
          <span className="page-title-meta">Relatórios, indicadores e pendências financeiras</span>
        </div>
        <div className="gestao-toolbar">
          <div className="gestao-toolbar-actions">
            <Button
              variant="outline-secondary"
              className="gestao-toolbar-button"
              onClick={carregarIndicadores}
              disabled={loading}
            >
              <RefreshCw size={16} aria-hidden="true" />
              Atualizar
            </Button>
            <Button
              variant="outline-danger"
              className="gestao-toolbar-button"
              onClick={handleAbrirPendentesModal}
              disabled={loadingPendentes}
            >
              <AlertTriangle size={16} aria-hidden="true" />
              Pendências
            </Button>
          </div>
          <div className="gestao-year-select">
            <Form.Select
              value={anoSelecionado}
              onChange={(e) => setAnoSelecionado(Number(e.target.value))}
              disabled={loading}
              aria-label="Selecionar Ano"
            >
              {anosDisponiveis.map((ano) => (
                <option key={ano} value={ano}>
                  {ano}
                </option>
              ))}
            </Form.Select>
          </div>
        </div>
      </div>
      <div className="page-content">{renderContent()}</div>
    </div>
  );
};

export default GestaoPage;


