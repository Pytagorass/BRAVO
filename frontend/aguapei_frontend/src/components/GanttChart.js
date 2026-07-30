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
import { DollarSign, Clock, XCircle, AlertCircle, CheckCircle, Navigation } from 'react-feather';

moment.locale('pt-br');
dayjs.locale('pt-br');

const capitalizeFirst = (value) => value.charAt(0).toUpperCase() + value.slice(1);
const WEEKDAY_LABELS_SHORT = ['dom.', 'seg.', 'ter.', 'qua.', 'qui.', 'sex.', 'sáb.'];
const MIN_COMPACT_DAY_LABEL_WIDTH = 24;
const MIN_FULL_DAY_LABEL_WIDTH = 90;
const UNASSIGNED_BOAT_GROUP_ID = -1;

const toLocalizedMoment = (value) => moment(value?.valueOf ? value.valueOf() : value).locale('pt-br');

const normalizeBoatGroupId = (barcoId) => {
  const numericId = Number(barcoId);
  return Number.isFinite(numericId) ? numericId : null;
};

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

const formatDate = (value) => {
  const parsedDate = moment(value);
  return value && parsedDate.isValid() ? parsedDate.format('DD/MM/YYYY') : '-';
};

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

const buildBarcoTooltip = (reserva) => ([
  `Reserva #${reserva.id_reserva || '-'}`,
  `Hospede: ${reserva.nome_titular || 'Nao informado'}`,
  `Barco: ${reserva.nome_barco || 'A definir'}`,
  `Passeio: ${reserva.tipo_passeio || 'Nao informado'}`,
  `Embarque: ${formatDate(reserva.data_embarque)}`,
  `Desembarque: ${formatDate(reserva.data_desembarque)}`,
  `Periodo no grafico: ${reserva.data_embarque && reserva.data_desembarque ? 'Operação' : 'Hospedagem'}`,
  `Operação: ${reserva.status_operacional || 'A Preparar'}`,
  `Reserva: ${reserva.status_reserva || '-'}`,
].join('\n'));

const getReservaStatusClass = (reservaStatus, pagtoStatus) => {
  if (reservaStatus === 'Cancelada') return 'item-cancelado';
  if (reservaStatus === 'Ativa') return 'item-ativo';
  if (pagtoStatus === 'Pago') return 'item-pago';
  if (pagtoStatus === 'Em Partes') return 'item-em-partes';
  return 'item-pendente';
};

