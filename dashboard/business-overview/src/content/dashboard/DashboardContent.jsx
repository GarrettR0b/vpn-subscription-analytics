import React from "react";
import {
  DataComponent,
  DataTable,
  EvidenceChart,
  MetricCard,
  SectionHeader,
  SortableItem,
  SortableRegion,
  useDataApp,
  useDashboardTabs,
} from "../../data-app-public.jsx";

const money = new Intl.NumberFormat("ru-RU", {
  style: "currency",
  currency: "RUB",
  maximumFractionDigits: 0,
});
const integer = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat("ru-RU", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const decimal3 = new Intl.NumberFormat("ru-RU", {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});
const percent = new Intl.NumberFormat("ru-RU", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const months = {
  "2026-01": "Янв",
  "2026-02": "Фев",
  "2026-03": "Мар",
  "2026-04": "Апр",
  "2026-05": "Май",
  "2026-06": "Июн",
};

function change(current, previous, digits = 1) {
  if (previous == null || previous === 0) return null;
  const value = ((current - previous) / previous) * 100;
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}% к прошлому месяцу`;
}

function Metric({
  id,
  title,
  value,
  comparison,
  negative,
  rows,
  trendValues,
  queryId = "monthly_business",
}) {
  return (
    <SortableItem id={id} label={title} kind="metric" span={3} minSpan={2}>
      <MetricCard
        id={id}
        queryId={queryId}
        title={title}
        value={value}
        comparison={comparison}
        negative={negative}
        trendValues={trendValues}
        sourceRows={rows}
        displayRows={[rows.at(-1)]}
      />
    </SortableItem>
  );
}

function Chart({ id, title, rows, spec, height = 250, queryId = "monthly_business", span = 6 }) {
  return (
    <SortableItem id={id} label={title} kind="chart" span={span} minSpan={4}>
      <EvidenceChart
        variant="card"
        id={id}
        queryId={queryId}
        title={title}
        spec={spec}
        rows={rows}
        sourceRows={rows}
        height={height}
      />
    </SortableItem>
  );
}

function BusinessOverview() {
  const { reviewedRows } = useDataApp();
  const sourceRows = reviewedRows("monthly_business", ["month"]);
  const tariffRows = reviewedRows("tariff_terms", ["plan"]);
  const rows = sourceRows.map((row) => ({ ...row, period: months[row.month] ?? row.month }));
  const latest = rows.at(-1);
  const previous = rows.at(-2);
  const planRows = [
    { plan: "Базовая", subscribers: latest.basicActiveSubscribers },
    { plan: "Про", subscribers: latest.proActiveSubscribers },
  ];
  const mrrMixRows = rows.flatMap((row) => [
    { period: row.period, source: "Тарифы", mrrRub: row.subscriptionMrrRub },
    { period: row.period, source: "Доп. устройства", mrrRub: row.addonMrrRub },
  ]);
  const failureDelta = (latest.connectionFailureRate - previous.connectionFailureRate) * 100;
  const tableRows = rows.map((row) => ({
    period: row.period,
    active: integer.format(row.endingPaidSubscribers),
    mrr: money.format(row.mrrRub),
    revenue: money.format(row.cashRevenueRub),
    newPaid: integer.format(row.newPaidUsers),
    churned: integer.format(row.churnedUsers),
    traffic: `${decimal.format(row.trafficGb)} ГБ`,
    failures: `${decimal.format(row.connectionFailureRate * 100)}%`,
  }));

  const sections = [
    {
      id: "overview:kpis",
      kind: "metrics",
      spacing: "none",
      items: ["active-paid", "mrr", "cash-revenue", "failure-rate"],
    },
    {
      id: "overview:growth",
      spacing: "after-metrics",
      header: <SectionHeader id="growth-heading" title="База и движение клиентов" />,
      items: ["subscriber-trend", "new-and-churn"],
    },
    {
      id: "overview:money",
      spacing: "section",
      header: <SectionHeader id="money-heading" title="Выручка" />,
      items: ["revenue-trend", "mrr-mix"],
    },
    {
      id: "overview:operations",
      spacing: "section",
      header: <SectionHeader id="operations-heading" title="Использование и качество" />,
      items: ["traffic-trend", "quality-trend"],
    },
    {
      id: "overview:plans",
      spacing: "section",
      header: <SectionHeader id="plans-heading" title="Тарифы, устройства и free trial" />,
      items: ["plan-mix", "tariff-terms"],
    },
    {
      id: "overview:detail",
      spacing: "section",
      header: <SectionHeader id="detail-heading" title="Помесячная детализация" />,
      items: ["monthly-detail"],
    },
  ];

  return (
    <article className="page">
      <SortableRegion
        id="business-overview:canvas"
        label="Business Overview"
        variant="canvas"
        columns={12}
        spacing="standard"
        authoredRevision={1}
        rows={sections}
      >
        <Metric
          id="active-paid"
          title="Активные подписчики"
          value={integer.format(latest.endingPaidSubscribers)}
          comparison={change(latest.endingPaidSubscribers, previous.endingPaidSubscribers)}
          negative={latest.endingPaidSubscribers < previous.endingPaidSubscribers}
          rows={sourceRows}
          trendValues={rows.map((row) => row.endingPaidSubscribers)}
        />
        <Metric
          id="mrr"
          title="MRR"
          value={money.format(latest.mrrRub)}
          comparison={change(latest.mrrRub, previous.mrrRub)}
          negative={latest.mrrRub < previous.mrrRub}
          rows={sourceRows}
          trendValues={rows.map((row) => row.mrrRub)}
        />
        <Metric
          id="cash-revenue"
          title="Выручка за месяц"
          value={money.format(latest.cashRevenueRub)}
          comparison={change(latest.cashRevenueRub, previous.cashRevenueRub)}
          negative={latest.cashRevenueRub < previous.cashRevenueRub}
          rows={sourceRows}
          trendValues={rows.map((row) => row.cashRevenueRub)}
        />
        <Metric
          id="failure-rate"
          title="Ошибки подключений"
          value={`${decimal.format(latest.connectionFailureRate * 100)}%`}
          comparison={`${failureDelta >= 0 ? "+" : ""}${failureDelta.toFixed(1)} п.п.`}
          negative={latest.connectionFailureRate > previous.connectionFailureRate}
          rows={sourceRows}
          trendValues={rows.map((row) => row.connectionFailureRate)}
        />

        <Chart
          id="subscriber-trend"
          title="Платящая и активная аудитория"
          rows={rows}
          spec={{
            type: "line",
            x: "period",
            y: "endingPaidSubscribers",
            fields: ["endingPaidSubscribers", "monthlyActivePaidUsers", "regularPaidUsers"],
            stackable: false,
            startAtZero: true,
            colors: {
              endingPaidSubscribers: "var(--chart-1)",
              monthlyActivePaidUsers: "var(--chart-2)",
              regularPaidUsers: "var(--chart-4)",
            },
            legend: {
              labels: {
                endingPaidSubscribers: "Подписчики на конец месяца",
                monthlyActivePaidUsers: "Пользовались VPN",
                regularPaidUsers: "Постоянное ядро",
              },
            },
          }}
        />
        <Chart
          id="new-and-churn"
          title="Новые и ушедшие клиенты"
          rows={rows}
          spec={{
            type: "bar",
            x: "period",
            y: "newPaidUsers",
            fields: ["newPaidUsers", "churnedUsers"],
            stackable: false,
            startAtZero: true,
            colors: {
              newPaidUsers: "var(--chart-2)",
              churnedUsers: "var(--chart-5)",
            },
            legend: { labels: { newPaidUsers: "Новые", churnedUsers: "Churn" } },
          }}
        />
        <Chart
          id="revenue-trend"
          title="MRR и фактическая выручка"
          rows={rows}
          spec={{
            type: "line",
            x: "period",
            y: "mrrRub",
            fields: ["mrrRub", "cashRevenueRub"],
            stackable: false,
            startAtZero: true,
            currency: "RUB",
            colors: { mrrRub: "var(--chart-1)", cashRevenueRub: "var(--chart-2)" },
            legend: { labels: { mrrRub: "MRR", cashRevenueRub: "Выручка" } },
          }}
        />
        <Chart
          id="mrr-mix"
          title="Состав MRR"
          rows={mrrMixRows}
          spec={{
            type: "bar",
            x: "period",
            y: "mrrRub",
            series: "source",
            startAtZero: true,
            currency: "RUB",
            colors: {
              "Тарифы": "var(--chart-1)",
              "Доп. устройства": "var(--chart-3)",
            },
          }}
        />
        <Chart
          id="traffic-trend"
          title="Прокси-трафик"
          rows={rows}
          spec={{
            type: "line",
            x: "period",
            y: "trafficGb",
            startAtZero: true,
            valueDecimals: 0,
            colors: { trafficGb: "var(--chart-1)" },
            legend: { labels: { trafficGb: "Трафик, ГБ" } },
          }}
        />
        <Chart
          id="quality-trend"
          title="Доля ошибок подключения"
          rows={rows}
          spec={{
            type: "line",
            x: "period",
            y: "connectionFailureRate",
            startAtZero: true,
            colors: { connectionFailureRate: "var(--chart-5)" },
            legend: { labels: { connectionFailureRate: "Ошибки" } },
          }}
        />
        <SortableItem id="plan-mix" label="Тарифный микс" kind="chart" span={6} minSpan={4}>
          <EvidenceChart
            variant="card"
            id="plan-mix"
            queryId="monthly_business"
            title="Подписчики по тарифам на конец июня"
            spec={{
              type: "horizontalBar",
              x: "plan",
              y: "subscribers",
              startAtZero: true,
              showValues: true,
              colors: { subscribers: "var(--chart-1)" },
            }}
            rows={planRows}
            sourceRows={sourceRows}
            height={210}
          />
        </SortableItem>
        <SortableItem id="tariff-terms" label="Условия тарифов" kind="table" span={6} minSpan={4}>
          <DataComponent
            variant="card"
            id="tariff-terms"
            queryId="tariff_terms"
            title={`Условия тарифов · free trial 4 дня · ${integer.format(latest.extraDeviceSlots)} допмест`}
            sourceRows={tariffRows}
            displayRows={tariffRows}
          >
            <DataTable
              rows={tariffRows}
              searchable={false}
              columns={[
                { field: "plan", label: "Тариф" },
                {
                  field: "monthlyPriceRub",
                  label: "Цена / мес.",
                  renderCell: (value) => money.format(value),
                },
                { field: "includedDevices", label: "Устройства" },
                {
                  field: "freeTrialDays",
                  label: "Free trial",
                  renderCell: (value) => (value == null ? "—" : `${value} дня`),
                },
              ]}
            />
          </DataComponent>
        </SortableItem>
        <SortableItem id="monthly-detail" label="Помесячная детализация" kind="table" span={12}>
          <DataComponent
            variant="card"
            id="monthly-detail"
            queryId="monthly_business"
            title="Ключевые показатели по месяцам"
            sourceRows={sourceRows}
            displayRows={tableRows}
          >
            <DataTable
              rows={tableRows}
              searchable={false}
              columns={[
                { field: "period", label: "Месяц" },
                { field: "active", label: "Активные" },
                { field: "mrr", label: "MRR" },
                { field: "revenue", label: "Выручка" },
                { field: "newPaid", label: "Новые" },
                { field: "churned", label: "Churn" },
                { field: "traffic", label: "Трафик" },
                { field: "failures", label: "Ошибки" },
              ]}
            />
          </DataComponent>
        </SortableItem>
      </SortableRegion>
    </article>
  );
}

function SubscriberActivation() {
  const { reviewedRows } = useDataApp();
  const summaryRows = reviewedRows("activation_summary", ["eligibleSubscriptions"]);
  const funnelRows = reviewedRows("activation_funnel", ["stageOrder"]);
  const monthlySourceRows = reviewedRows("activation_monthly", ["month"]);
  const segmentRows = reviewedRows("activation_segments", ["dimension", "segment"]);
  const summary = summaryRows[0];
  const monthlyRows = monthlySourceRows.map((row) => ({
    ...row,
    period: months[row.month] ?? row.month,
  }));
  const channelRows = segmentRows.filter((row) => row.dimension === "Канал продажи");
  const planRows = segmentRows.filter((row) => row.dimension === "Тариф");
  const detailRows = segmentRows.map((row) => ({
    dimension: row.dimension,
    segment: row.segment,
    eligible: integer.format(row.eligibleSubscriptions),
    activation: percent.format(row.activationRate),
    linkFetch: percent.format(row.linkFetchRate),
    failures: percent.format(row.connectionFailureRate),
  }));

  const sections = [
    {
      id: "activation:kpis",
      kind: "metrics",
      spacing: "none",
      items: [
        "eligible-subscriptions",
        "activation-rate",
        "link-fetch-rate",
        "time-to-value",
      ],
    },
    {
      id: "activation:path",
      spacing: "after-metrics",
      header: <SectionHeader id="activation-path-heading" title="Путь нового подписчика" />,
      items: ["activation-funnel", "activation-trend"],
    },
    {
      id: "activation:segments",
      spacing: "section",
      header: <SectionHeader id="activation-segments-heading" title="Сегменты" />,
      items: ["activation-by-channel", "activation-by-plan"],
    },
    {
      id: "activation:detail",
      spacing: "section",
      header: <SectionHeader id="activation-detail-heading" title="Детализация" />,
      items: ["activation-detail"],
    },
  ];

  return (
    <article className="page">
      <SortableRegion
        id="subscriber-activation:canvas"
        label="New Subscriber Activation"
        variant="canvas"
        columns={12}
        spacing="standard"
        authoredRevision={1}
        rows={sections}
      >
        <Metric
          id="eligible-subscriptions"
          title="Новые подписки"
          value={integer.format(summary.eligibleSubscriptions)}
          comparison={`${integer.format(summary.activatedSubscriptions)} дошли до активации`}
          negative={false}
          rows={summaryRows}
          trendValues={monthlyRows.map((row) => row.eligibleSubscriptions)}
          queryId="activation_summary"
        />
        <Metric
          id="activation-rate"
          title="7-day activation"
          value={percent.format(summary.activationRate)}
          comparison={`${integer.format(summary.activatedSubscriptions)} из ${integer.format(summary.eligibleSubscriptions)}`}
          negative={false}
          rows={summaryRows}
          trendValues={monthlyRows.map((row) => row.activationRate)}
          queryId="activation_summary"
        />
        <Metric
          id="link-fetch-rate"
          title="Ссылка добавлена в HAPP"
          value={percent.format(summary.linkFetchRate)}
          comparison={`${integer.format(summary.linkFetchedSubscriptions)} из ${integer.format(summary.eligibleSubscriptions)}`}
          negative={false}
          rows={summaryRows}
          trendValues={monthlyRows.map((row) => row.linkFetchRate)}
          queryId="activation_summary"
        />
        <Metric
          id="time-to-value"
          title="Медиана до подключения"
          value={`${decimal.format(summary.medianTimeToValueHours)} ч`}
          comparison="до первой успешной сессии"
          negative={false}
          rows={summaryRows}
          trendValues={monthlyRows.map((row) => row.medianTimeToValueHours)}
          queryId="activation_summary"
        />

        <Chart
          id="activation-funnel"
          title="Воронка первых 7 дней"
          rows={funnelRows}
          queryId="activation_funnel"
          spec={{
            type: "horizontalBar",
            x: "stage",
            y: "subscriptions",
            startAtZero: true,
            showValues: true,
            colors: { subscriptions: "var(--chart-1)" },
          }}
        />
        <Chart
          id="activation-trend"
          title="Активация по месяцу покупки"
          rows={monthlyRows}
          queryId="activation_monthly"
          spec={{
            type: "line",
            x: "period",
            y: "activationRate",
            fields: ["activationRate", "linkFetchRate"],
            stackable: false,
            startAtZero: true,
            colors: {
              activationRate: "var(--chart-1)",
              linkFetchRate: "var(--chart-2)",
            },
            legend: {
              labels: {
                activationRate: "7-day activation",
                linkFetchRate: "Ссылка в HAPP",
              },
            },
          }}
        />
        <Chart
          id="activation-by-channel"
          title="7-day activation по каналу продажи"
          rows={channelRows}
          queryId="activation_segments"
          spec={{
            type: "horizontalBar",
            x: "segment",
            y: "activationRate",
            startAtZero: true,
            showValues: true,
            colors: { activationRate: "var(--chart-1)" },
          }}
          height={210}
        />
        <Chart
          id="activation-by-plan"
          title="7-day activation по тарифу"
          rows={planRows}
          queryId="activation_segments"
          spec={{
            type: "horizontalBar",
            x: "segment",
            y: "activationRate",
            startAtZero: true,
            showValues: true,
            colors: { activationRate: "var(--chart-2)" },
          }}
          height={210}
        />
        <SortableItem id="activation-detail" label="Детализация активации" kind="table" span={12}>
          <DataComponent
            variant="card"
            id="activation-detail"
            queryId="activation_segments"
            title="Качество активации по сегментам"
            sourceRows={segmentRows}
            displayRows={detailRows}
          >
            <DataTable
              rows={detailRows}
              searchable={false}
              columns={[
                { field: "dimension", label: "Разрез" },
                { field: "segment", label: "Сегмент" },
                { field: "eligible", label: "Новые подписки" },
                { field: "activation", label: "7-day activation" },
                { field: "linkFetch", label: "Ссылка в HAPP" },
                { field: "failures", label: "Ошибки" },
              ]}
            />
          </DataComponent>
        </SortableItem>
      </SortableRegion>
    </article>
  );
}

function RetentionCohorts() {
  const { reviewedRows } = useDataApp();
  const summaryRows = reviewedRows("retention_summary", ["monthNumber"]);
  const cohortSourceRows = reviewedRows("retention_cohorts", ["cohort", "monthNumber"]);
  const segmentRows = reviewedRows("retention_segments", ["dimension", "segment"]);
  const m1 = summaryRows.find((row) => row.monthNumber === 1);
  const m2 = summaryRows.find((row) => row.monthNumber === 2);
  const m3 = summaryRows.find((row) => row.monthNumber === 3);
  const cohortRows = cohortSourceRows.map((row) => ({
    ...row,
    cohortLabel: months[row.cohort] ?? row.cohort,
  }));
  const channelRows = segmentRows.filter((row) => row.dimension === "Канал продажи");
  const planRows = segmentRows.filter((row) => row.dimension === "Тариф");
  const activationRows = segmentRows.filter((row) => row.dimension === "7-day activation");
  const activated = activationRows.find((row) => row.segment === "Активировались");
  const notActivated = activationRows.find((row) => row.segment === "Не активировались");
  const activationGap = activated.retentionRate - notActivated.retentionRate;
  const detailRows = cohortRows.map((row) => ({
    cohort: row.cohortLabel,
    period: row.period,
    cohortSize: integer.format(row.cohortSize),
    retained: integer.format(row.retainedSubscriptions),
    retention: percent.format(row.retentionRate),
  }));

  const sections = [
    {
      id: "retention:kpis",
      kind: "metrics",
      spacing: "none",
      items: ["m1-retention", "m2-retention", "m3-retention", "activation-retention-gap"],
    },
    {
      id: "retention:cohorts",
      spacing: "after-metrics",
      header: <SectionHeader id="retention-cohorts-heading" title="Когортная динамика" />,
      items: ["retention-curve"],
    },
    {
      id: "retention:segments",
      spacing: "section",
      header: <SectionHeader id="retention-segments-heading" title="M1 retention по сегментам" />,
      items: ["retention-by-channel", "retention-by-plan", "retention-by-activation"],
    },
    {
      id: "retention:detail",
      spacing: "section",
      header: <SectionHeader id="retention-detail-heading" title="Зрелость когорт" />,
      items: ["retention-detail"],
    },
  ];

  return (
    <article className="page">
      <SortableRegion
        id="subscriber-retention:canvas"
        label="Retention and cohorts"
        variant="canvas"
        columns={12}
        spacing="standard"
        authoredRevision={1}
        rows={sections}
      >
        <Metric
          id="m1-retention"
          title="M1 usage retention"
          value={percent.format(m1.retentionRate)}
          comparison={`${integer.format(m1.retainedSubscriptions)} из ${integer.format(m1.eligibleSubscriptions)}`}
          negative={false}
          rows={[m1]}
          trendValues={summaryRows.map((row) => row.retentionRate)}
          queryId="retention_summary"
        />
        <Metric
          id="m2-retention"
          title="M2 usage retention"
          value={percent.format(m2.retentionRate)}
          comparison={`${integer.format(m2.retainedSubscriptions)} из ${integer.format(m2.eligibleSubscriptions)}`}
          negative={false}
          rows={[m2]}
          trendValues={summaryRows.map((row) => row.retentionRate)}
          queryId="retention_summary"
        />
        <Metric
          id="m3-retention"
          title="M3 usage retention"
          value={percent.format(m3.retentionRate)}
          comparison={`${integer.format(m3.retainedSubscriptions)} из ${integer.format(m3.eligibleSubscriptions)}`}
          negative={false}
          rows={[m3]}
          trendValues={summaryRows.map((row) => row.retentionRate)}
          queryId="retention_summary"
        />
        <Metric
          id="activation-retention-gap"
          title="Разница M1 после активации"
          value={`${activationGap >= 0 ? "+" : ""}${decimal.format(activationGap * 100)} п.п.`}
          comparison={`${percent.format(activated.retentionRate)} vs ${percent.format(notActivated.retentionRate)}`}
          negative={activationGap < 0}
          rows={activationRows}
          trendValues={activationRows.map((row) => row.retentionRate)}
          queryId="retention_segments"
        />

        <SortableItem id="retention-curve" label="Когортная retention" kind="chart" span={12}>
          <EvidenceChart
            variant="card"
            id="retention-curve"
            queryId="retention_cohorts"
            title="Usage retention по возрасту когорты · M0 = месяц покупки"
            spec={{
              type: "line",
              x: "period",
              y: "retentionRate",
              series: "cohortLabel",
              stackable: false,
              startAtZero: true,
            }}
            rows={cohortRows}
            sourceRows={cohortSourceRows}
            height={300}
          />
        </SortableItem>
        <Chart
          id="retention-by-channel"
          title="M1 usage retention по каналу продажи"
          rows={channelRows}
          queryId="retention_segments"
          spec={{
            type: "horizontalBar",
            x: "segment",
            y: "retentionRate",
            startAtZero: true,
            showValues: true,
            colors: { retentionRate: "var(--chart-1)" },
          }}
          height={210}
          span={4}
        />
        <Chart
          id="retention-by-plan"
          title="M1 usage retention по тарифу"
          rows={planRows}
          queryId="retention_segments"
          spec={{
            type: "horizontalBar",
            x: "segment",
            y: "retentionRate",
            startAtZero: true,
            showValues: true,
            colors: { retentionRate: "var(--chart-2)" },
          }}
          height={210}
          span={4}
        />
        <Chart
          id="retention-by-activation"
          title="M1 usage retention и 7-day activation"
          rows={activationRows}
          queryId="retention_segments"
          spec={{
            type: "horizontalBar",
            x: "segment",
            y: "retentionRate",
            startAtZero: true,
            showValues: true,
            colors: { retentionRate: "var(--chart-3)" },
          }}
          height={210}
          span={4}
        />
        <SortableItem id="retention-detail" label="Детализация retention" kind="table" span={12}>
          <DataComponent
            variant="card"
            id="retention-detail"
            queryId="retention_cohorts"
            title="Retention по зрелым когортным периодам"
            sourceRows={cohortSourceRows}
            displayRows={detailRows}
          >
            <DataTable
              rows={detailRows}
              searchable={false}
              columns={[
                { field: "cohort", label: "Когорта" },
                { field: "period", label: "Возраст" },
                { field: "cohortSize", label: "Размер когорты" },
                { field: "retained", label: "Вернулись" },
                { field: "retention", label: "Usage retention" },
              ]}
            />
          </DataComponent>
        </SortableItem>
      </SortableRegion>
    </article>
  );
}

function ActivationExperiment() {
  const { reviewedRows } = useDataApp();
  const summaryRows = reviewedRows("experiment_summary", ["observedSampleSize"]);
  const variantRows = reviewedRows("experiment_variants", ["variant"]);
  const monthlySourceRows = reviewedRows("experiment_monthly", ["month", "variant"]);
  const summary = summaryRows[0];
  const control = variantRows.find((row) => row.variant === "control");
  const treatment = variantRows.find((row) => row.variant === "treatment");
  const monthlyRows = monthlySourceRows.map((row) => ({
    ...row,
    period: months[row.month] ?? row.month,
  }));
  const detailRows = variantRows.map((row) => ({
    variant: row.variantLabel,
    subscriptions: integer.format(row.subscriptions),
    linkFetch: percent.format(row.linkFetchRate),
    activation: percent.format(row.activationRate),
    timeToValue: `${decimal.format(row.medianTimeToValueHours)} ч`,
    failures: percent.format(row.connectionFailureRate),
  }));
  const confidenceInterval = `${summary.ciLow >= 0 ? "+" : ""}${decimal.format(summary.ciLow * 100)}…${summary.ciHigh >= 0 ? "+" : ""}${decimal.format(summary.ciHigh * 100)} п.п.`;
  const decision =
    summary.statisticallySignificant && summary.ciLow > 0
      ? "эффект подтверждён"
      : "данных пока недостаточно";

  const sections = [
    {
      id: "experiment:kpis",
      kind: "metrics",
      spacing: "none",
      items: [
        "experiment-sample",
        "experiment-control",
        "experiment-treatment",
        "experiment-effect",
      ],
    },
    {
      id: "experiment:result",
      spacing: "after-metrics",
      header: <SectionHeader id="experiment-result-heading" title="Primary metric" />,
      items: ["experiment-activation", "experiment-monthly"],
    },
    {
      id: "experiment:quality",
      spacing: "section",
      header: <SectionHeader id="experiment-quality-heading" title="Secondary и guardrail" />,
      items: ["experiment-detail"],
    },
  ];

  return (
    <article className="page">
      <SortableRegion
        id="activation-experiment:canvas"
        label="Activation experiment"
        variant="canvas"
        columns={12}
        spacing="standard"
        authoredRevision={1}
        rows={sections}
      >
        <Metric
          id="experiment-sample"
          title="Участники"
          value={integer.format(summary.observedSampleSize)}
          comparison={`Нужно ≈${integer.format(summary.requiredSampleSize)} для MDE ${decimal.format(summary.mde * 100)} п.п.`}
          negative={summary.observedSampleSize < summary.requiredSampleSize}
          rows={summaryRows}
          trendValues={variantRows.map((row) => row.subscriptions)}
          queryId="experiment_summary"
        />
        <Metric
          id="experiment-control"
          title="Control activation"
          value={percent.format(control.activationRate)}
          comparison={`${integer.format(control.activatedSubscriptions)} из ${integer.format(control.subscriptions)}`}
          negative={false}
          rows={[control]}
          trendValues={[control.activationRate]}
          queryId="experiment_variants"
        />
        <Metric
          id="experiment-treatment"
          title="Treatment activation"
          value={percent.format(treatment.activationRate)}
          comparison={`${integer.format(treatment.activatedSubscriptions)} из ${integer.format(treatment.subscriptions)}`}
          negative={false}
          rows={[treatment]}
          trendValues={[treatment.activationRate]}
          queryId="experiment_variants"
        />
        <Metric
          id="experiment-effect"
          title="Эффект treatment"
          value={`${summary.absoluteEffect >= 0 ? "+" : ""}${decimal.format(summary.absoluteEffect * 100)} п.п.`}
          comparison={`95% ДИ ${confidenceInterval}; p=${decimal3.format(summary.pValue)} — ${decision}`}
          negative={summary.absoluteEffect < 0}
          rows={summaryRows}
          trendValues={variantRows.map((row) => row.activationRate)}
          queryId="experiment_summary"
        />

        <Chart
          id="experiment-activation"
          title="7-day activation по варианту"
          rows={variantRows}
          queryId="experiment_variants"
          spec={{
            type: "horizontalBar",
            x: "variantLabel",
            y: "activationRate",
            startAtZero: true,
            showValues: true,
            colors: { activationRate: "var(--chart-1)" },
          }}
          height={240}
        />
        <Chart
          id="experiment-monthly"
          title="Активация по месяцу и варианту"
          rows={monthlyRows}
          queryId="experiment_monthly"
          spec={{
            type: "line",
            x: "period",
            y: "activationRate",
            series: "variantLabel",
            stackable: false,
            startAtZero: true,
            colors: { Control: "var(--chart-2)", Treatment: "var(--chart-1)" },
          }}
          height={240}
        />
        <SortableItem id="experiment-detail" label="Метрики эксперимента" kind="table" span={12}>
          <DataComponent
            variant="card"
            id="experiment-detail"
            queryId="experiment_variants"
            title="Secondary metrics и качество подключения"
            sourceRows={variantRows}
            displayRows={detailRows}
          >
            <DataTable
              rows={detailRows}
              searchable={false}
              columns={[
                { field: "variant", label: "Вариант" },
                { field: "subscriptions", label: "Подписки" },
                { field: "linkFetch", label: "Ссылка в HAPP" },
                { field: "activation", label: "7-day activation" },
                { field: "timeToValue", label: "Медиана до подключения" },
                { field: "failures", label: "Ошибки подключения" },
              ]}
            />
          </DataComponent>
        </SortableItem>
      </SortableRegion>
    </article>
  );
}

export function DashboardContent() {
  const { activeTabId } = useDashboardTabs([
    { id: "dashboard", label: "Business Overview" },
    {
      id: "activation",
      label: "Activation",
      previousLabels: ["New Subscriber Activation"],
    },
    { id: "retention", label: "Retention" },
    { id: "experiment", label: "Experiment" },
  ]);

  if (activeTabId === "activation") return <SubscriberActivation />;
  if (activeTabId === "retention") return <RetentionCohorts />;
  if (activeTabId === "experiment") return <ActivationExperiment />;
  return <BusinessOverview />;
}
