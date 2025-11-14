import React from 'react';
import Timeline, { TimelineMarkers, TodayMarker } from 'react-calendar-timeline';
import moment from 'moment';
import 'moment/locale/pt-br';
import 'react-calendar-timeline/style.css';
import './GanttChart.css';
import { DollarSign, Clock, XCircle, AlertCircle } from 'react-feather';

moment.locale('pt-br');

// =========================================================
// 🔹 Processa dados vindos da API Django
// =========================================================
const processDataForTimeline = (quartosData = [], reservasData = []) => {
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
      const endTime = moment(r.checkout).add(1, 'day').valueOf(); // use add(1,'day') se precisar incluir a data do checkout
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
        // Dados extras para o renderer
        status_pagamento: r.status_pagamento || null,
        status_reserva: r.status_reserva || null,
      });
    } catch (error) {
      console.error(`Erro ao processar item ${index}:`, error);
    }
  });

  console.log("GanttChart.js [DEBUG]: Dados processados:", { groups, items });
  return { groups, items };
};

// =========================================================
// 🔹 Renderizador customizado com ícones (refinado)
// =========================================================
const itemRenderer = ({ item, getItemProps }) => {
  const getIcon = () => {
    if (item.status_reserva === 'Cancelada') return <XCircle className="item-icon" />;
    if (item.status_pagamento === 'Pago') return <DollarSign className="item-icon" />;
    if (item.status_reserva === 'Ativa') return <DollarSign className="item-icon" />;
    if (item.status_pagamento === 'Em Partes') return <AlertCircle className="item-icon" />;
    if (item.status_pagamento === 'Pendente') return <Clock className="item-icon" />;
    return <Clock className="item-icon" />; // fallback
  };

  // Neutraliza line-height inline da biblioteca e garante altura total
  const itemProps = getItemProps({
    className: item.className, // aplica cor/status
    style: {
      lineHeight: 'normal',     // 🔧 evita vertical-align baseado em line-height
      display: 'block',         // mantém a estrutura
    }
  });

  return (
    <div {...itemProps}>
      {/* Wrapper interno controlado: ocupa 100%, flex centralizado */}
      <div className="rct-item-content" style={{ height: '100%' }}>
        <span className="d-inline-flex align-items-center gap-2">
          {getIcon()}
          {item.title || 'Reserva sem título'}
        </span>
      </div>
    </div>
  );
};

// =========================================================
// 🔹 Componente principal
// =========================================================
function GanttChart({
  quartosData,
  reservasData,
  visibleTimeStart,
  visibleTimeEnd,
  onTimeChange,
  onItemClick,
  }) {
  const { groups, items } = processDataForTimeline(quartosData, reservasData);

  return (
    <div className="timeline-container">
      <Timeline
        groups={groups}
        items={items}
        visibleTimeStart={visibleTimeStart}
        visibleTimeEnd={visibleTimeEnd}
        onTimeChange={onTimeChange}
        calendarHeaderUnit="month"
        calendarSubHeaderUnit="day"
        headerLabelFormats={{
          dayShort: { format: 'ddd DD/MM' },
          monthShort: { format: 'MMMM [de] YYYY' },
        }}
        timeSteps={{ day: 1, month: 1, year: 1 }}
        defaultTimeStart={moment().startOf('month')}
        defaultTimeEnd={moment().endOf('month')}
        sidebarWidth={200}
        lineHeight={60}
        itemHeightRatio={0.85}
        canMove={false}
        canResize={false}
        stackItems
        canOverlap={false}
        onItemClick={onItemClick}
        itemRenderer={itemRenderer}
      >
        <TimelineMarkers>
          <TodayMarker>
            {({ styles }) => (
              <div
                style={{
                  ...styles,
                  backgroundColor: 'rgba(220, 53, 69, 0.7)',
                  width: '3px',
                }}
              />
            )}
          </TodayMarker>
        </TimelineMarkers>
      </Timeline>
    </div>
  );
}

export default GanttChart;
