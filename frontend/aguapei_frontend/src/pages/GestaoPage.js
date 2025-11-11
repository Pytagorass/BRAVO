import React, { useState, useEffect } from 'react';
import { fetchIndicadoresGestao } from '../services/api';
import { Row, Col, Spinner, Alert, Button, Form, Card } from 'react-bootstrap';
import './GestaoPage.css';

import { Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

Chart.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend);

const formatCurrency = (value) => {
  const numberValue = parseFloat(value) || 0;
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(numberValue);
};

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

const GestaoPage = () => {
  const [indicadores, setIndicadores] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [anoSelecionado, setAnoSelecionado] = useState(new Date().getFullYear());
  const anosDisponiveis = [0, 1, 2, 3].map((i) => new Date().getFullYear() - i);

  useEffect(() => {
    const carregarIndicadores = async () => {
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
    };
    carregarIndicadores();
  }, [anoSelecionado]);

  const renderContent = () => {
    if (loading)
      return (
        <div className="text-center p-5">
          <Spinner animation="border" variant="success" />
          <p>Carregando indicadores...</p>
        </div>
      );

    if (error)
      return (
        <Alert variant="danger">
          <Alert.Heading>Erro ao Carregar Indicadores</Alert.Heading>
          <p>{error}</p>
          <Button onClick={() => setAnoSelecionado(anoSelecionado)} variant="danger">
            Tentar Novamente
          </Button>
        </Alert>
      );

    if (!indicadores) return <Alert variant="warning">Nenhum dado encontrado.</Alert>;

    const { kpis, taxa_ocupacao, faturamento_mensal, faturamento_por_tipo } = indicadores;

    const barChartLabels = faturamento_mensal.map((item) => formatChartLabel(item.mes_ano));
    const barChartDataPoints = faturamento_mensal.map((item) => item.faturamento_mensal);
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
      ],
    };

    const barChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        title: { display: true, text: 'Faturamento Mensal (Últimos 12 Meses)' },
        tooltip: {
          callbacks: {
            label: (context) =>
              `${context.dataset.label || ''}: ${formatCurrency(context.parsed.y)}`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: (value) => 'R$ ' + value / 1000 + 'k',
          },
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
        legend: { position: 'top' },
        title: {
          display: true,
          text: `Faturamento por Tipo de Quarto (${indicadores.ano_filtrado})`,
        },
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
        <Row className="mb-4">
          <Col md={4} className="mb-3 mb-md-0">
            <Card className="kpi-card">
              <Card.Body>
                <Card.Title className="kpi-card-title">
                  Faturamento Total ({indicadores.ano_filtrado})
                </Card.Title>
                <Card.Text className="kpi-card-value">
                  {formatCurrency(kpis.faturamento_total)}
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>

          <Col md={4} className="mb-3 mb-md-0">
            <Card className="kpi-card">
              <Card.Body>
                <Card.Title className="kpi-card-title">
                  Total de Reservas ({indicadores.ano_filtrado})
                </Card.Title>
                <Card.Text className="kpi-card-value">{kpis.total_reservas}</Card.Text>
              </Card.Body>
            </Card>
          </Col>

          <Col md={4}>
            <Card className="kpi-card">
              <Card.Body>
                <Card.Title className="kpi-card-title">
                  Taxa de Ocupação ({indicadores.ano_filtrado})
                </Card.Title>
                <Card.Text className="kpi-card-value">
                  {parseFloat(taxa_ocupacao.taxa_ocupacao_percent).toFixed(2)}%
                </Card.Text>
                <small className="text-muted">
                  {taxa_ocupacao.total_dias_vendidos} dias vendidos de{' '}
                  {taxa_ocupacao.total_dias_base} disponíveis
                </small>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        <Row>
          <Col md={8} className="mb-3 mb-md-0">
            <Card className="financial-panel">
              <Card.Body>
                <div className="chart-container" style={{ position: 'relative', height: '400px' }}>
                  {barChartDataPoints.length > 0 ? (
                    <Bar options={barChartOptions} data={barChartData} />
                  ) : (
                    <p>Nenhum faturamento para exibir.</p>
                  )}
                </div>
              </Card.Body>
            </Card>
          </Col>

          <Col md={4}>
            <Card className="financial-panel">
              <Card.Body>
                <div className="chart-container" style={{ position: 'relative', height: '400px' }}>
                  {pieChartDataPoints.length > 0 ? (
                    <Doughnut options={pieChartOptions} data={pieChartData} />
                  ) : (
                    <p>Nenhum faturamento para agrupar.</p>
                  )}
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </>
    );
  };

  return (
    <div className="gestao-page">
      <div className="page-header">
        <h1>Gestão Aguapeí - Relatórios e Indicadores</h1>
        <div style={{ width: '200px' }}>
          <Form.Select
            value={anoSelecionado}
            onChange={(e) => setAnoSelecionado(e.target.value)}
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
      <div className="page-content">{renderContent()}</div>
    </div>
  );
};

export default GestaoPage;