const getOperacaoStatusClass = (operacaoStatus, reservaStatus) => {
  if (reservaStatus === 'Cancelada') return 'item-cancelado';
  if (operacaoStatus === 'Pronto') return 'item-operacao-pronto';
  if (operacaoStatus === 'Em Viagem') return 'item-operacao-viagem';
  if (operacaoStatus === 'Finalizado') return 'item-operacao-finalizado';
  return 'item-operacao-preparar';
};

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
const processDataForTimeline = ({
  quartosData = [],
  barcosData = [],
  reservasData = [],
  resourceType = 'quartos',
}) => {
  const isBarcosView = resourceType === 'barcos';
  const barcosDisponiveis = isBarcosView
    ? barcosData.filter((barco) => barco.status_barco === 'Disponível')
    : [];
  const barcosDisponiveisIds = new Set(
    barcosDisponiveis
      .map((barco) => normalizeBoatGroupId(barco.id_barco))
      .filter((barcoId) => barcoId !== null)
  );
  const reservasPorRecurso = new Map();
  const reservasContadas = new Set();

  if (isBarcosView) {
    reservasData.forEach((reserva) => {
      const barcoGroupId = normalizeBoatGroupId(reserva.fk_barco);
      const hasTimelineDates = (
        (reserva.data_embarque && reserva.data_desembarque) ||
        (reserva.checkin && reserva.checkout)
      );

      if (
        !reserva.id_reserva ||
        !hasTimelineDates ||
        reservasContadas.has(reserva.id_reserva)
      ) {
        return;
      }

      if (barcoGroupId && !barcosDisponiveisIds.has(barcoGroupId)) return;

      const groupId = barcoGroupId || UNASSIGNED_BOAT_GROUP_ID;
      reservasContadas.add(reserva.id_reserva);
      reservasPorRecurso.set(groupId, (reservasPorRecurso.get(groupId) || 0) + 1);
    });
  }

  const hasReservasSemBarco = isBarcosView && reservasData.some((reserva) => {
    const hasTimelineDates = (
      (reserva.data_embarque && reserva.data_desembarque) ||
      (reserva.checkin && reserva.checkout)
    );

    return reserva.id_reserva && !normalizeBoatGroupId(reserva.fk_barco) && hasTimelineDates;
  });

  const groups = isBarcosView
    ? [
        ...(hasReservasSemBarco ? [{
          id: UNASSIGNED_BOAT_GROUP_ID,
          title: 'Sem barco definido',
          type: 'sem-barco',
          meta: 'Reserva pendente',
          status: 'A definir',
          count: reservasPorRecurso.get(UNASSIGNED_BOAT_GROUP_ID) || 0,
        }] : []),
        ...barcosDisponiveis.map((barco) => ({
          id: normalizeBoatGroupId(barco.id_barco),
          title: barco.nome_barco,
          type: 'barco',
          meta: `${barco.capacidade_pessoas || 0} pessoas`,
          status: barco.status_barco,
          count: reservasPorRecurso.get(normalizeBoatGroupId(barco.id_barco)) || 0,
        })),
      ]
    : quartosData.map((quarto) => ({
        id: quarto.id_quarto,
        title: quarto.numero,
        type: 'quarto',
        meta: quarto.tipo_quarto,
      }));

  const items = [];
  const reservasBarcoProcessadas = new Set();

  reservasData.forEach((r, index) => {
    try {
      const titular = r.nome_titular || 'Hóspede';

      if (isBarcosView) {
        const startDate = r.data_embarque || r.checkin;
        const endDate = r.data_desembarque || r.checkout;
        if (!startDate || !endDate || !r.id_reserva) return;
        if (reservasBarcoProcessadas.has(r.id_reserva)) return;

        const startTime = moment(startDate).valueOf();
        const endTime = moment(endDate).add(1, 'day').valueOf();
        if (Number.isNaN(startTime) || Number.isNaN(endTime)) return;

        const barcoGroupId = normalizeBoatGroupId(r.fk_barco);
        if (barcoGroupId && !barcosDisponiveisIds.has(barcoGroupId)) return;

        const hasAssignedBoat = Boolean(barcoGroupId);

        reservasBarcoProcessadas.add(r.id_reserva);
        items.push({
          id: r.id_reserva_quarto,
          group: hasAssignedBoat ? barcoGroupId : UNASSIGNED_BOAT_GROUP_ID,
          title: `Reserva #${r.id_reserva} - ${titular}${hasAssignedBoat ? '' : ' (sem barco)'}`,
          start_time: startTime,
          end_time: endTime,
          className: `${getOperacaoStatusClass(r.status_operacional, r.status_reserva)}${hasAssignedBoat ? '' : ' item-operacao-sem-barco'}`,
          timelineType: 'barcos',
          id_reserva: r.id_reserva,
          status_operacional: r.status_operacional || 'A Preparar',
          status_reserva: r.status_reserva || null,
          titular,
          resourceName: hasAssignedBoat ? (r.nome_barco || 'Barco definido') : 'Sem barco definido',
          tooltip: buildBarcoTooltip(r),
        });
        return;
      }

      // Ignora registros incompletos para evitar itens quebrados no timeline.
      if (!r.checkin || !r.checkout || !r.id_quarto) return;

      const startTime = moment(r.checkin).valueOf();
      const endTime = moment(r.checkout).add(1, 'day').valueOf();
      if (Number.isNaN(startTime) || Number.isNaN(endTime)) return;

      const quartoId = r.id_quarto;

      items.push({
        id: r.id_reserva_quarto,
        group: quartoId,
        title: `Reserva #${r.id_reserva} - ${titular}`,
        start_time: startTime,
        end_time: endTime,
        className: getReservaStatusClass(r.status_reserva, r.status_pagamento),
        timelineType: 'quartos',
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
  const isOperationResource = group.type === 'barco' || group.type === 'sem-barco';

  if (!isOperationResource) {
    return (
      <div className="timeline-room">
        <span className="timeline-room-number">{group.title}</span>
        {group.meta && <span className="timeline-room-type">{group.meta}</span>}
      </div>
    );
  }

  return (
    <div className={`timeline-room timeline-resource-boat ${group.type === 'sem-barco' ? 'timeline-resource-unassigned' : ''}`}>
      <div className="timeline-resource-title-row">
        <span className="timeline-room-number">{group.title}</span>
      </div>
      <div className="timeline-resource-meta-row">
        {typeof group.count === 'number' && group.count > 0 && (
          <span className="timeline-resource-count">
            {group.count} {group.count === 1 ? 'reserva' : 'reservas'}
          </span>
        )}
        {group.meta && <span className="timeline-room-type">{group.meta}</span>}
        {group.status && (
          <span className={`timeline-resource-status ${group.status === 'Disponível' ? 'success' : 'warning'}`}>
            {group.status}
          </span>
        )}
      </div>
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
    if (item.timelineType === 'barcos') {
      if (item.status_reserva === 'Cancelada') return <XCircle className="item-icon" />;
      if (item.status_operacional === 'Em Viagem') return <Navigation className="item-icon" />;
      if (item.status_operacional === 'Pronto') return <CheckCircle className="item-icon" />;
      if (item.status_operacional === 'Finalizado') return <CheckCircle className="item-icon" />;
      return <Clock className="item-icon" />;
    }

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
          <span className="timeline-item-text">
            <span className="timeline-item-title">{item.title || 'Reserva sem título'}</span>
            {item.timelineType === 'barcos' && !isCompact && item.resourceName && (
              <span className="timeline-item-subtitle">{item.resourceName}</span>
            )}
          </span>
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
  barcosData,
  reservasData,
  resourceType = 'quartos',
  sidebarTitle = 'Quartos',
  emptyMessage = 'Nenhuma reserva encontrada para os filtros atuais.',
  visibleTimeStart,
  visibleTimeEnd,
  onTimeChange,
  onItemClick,
  }) {
  const { groups, items } = useMemo(
    () => processDataForTimeline({ quartosData, barcosData, reservasData, resourceType }),
    [quartosData, barcosData, reservasData, resourceType]
  );

  return (
    <div className={`timeline-container timeline-container-${resourceType}`}>
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
        sidebarWidth={resourceType === 'barcos' ? 300 : 200}
        lineHeight={resourceType === 'barcos' ? 72 : 60}
        itemHeightRatio={resourceType === 'barcos' ? 0.68 : 0.85}
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
                {sidebarTitle}
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
          {emptyMessage}
        </div>
      )}
    </div>
  );
}

export default GanttChart;
