/**
 * GanttChart.js
 * --------------
 * Encapsula o componente `react-calendar-timeline` usado na Agenda.
 * Recebe quartos/reservas, transforma no formato `groups/items` exigido
 * pela biblioteca e aplica renderização customizada com ícones/cores.
 */
import React, { useMemo } from 'react';
import Timeline, {
  DateHeader,
  SidebarHeader,
  TimelineHeaders,
  TimelineMarkers,
  TodayMarker,
} from 'react-calendar-timeline';
import moment from 'moment';
import 'moment/locale/pt-br';
import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';
import 'react-calendar-timeline/style.css';
import './GanttChart.css';
import { DollarSign, Clock, XCircle, AlertCircle } from 'react-feather';

moment.locale('pt-br');
dayjs.locale('pt-br');

const capitalizeFirst = (value) => value.charAt(0).toUpperCase() + value.slice(1);
const WEEKDAY_LABELS_SHORT = ['dom.', 'seg.', 'ter.', 'qua.', 'qui.', 'sex.', 'sáb.'];
const MIN_COMPACT_DAY_LABEL_WIDTH = 24;
const MIN_FULL_DAY_LABEL_WIDTH = 90;

const toLocalizedMoment = (value) => moment(value?.valueOf ? value.valueOf() : value).locale('pt-br');

const getHeaderLabelWidth = (interval, intervalProps) => {
  const rawWidth = interval?.labelWidth ?? intervalProps?.style?.width ?? 0;
  const numericWidth = typeof rawWidth === 'number' ? rawWidth : Number.parseFloat(String(rawWidth));

  return Number.isFinite(numericWidth) ? numericWidth : 0;
};

const formatMonthHeader = ([startTime], unit, labelWidth = 0) => {
  const localizedStart = startTime.locale('pt-br');

  if (unit === 'year') {
    return localizedStart.format('YYYY');
  }

  if (labelWidth < 70) {
    return capitalizeFirst(localizedStart.format('MMM').replace('.', ''));
  }

  if (labelWidth < 150) {
    return capitalizeFirst(localizedStart.format('MMM YYYY').replace('.', ''));
  }

  return capitalizeFirst(localizedStart.format('MMMM [de] YYYY'));
};

const formatDayHeader = ([startTime], _unit, labelWidth = 0) => {
  const localizedStart = toLocalizedMoment(startTime);

  if (labelWidth < 34) {
    return localizedStart.format('D');
  }

  return localizedStart.format('D');
};

const formatSecondaryHeader = ([startTime], unit, labelWidth = 0) => {
  const localizedStart = toLocalizedMoment(startTime);

  if (unit === 'day') {
    return formatDayHeader([startTime], unit, labelWidth);
  }

  if (unit === 'month') {
    const monthLabel = localizedStart.format('MMM').replace('.', '');
    return labelWidth < 80
      ? capitalizeFirst(monthLabel)
      : capitalizeFirst(localizedStart.format('MMM YYYY').replace('.', ''));
  }

  if (unit === 'year') {
    return localizedStart.format('YYYY');
  }

  return localizedStart.format('D');
};

const getWeekdayHeaderLabel = (date, labelWidth) =>
  labelWidth >= MIN_FULL_DAY_LABEL_WIDTH ? date.format('dddd') : WEEKDAY_LABELS_SHORT[date.day()];

const secondaryHeaderRenderer = ({ getIntervalProps, intervalContext }) => {
  const { interval, intervalText } = intervalContext;
  const { key, ...intervalProps } = getIntervalProps();
  const localizedStart = toLocalizedMoment(interval.startTime);
  const intervalHours = toLocalizedMoment(interval.endTime).diff(localizedStart, 'hours');
  const isDayInterval = intervalHours <= 36;
  const labelWidth = getHeaderLabelWidth(interval, intervalProps);
  const isFullDayLabel = labelWidth >= MIN_FULL_DAY_LABEL_WIDTH;

  return (
    <div key={key} {...intervalProps} className="rct-dateHeader timeline-dateHeader-secondary">
      {isDayInterval && labelWidth >= MIN_COMPACT_DAY_LABEL_WIDTH ? (
        <span className={`timeline-day-label ${isFullDayLabel ? 'timeline-day-label-full' : ''}`}>
          <span>{getWeekdayHeaderLabel(localizedStart, labelWidth)}</span>
          <strong>{localizedStart.format('D')}</strong>
        </span>
      ) : (
        <span>{intervalText}</span>
      )}
    </div>
  );
};

const formatDate = (value) => moment(value).format('DD/MM/YYYY');

const buildReservaTooltip = (reserva) => ([
  `Reserva #${reserva.id_reserva || '-'}`,
  `Hospede: ${reserva.nome_titular || 'Nao informado'}`,
  `Quarto: ${reserva.numero_quarto || reserva.id_quarto || '-'}`,
  `Barco: ${reserva.nome_barco || 'Nao informado'}`,
  `Passeio: ${reserva.tipo_passeio || 'Nao informado'}`,
  `Check-in: ${formatDate(reserva.checkin)}`,
  `Checkout: ${formatDate(reserva.checkout)}`,
  `Reserva: ${reserva.status_reserva || '-'}`,
  `Pagamento: ${reserva.status_pagamento || '-'}`,
].join('\n'));

