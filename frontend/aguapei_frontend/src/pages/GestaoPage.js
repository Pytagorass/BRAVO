import React, { useState, useEffect } from 'react';
import { fetchIndicadoresGestao } from '../services/api';
import { Row, Col, Spinner, Alert } from 'react-bootstrap';
// import MainLayout from '../layouts/MainLayout';
import './GestaoPage.css';

// ==========================================================
// 1. IMPORTAÇÕES DO CHART.JS
// ==========================================================
import { Bar } from 'react-chartjs-2';
import {
    Chart,
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
} from 'chart.js';

// ==========================================================
// 2. REGISTRO DOS COMPONENTES DO GRÁFICO
// (Obrigatório para o Chart.js v3+)
// ==========================================================
Chart.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend
);


// Função helper para formatar dinheiro (R$) (sem mudanças)
const formatCurrency = (value) => {
    const numberValue = parseFloat(value) || 0;
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(numberValue);
};

const GestaoPage = () => {
    const [indicadores, setIndicadores] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const carregarIndicadores = async () => {
            try {
                setLoading(true);
                const response = await fetchIndicadoresGestao();
                setIndicadores(response.data);
                setError(null);
            } catch (err) {
                setError('Falha ao carregar os indicadores de gestão.');
                console.error('Erro detalhado:', err);
            } finally {
                setLoading(false);
            }
        };

        carregarIndicadores();
    }, []);

    // Função para renderizar o conteúdo principal
    const renderContent = () => {
        if (loading) {
            return (
                <div className="text-center">
                    <Spinner animation="border" variant="success" />
                    <p>Carregando indicadores...</p>
                </div>
            );
        }

        if (error) {
            return <Alert variant="danger">{error}</Alert>;
        }

        if (!indicadores) {
            return <Alert variant="warning">Nenhum dado de gestão encontrado.</Alert>;
        }

        // ==========================================================
        // 3. TRANSFORMAÇÃO DE DADOS (API -> Gráfico)
        // ==========================================================
        const { kpis, faturamento_mensal } = indicadores;
        
        // O backend manda os dados ordenados (DESC). Para o gráfico,
        // é melhor ter os mais antigos primeiro (ASC), por isso usamos .reverse().
        const faturamentoReverso = [...faturamento_mensal].reverse();

        // Mapeia o array de objetos para dois arrays simples
        const chartLabels = faturamentoReverso.map(item => item.mes_ano);
        const chartDataPoints = faturamentoReverso.map(item => item.faturamento_mensal);

        // Objeto de dados que o <Bar> espera
        const chartData = {
            labels: chartLabels,
            datasets: [
                {
                    label: 'Faturamento Mensal',
                    data: chartDataPoints,
                    backgroundColor: 'rgba(38, 82, 44, 0.6)', // Verde do seu protótipo
                    borderColor: 'rgba(38, 82, 44, 1)',
                    borderWidth: 1,
                },
            ],
        };

        // Objeto de opções para o <Bar>
        const chartOptions = {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top', // Posição da legenda
                },
                title: {
                    display: true,
                    text: 'Faturamento Total Mensal', // Título do gráfico [cite: 488]
                },
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        };

        // ==========================================================
        // 4. RENDERIZAÇÃO DO JSX
        // ==========================================================
        return (
            <>
                {/* 1. Linha dos Cards (KPIs) (sem mudanças) */}
                <Row className="mb-4">
                    <Col md={6}>
                        <div className="kpi-card">
                            <div className="kpi-card-title">Faturamento Total</div>
                            <div className="kpi-card-value">
                                {formatCurrency(kpis.faturamento_total)}
                            </div>
                        </div>
                    </Col>
                    
                    <Col md={6}>
                        <div className="kpi-card">
                            <div className="kpi-card-title">Total de Reservas</div>
                            <div className="kpi-card-value">
                                {kpis.total_reservas}
                            </div>
                        </div>
                    </Col>
                </Row>

                {/* 2. Painel de Faturamento Mensal (AGORA COM O GRÁFICO) */}
                <div className="financial-panel">
                    <h2>Painel Financeiro</h2>
                    
                    {/* Substituímos a <ul> por <Bar> */}
                    {chartDataPoints.length > 0 ? (
                        <Bar options={chartOptions} data={chartData} />
                    ) : (
                        <p>Nenhum dado de faturamento mensal para exibir no gráfico.</p>
                    )}
                </div>
            </>
        );
    };

    return (
        // <MainLayout>
            <div className="gestao-page">
                <div className="page-header">
                    <h1>Gestão Aguapeí - Relatórios e Indicadores</h1>
                </div>
                
                <div className="page-content">
                    {renderContent()}
                </div>
            </div>
        // </MainLayout>
    );
};

export default GestaoPage;