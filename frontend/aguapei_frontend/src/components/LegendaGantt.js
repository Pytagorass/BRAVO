import React from 'react';
// Importa os ícones que você já usa no Gantt
import { DollarSign, Clock, XCircle, AlertCircle } from 'react-feather';
import './LegendaGantt.css'; // Vamos criar este arquivo de CSS

const LegendaGantt = () => {
    return (
        <div className="gantt-legenda">
            <div className="legenda-titulo">Legenda</div>

            {/* Seção para as CORES */}
            <div className="legenda-secao">
                <strong>Status da Reserva (Cor)</strong>
                <div className="legenda-item">
                    <span className="cor-box item-ativo"></span> Ativa / Paga
                </div>
                <div className="legenda-item">
                    <span className="cor-box item-pendente"></span> Agendada
                </div>
                <div className="legenda-item">
                    <span className="cor-box item-em-partes"></span> Pago em Partes
                </div>
                <div className="legenda-item">
                    <span className="cor-box item-cancelado"></span> Cancelada
                </div>
            </div>

            {/* Seção para os ÍCONES */}
            <div className="legenda-secao">
                <strong>Status do Pagamento (Ícone)</strong>
                <div className="legenda-item">
                    <DollarSign size={14} className="legenda-icon" /> Pago Total
                </div>
                <div className="legenda-item">
                    <AlertCircle size={14} className="legenda-icon" /> Em Partes
                </div>
                <div className="legenda-item">
                    <Clock size={14} className="legenda-icon" /> Pendente
                </div>
                <div className="legenda-item">
                    <XCircle size={14} className="legenda-icon" /> Cancelada
                </div>
            </div>
        </div>
    );
};

export default LegendaGantt;