// =========================================================
// 🔹 Processa dados vindos da API Django
// =========================================================
// Converte os dados crus (quartos/reservas) em groups/items compatíveis
// com o react-calendar-timeline.
/**
 * Transforma os dados vindos da API Django no formato exigido pelo
 * `react-calendar-timeline`.
 *
 * @param {Array} quartosData - coleção retornada pelo endpoint de quartos.
 * @param {Array} reservasData - reservas com check-in/out vindas da agenda.
 * @returns {{groups: Array, items: Array}} objeto pronto para o Timeline.
 */
const processDataForTimeline = (quartosData = [], reservasData = []) => {
  const groups = quartosData.map(q => ({
    id: q.id_quarto,
    title: `${q.numero} (${q.tipo_quarto})`,
  }));

  const items = [];

  reservasData.forEach((r, index) => {
    try {
      // Ignora registros incompletos para evitar itens quebrados no timeline.
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
        checkin: r.checkin,
        checkout: r.checkout,
        id_reserva: r.id_reserva,
        numero_quarto: r.numero_quarto,
        status_pagamento: r.status_pagamento || null,
        status_reserva: r.status_reserva || null,
        titular,
        tooltip: buildReservaTooltip(r),
      });
    } catch (error) {
      console.error(`Erro ao processar item ${index}:`, error);
    }
  });

  return { groups, items };
};

const groupRenderer = ({ group }) => {
  const [, numero = group.title, tipo = ''] = /^(.+?)\s*\((.+)\)$/.exec(group.title) || [];

  return (
    <div className="timeline-room">
      <span className="timeline-room-number">{numero}</span>
      {tipo && <span className="timeline-room-type">{tipo}</span>}
    </div>
  );
};

// =========================================================
// Renderizador customizado com ícones
// =========================================================
/**
 * Renderer customizado responsável por aplicar ícones de status
 * e ajustar o estilo inline fornecido pela lib.
 *
 * @param {object} item - recebe os dados do Timeline (inclui payload extra).
 * @param {function} getItemProps - função da lib para obter props/estilos.
 */
const itemRenderer = ({ item, itemContext, getItemProps }) => {
  const isCompact = (itemContext?.dimensions?.width || 0) < 120;

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
    className: `${item.className} ${isCompact ? 'timeline-item-compact' : ''}`,
    title: item.tooltip,
    style: {
      lineHeight: 'normal',     // evita vertical-align baseado em line-height
      display: 'block',         // mantém a estrutura
    }
  });

  return (
    <div {...itemProps}>
      {/* Wrapper interno controlado: ocupa 100%, flex centralizado */}
      <div className="rct-item-content" style={{ height: '100%' }}>
        <span className="timeline-item-label">
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
/**
 * Componente que orquestra o Timeline da agenda, recebendo os dados
 * já carregados pelo backend e repassando eventos para o dashboard.
 *
 * @param {Array} quartosData - lista de quartos disponíveis.
 * @param {Array} reservasData - reservas renderizadas no Gantt.
 * @param {number} visibleTimeStart/visibleTimeEnd - janelas visíveis (ms).
 * @param {function} onTimeChange - callback disparado ao navegar.
 * @param {function} onItemClick - callback para abrir modais de reserva.
 */
function GanttChart({
  quartosData,
  reservasData,
  visibleTimeStart,
  visibleTimeEnd,
  onTimeChange,
  onItemClick,
  }) {
  const { groups, items } = useMemo(
    () => processDataForTimeline(quartosData, reservasData),
    [quartosData, reservasData]
  );

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
        groupRenderer={groupRenderer}
        itemRenderer={itemRenderer}
      >
        <TimelineHeaders>
          <SidebarHeader>
            {({ getRootProps }) => (
              <div {...getRootProps({ style: { height: 60 } })} className="timeline-sidebar-header">
                Quartos
              </div>
            )}
          </SidebarHeader>
          <DateHeader unit="primaryHeader" labelFormat={formatMonthHeader} />
          <DateHeader labelFormat={formatSecondaryHeader} intervalRenderer={secondaryHeaderRenderer} />
        </TimelineHeaders>
        <TimelineMarkers>
          <TodayMarker>
            {({ styles }) => (
              <div
                className="timeline-today-marker"
                style={{
                  ...styles,
                  width: '2px',
                }}
              />
            )}
          </TodayMarker>
        </TimelineMarkers>
      </Timeline>
      {items.length === 0 && (
        <div className="timeline-empty-state">
          Nenhuma reserva encontrada para os filtros atuais.
        </div>
      )}
    </div>
  );
}

export default GanttChart;
