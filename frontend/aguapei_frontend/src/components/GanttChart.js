import React from 'react';
import Timeline from 'react-calendar-timeline';
import moment from 'moment';
import 'moment/locale/pt-br';
import 'react-calendar-timeline/style.css';
import './GanttChart.css';
import { DollarSign, Clock, XCircle, AlertCircle } from 'react-feather';

// Aplica o idioma português globalmente
moment.locale('pt-br');

// =========================================================
// 🔹 Processa dados vindos da API Django
// =========================================================
const processDataForTimeline = (quartosData, reservasData) => {
  console.log("GanttChart.js [DEBUG]: Dados brutos recebidos:", { quartosData, reservasData });

  const groups = quartosData.map(q => ({
    id: q.id_quarto,
    title: `${q.numero} (${q.tipo_quarto})`,
  }));

  const items = [];

  reservasData.forEach((r, index) => {
    try {
      if (!r.checkin || !r.checkout || !r.id_quarto) return;

      const startTime = moment(r.checkin).valueOf();
      const endTime = moment(r.checkout).add(1, 'day').valueOf();
      if (isNaN(startTime) || isNaN(endTime)) return;

      const titular = r.nome_titular || 'Hóspede';
      const quartoId = r.id_quarto;

      const getStatusClass = (reservaStatus, pagtoStatus) => {
        if (reservaStatus === 'Cancelada') return 'item-cancelado';
        if (reservaStatus === 'Ativa') return 'item-ativo';
        if (pagtoStatus === 'Pago') return 'item-pago';
        if (pagtoStatus === 'Em Partes') return 'item-em-partes';
        return 'item-pendente';
      };

      items.push({
        id: r.id_reserva_quarto,
        group: quartoId,
        title: `Reserva #${r.id_reserva} - ${titular}`,
        start_time: startTime,
        end_time: endTime,
        className: getStatusClass(r.status_reserva, r.status_pagamento),
      });
    } catch (error) {
      console.error(`Erro ao processar item ${index}:`, error);
    }
  });

  console.log("GanttChart.js [DEBUG]: Dados processados:", { groups, items });
  return { groups, items };
};

// =========================================================
// 🔹 Renderizador customizado com ícones
// =========================================================
const itemRenderer = ({ item, getItemProps }) => {
  const getIcon = () => {
    if (item.className.includes('pago')) return <DollarSign className="item-icon" />;
    if (item.className.includes('ativo')) return <DollarSign className="item-icon" />;
    if (item.className.includes('pendente')) return <Clock className="item-icon" />;
    if (item.className.includes('cancelado')) return <XCircle className="item-icon" />;
    if (item.className.includes('em-partes')) return <AlertCircle className="item-icon" />;
    return null;
  };

  return (
    <div {...getItemProps()}>
      <div className="rct-item-content">
        {getIcon()}
        <span>{item.title}</span>
      </div>
    </div>
  );
};

// =========================================================
// 🔹 Componente principal com tradução pt-BR
// =========================================================
function GanttChart({
  quartos,
  reservas,
  visibleTimeStart,
  visibleTimeEnd,
  onTimeChange,
  onItemClick,
}) {
  const { groups, items } = processDataForTimeline(quartos, reservas);

  return (
    <div className="timeline-container">
      <Timeline
        groups={groups}
        items={items}
        visibleTimeStart={visibleTimeStart}
        visibleTimeEnd={visibleTimeEnd}
        onTimeChange={onTimeChange}

        /* Cabeçalhos e datas em português */
        calendarHeaderUnit="month"
        calendarSubHeaderUnit="day"
        headerLabelFormats={{
          dayShort: { format: 'ddd DD/MM' },           // ex: seg 10/11
          monthShort: { format: 'MMMM [de] YYYY' },    // ex: novembro de 2025
        }}

        /* Garantia de uso do locale pt-BR */
        timeSteps={{
          second: 1,
          minute: 1,
          hour: 1,
          day: 1,
          month: 1,
          year: 1,
        }}
        defaultTimeStart={moment().startOf('month')}
        defaultTimeEnd={moment().endOf('month')}

        /* Aparência e comportamento */
        sidebarWidth={200}
        lineHeight={60}
        itemHeightRatio={0.75}
        canMove
        canResize
        stackItems
        canOverlap={false}
        onItemClick={onItemClick}
        itemRenderer={itemRenderer}
      />
    </div>
  );
}

export default GanttChart;
