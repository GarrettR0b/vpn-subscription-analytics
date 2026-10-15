import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Run with the target report closed: Desktop can overwrite PBIR with its older in-memory layout.
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const definition = path.join(repo, 'powerbi', 'vpn-analytics.Report', 'definition');
const pagesRoot = path.join(definition, 'pages');
const managedPath = path.join(repo, 'scripts', 'powerbi-generated-visuals.json');
const resourcesRoot = path.join(path.dirname(definition), 'StaticResources', 'RegisteredResources');
const visualSchema = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json';
const pageSchema = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json';
const pagesSchema = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json';
const colors = {
  green: '#34C759', blue: '#4C9AFF', teal: '#2DD4BF', red: '#FF6B6B',
  purple: '#A78BFA', amber: '#F59E0B', bg: '#111827', panel: '#1F2937',
  border: '#374151', text: '#F9FAFB', muted: '#9CA3AF', grid: '#374151'
};

const id = (seed) => createHash('sha1').update(seed).digest('hex').slice(0, 20);
const lit = (value) => ({ expr: { Literal: { Value: typeof value === 'string' && !/^-?\d+(?:\.\d+)?[DL]$/.test(value) ? `'${value}'` : `${value}` } } });
const fill = (color) => ({ solid: { color: lit(color) } });
const displayColumns = { Plan: 'Тариф', 'Sales Channel': 'Канал покупки', 'Onboarding Variant': 'Вариант настройки', 'Activated 7D': 'Ранняя активация' };
const labels = {
  'Month': 'Месяц', 'Month Start': 'Месяц', 'Cohort Month': 'Месяц первой оплаты', 'Month Number': 'Месяцев после оплаты',
  'Ending Subscribers': 'Платящие подписчики', 'MRR': 'Месячная выручка по подпискам', 'Revenue': 'Полученная выручка',
  'New Paying Users': 'Новые платящие', 'Churned Subscribers': 'Ушедшие подписчики', 'Traffic': 'Трафик',
  'Latest Connection Failure Rate': 'Ошибки подключения', '# Paid Subscriptions': 'Оплаченные подписки',
  '# Activated Subscriptions': 'Активированные подписки', 'Activation Rate': 'Доля активированных',
  'Link Fetch Rate': 'Доля получивших ссылку', 'Weighted Failure Rate': 'Доля ошибок подключения',
  'Average Time to First Value': 'Часов до первого подключения', 'Cohort Size': 'Подписки в выбранных группах',
  'Retained Subscribers': 'Вернувшиеся подписчики', 'Observed Subscriptions': 'Наблюдаемые подписки',
  'Retention Rate': 'Доля вернувшихся', 'M1 Retention': 'Возврат через 1 месяц', 'M3 Retention': 'Возврат через 3 месяца',
  'M1 Observed Subscriptions': 'Подписки с наблюдением через 1 месяц', 'M3 Observed Subscriptions': 'Подписки с наблюдением через 3 месяца',
  'M1 Retained Subscribers': 'Вернувшиеся через 1 месяц', '# Experiment Subscriptions': 'Участники проверки',
  'Experiment Activation Rate': 'Доля активированных', 'Experiment Link Fetch Rate': 'Доля получивших ссылку',
  'Control Sample': 'Участники обычной настройки', 'Treatment Sample': 'Участники настройки с подсказками',
  'Control Activation Rate': 'Активация · обычная настройка', 'Treatment Activation Rate': 'Активация · с подсказками',
  'Absolute Lift': 'Разница активации, п.п.', 'Relative Lift': 'Относительное изменение',
  'Lift CI Lower': 'Нижняя граница оценки (95%)', 'Lift CI Upper': 'Верхняя граница оценки (95%)',
  'Activation P Value': 'Проверка различий (p)'
};
const column = (table, property) => ({ Column: { Expression: { SourceRef: { Entity: table } }, Property: displayColumns[property] ?? property } });
const measure = (table, property) => ({ Measure: { Expression: { SourceRef: { Entity: table } }, Property: property } });
const projection = (kind, table, property, active = false) => ({
  field: kind === 'measure' ? { Measure: measure(table, property).Measure } : { Column: column(table, property).Column },
  queryRef: `${table}.${kind === 'column' ? displayColumns[property] ?? property : property}`,
  nativeQueryRef: kind === 'column' ? displayColumns[property] ?? property : property,
  displayName: labels[property] ?? displayColumns[property] ?? property,
  ...(active ? { active: true } : {})
});
const position = (x, y, width, height, z) => ({ x, y, z, height, width, tabOrder: z });
const panelVco = (title) => ({
  title: [{ properties: { show: lit(true), text: lit(title), fontSize: lit('13D'), fontColor: fill(colors.text), bold: lit(true) } }],
  subTitle: [{ properties: { show: lit(false) } }],
  background: [{ properties: { show: lit(true), color: fill(colors.panel), transparency: lit('0D') } }],
  border: [{ properties: { show: lit(true), color: fill(colors.border), radius: lit('8D'), width: lit('1D') } }],
  padding: [{ properties: { top: lit('8D'), bottom: lit('8D'), left: lit('8D'), right: lit('8D') } }],
  visualHeader: [{ properties: { show: lit(false) } }]
});
const visual = (seed, pos, body) => ({ $schema: visualSchema, name: id(seed), position: pos, visual: body });

function textbox(seed, text, x, y, width, height, fontSize = 26, color = colors.text, weight = 'bold') {
  const safeHeight = Math.max(height, fontSize >= 20 ? 60 : 40);
  return visual(seed, position(x, y, width, safeHeight, 10), {
    visualType: 'textbox',
    objects: { general: [{ properties: { paragraphs: [{ textRuns: [{ value: text, textStyle: { fontFamily: 'Segoe UI', fontSize: `${fontSize}px`, fontWeight: weight, color } }], horizontalTextAlignment: 'left' }] } }] },
    visualContainerObjects: {
      background: [{ properties: { show: lit(false) } }],
      border: [{ properties: { show: lit(false) } }],
      padding: [{ properties: { top: lit('0D'), bottom: lit('0D'), left: lit('0D'), right: lit('0D') } }]
    }
  });
}

function card(seed, table, metric, label, color, x, y, width = 280, tooltip) {
  return visual(seed, position(x, y, width, 97, 100), {
    visualType: 'cardVisual',
    query: { queryState: {
      Data: { projections: [projection('measure', table, metric)] },
      ...(tooltip ? { Tooltips: { projections: [projection('measure', table, tooltip)] } } : {})
    } },
    objects: {
      value: [{ properties: { fontSize: lit(width < 280 ? '24D' : '28D'), fontColor: fill(color), bold: lit(true), labelDisplayUnits: lit('0'), showBlankAs: lit('-') }, selector: { id: 'default' } }],
      label: [{ properties: { show: lit(true), text: lit(label), fontSize: lit('12D'), fontColor: fill(colors.muted) }, selector: { id: 'default' } }],
      outline: [{ properties: { show: lit(false) }, selector: { id: 'default' } }],
      accentBar: [{ properties: { show: lit(true), position: lit('Left'), width: lit('4D'), color: fill(color) }, selector: { id: 'default' } }],
      padding: [{ properties: { paddingUniform: lit('8D') }, selector: { id: 'default' } }],
      layout: [{ properties: { paddingUniform: lit('0D') }, selector: { id: 'default' } }]
    },
    visualContainerObjects: {
      ...panelVco(''),
      title: [{ properties: { show: lit(false) } }],
      padding: [{ properties: { top: lit('0D'), bottom: lit('0D'), left: lit('0D'), right: lit('0D') } }],
      spacing: [{ properties: { customizeSpacing: lit(true), verticalSpacing: lit('2D') }, selector: { id: 'default' } }],
      ...(tooltip ? { visualTooltip: [{ properties: { show: lit(true) } }] } : {})
    }
  });
}

function slicer(seed, table, field, label, x, y, width = 210) {
  return visual(seed, position(x, y, width, 80, 90), {
    visualType: 'slicer',
    query: { queryState: { Values: { projections: [projection('column', table, field)] } } },
    objects: {
      data: [{ properties: { mode: lit('Dropdown') } }],
      header: [{ properties: { show: lit(true), text: lit(label), fontColor: fill(colors.text), background: fill(colors.panel) } }],
      items: [{ properties: { fontColor: fill(colors.text), background: fill(colors.panel) } }]
    },
    visualContainerObjects: {
      ...panelVco(''),
      title: [{ properties: { show: lit(false) } }]
    }
  });
}

function chart(seed, type, title, category, metrics, x, y, width, height, palette, tooltips = []) {
  const categoryProjection = projection('column', category.table, category.field, true);
  const metricProjections = metrics.map((m) => projection('measure', m.table, m.field));
  const dataPoint = metrics.length === 1
    ? [{ properties: { defaultColor: fill(palette[0]) } }]
    : metrics.map((m, index) => ({ properties: { fill: fill(palette[index]) }, selector: { metadata: `${m.table}.${m.field}` } }));
  return visual(seed, position(x, y, width, height, 200), {
    visualType: type,
    query: {
      queryState: {
        Category: { projections: [categoryProjection] }, Y: { projections: metricProjections },
        ...(tooltips.length ? { Tooltips: { projections: tooltips.map((m) => projection('measure', m.table, m.field)) } } : {})
      },
      sortDefinition: { sort: [{ field: { Column: column(category.table, category.field).Column }, direction: 'Ascending' }], isDefaultSort: true }
    },
    objects: {
      dataPoint,
      categoryAxis: [{ properties: { show: lit(true), labelColor: fill(colors.muted), titleColor: fill(colors.muted), fontSize: lit('10D') } }],
      valueAxis: [{ properties: { show: lit(true), labelColor: fill(colors.muted), titleColor: fill(colors.muted), gridlineColor: fill(colors.grid), gridlineStyle: lit('dotted') } }],
      legend: [{ properties: { show: lit(metrics.length > 1), position: lit('Top') } }]
    },
    visualContainerObjects: { ...panelVco(title), ...(tooltips.length ? { visualTooltip: [{ properties: { show: lit(true) } }] } : {}) }
  });
}

function matrix(seed, title, table, rows, columns, metrics, x, y, width, height) {
  const queryState = {
    Rows: { projections: rows.map((f) => projection('column', table, f)) },
    Values: { projections: metrics.map((m) => projection('measure', m.table, m.field)) }
  };
  if (columns.length) queryState.Columns = { projections: columns.map((f) => projection('column', table, f)) };
  return visual(seed, position(x, y, width, height, 220), {
    visualType: 'pivotTable',
    query: { queryState },
    objects: {
      columnHeaders: [{ properties: { autoSizeColumnWidth: lit(true), columnAdjustment: lit('growToFit'), fontColor: fill(colors.text), backColor: fill('#243244') } }],
      rowHeaders: [{ properties: { fontColor: fill(colors.text), backColor: fill(colors.panel) } }],
      values: [{ properties: { backColorPrimary: fill(colors.panel), backColorSecondary: fill('#243244'), fontColorPrimary: fill(colors.text), fontColorSecondary: fill(colors.text) } }]
    },
    visualContainerObjects: { ...panelVco(title), stylePreset: [{ properties: { name: lit('None') } }] }
  });
}

function navigator(seed, currentPage) {
  return [
    ['business-overview', 'Обзор бизнеса'], ['activation', 'Активация подписки'],
    ['retention', 'Удержание подписчиков'], ['activation-experiment', 'Проверка новой настройки']
  ].map(([key, label], index) => visual(index ? `${seed}-${index}` : seed, position(20 + index * 474, 1004, 458, 48, 500 + index), {
    visualType: 'actionButton',
    objects: {
      text: [
        { properties: { show: lit(true) } },
        { properties: { text: lit(label), fontSize: lit('12D'), bold: lit(key === currentPage), fontColor: fill(colors.text), horizontalAlignment: lit('center') }, selector: { id: 'default' } }
      ],
      fill: [
        { properties: { show: lit(true) } },
        { properties: { fillColor: fill(key === currentPage ? colors.blue : '#243244') }, selector: { id: 'default' } },
        { properties: { fillColor: fill('#3B82F6') }, selector: { id: 'hover' } }
      ],
      icon: [{ properties: { show: lit(false) } }, { properties: { shapeType: lit('blank'), placement: lit('left') }, selector: { id: 'default' } }],
      outline: [{ properties: { show: lit(false) } }],
      shape: [{ properties: { tileShape: lit('rectangleRounded'), roundEdge: lit('8L') } }, { properties: { tileShape: lit('rectangleRounded') }, selector: { id: 'default' } }]
    },
    visualContainerObjects: {
      background: [{ properties: { show: lit(false) } }], border: [{ properties: { show: lit(false) } }],
      padding: [{ properties: { top: lit('0D'), bottom: lit('0D'), left: lit('0D'), right: lit('0D') } }],
      visualHeader: [{ properties: { show: lit(false) } }],
      visualLink: [{ properties: { show: lit(true), type: lit('PageNavigation'), navigationSection: lit(id(`page-${key}`)), tooltip: lit(label) } }]
    },
    drillFilterOtherVisuals: true
  }));
}

const pageDefinitions = [
  {
    key: 'business-overview', displayName: 'Обзор бизнеса', visuals: [
      textbox('bo-title', 'Обзор бизнеса', 20, 18, 900, 52),
      textbox('bo-subtitle', 'Синтетические данные: январь–июнь 2026. Выручка - выбранный период; остальные карточки - последний выбранный месяц (по умолчанию - июнь).\nПробный период 4 дня • Basic 130 ₽ / 6 устройств • Pro 220 ₽ / 8 • дополнительные места отдельно', 20, 68, 1560, 40, 14, colors.muted, 'normal'),
      slicer('bo-month', 'Date', 'Month', 'Месяц', 1660, 20, 240),
      card('bo-revenue', 'Monthly Business', 'Revenue', 'Выручка · за период', colors.green, 20, 120, 252),
      card('bo-mrr', 'Monthly Business', 'MRR', 'Подписки · последний месяц', colors.green, 288, 120, 252),
      card('bo-subs', 'Monthly Business', 'Ending Subscribers', 'Подписчики · конец месяца', colors.blue, 556, 120, 252),
      card('bo-new', 'Monthly Business', 'New Paying Users', 'Новые · последний месяц', colors.teal, 824, 120, 252),
      card('bo-churn', 'Monthly Business', 'Churned Subscribers', 'Отток · последний месяц', colors.red, 1092, 120, 252),
      card('bo-traffic', 'Monthly Business', 'Traffic', 'Трафик · последний месяц', colors.purple, 1360, 120, 252),
      card('bo-fail', 'Monthly Business', 'Latest Connection Failure Rate', 'Ошибки · последний месяц', colors.amber, 1628, 120, 272),
      chart('bo-mrr-line', 'lineChart', 'Месячная выручка по подпискам', { table: 'Date', field: 'Month Start' }, [{ table: 'Monthly Business', field: 'MRR' }], 20, 240, 920, 340, [colors.green]),
      chart('bo-subs-line', 'lineChart', 'Динамика подписчиков', { table: 'Date', field: 'Month Start' }, [{ table: 'Monthly Business', field: 'Ending Subscribers' }], 960, 240, 940, 340, [colors.blue]),
      chart('bo-new-churn', 'clusteredColumnChart', 'Новые и ушедшие платящие подписчики', { table: 'Date', field: 'Month Start' }, [{ table: 'Monthly Business', field: 'New Paying Users' }, { table: 'Monthly Business', field: 'Churned Subscribers' }], 20, 600, 920, 280, [colors.teal, colors.red]),
      chart('bo-traffic-line', 'lineChart', 'Трафик', { table: 'Date', field: 'Month Start' }, [{ table: 'Monthly Business', field: 'Traffic' }], 960, 600, 455, 280, [colors.purple]),
      chart('bo-fail-line', 'lineChart', 'Ошибки подключения', { table: 'Date', field: 'Month Start' }, [{ table: 'Monthly Business', field: 'Latest Connection Failure Rate' }], 1435, 600, 465, 280, [colors.amber]),
      textbox('bo-note', 'Вывод по всем данным, январь–июнь: платящая база и месячная выручка выросли, но доля ошибок тоже увеличилась. Рекомендация: проверить причины ошибок; их связь с оттоком пока не доказана. Этот вывод не пересчитывается фильтром.', 20, 904, 1880, 76, 16, colors.muted, 'normal'),
      ...navigator('bo-nav', 'business-overview')
    ]
  },
  {
    key: 'activation', displayName: 'Активация подписки', visuals: [
      textbox('act-title', 'Активация подписки', 20, 18, 760, 52),
      textbox('act-subtitle', 'Первые 7 дней после оплаты; время до первого подключения - только среди подключившихся', 20, 68, 1040, 40, 14, colors.muted, 'normal'),
      slicer('act-onboarding', 'Subscriber Activation', 'Onboarding Variant', 'Вариант настройки', 1160, 20, 240),
      slicer('act-plan', 'Subscriber Activation', 'Plan', 'Тариф', 1420, 20, 220),
      slicer('act-channel', 'Subscriber Activation', 'Sales Channel', 'Канал продаж', 1660, 20, 240),
      card('act-paid', 'Subscriber Activation', '# Paid Subscriptions', 'Оплаченные подписки', colors.blue, 20, 120, 340),
      card('act-activated', 'Subscriber Activation', '# Activated Subscriptions', 'Активированы за 7 дней', colors.green, 380, 120, 340),
      card('act-rate', 'Subscriber Activation', 'Activation Rate', 'Доля активированных', colors.teal, 740, 120, 340),
      card('act-link', 'Subscriber Activation', 'Link Fetch Rate', 'Получили ссылку', colors.purple, 1100, 120, 340),
      card('act-time', 'Subscriber Activation', 'Average Time to First Value', 'Время до первого подключения', colors.amber, 1460, 120, 440),
      chart('act-rate-plan', 'clusteredColumnChart', 'Доля активированных по тарифам', { table: 'Subscriber Activation', field: 'Plan' }, [{ table: 'Subscriber Activation', field: 'Activation Rate' }], 20, 240, 610, 330, [colors.teal]),
      chart('act-link-plan', 'clusteredColumnChart', 'Получение ссылки по тарифам', { table: 'Subscriber Activation', field: 'Plan' }, [{ table: 'Subscriber Activation', field: 'Link Fetch Rate' }], 650, 240, 610, 330, [colors.purple]),
      chart('act-failure-channel', 'clusteredColumnChart', 'Ошибки по каналам продаж', { table: 'Subscriber Activation', field: 'Sales Channel' }, [{ table: 'Subscriber Activation', field: 'Weighted Failure Rate' }], 1280, 240, 620, 330, [colors.amber]),
      matrix('act-matrix', 'Детализация воронки активации', 'Subscriber Activation', ['Plan'], [], [
        { table: 'Subscriber Activation', field: '# Paid Subscriptions' },
        { table: 'Subscriber Activation', field: '# Activated Subscriptions' },
        { table: 'Subscriber Activation', field: 'Activation Rate' },
        { table: 'Subscriber Activation', field: 'Link Fetch Rate' },
        { table: 'Subscriber Activation', field: 'Average Time to First Value' }
      ], 20, 590, 1880, 290),
      textbox('act-note', 'Вывод по всем данным, январь–июнь: получение ссылки ещё не означает регулярное использование. Рекомендация: помочь оплатившим, но не активировавшимся за 7 дней; проверить инструкцию HAPP и ошибки подключения. Этот вывод не пересчитывается фильтрами.', 20, 904, 1880, 76, 16, colors.muted, 'normal'),
      ...navigator('act-nav', 'activation')
    ]
  },
  {
    key: 'retention', displayName: 'Удержание подписчиков', visuals: [
      textbox('ret-title', 'Удержание подписчиков', 20, 18, 840, 52),
      textbox('ret-subtitle', 'Сколько подписчиков возвращается; группы сформированы по месяцу первой оплаты', 20, 68, 1040, 40, 14, colors.muted, 'normal'),
      slicer('ret-activated', 'Subscriber Retention', 'Activated 7D', 'Активация за 7 дней', 1160, 20, 240),
      slicer('ret-plan', 'Subscriber Retention', 'Plan', 'Тариф', 1420, 20, 220),
      slicer('ret-channel', 'Subscriber Retention', 'Sales Channel', 'Канал продаж', 1660, 20, 240),
      card('ret-size', 'Subscriber Retention', 'Cohort Size', 'Подписки в выбранных группах', colors.blue, 20, 120, 340),
      card('ret-users', 'Subscriber Retention', 'M1 Retained Subscribers', 'Вернулись через 1 месяц', colors.teal, 380, 120, 340),
      card('ret-rate', 'Subscriber Retention', 'M1 Observed Subscriptions', 'Наблюдались через 1 месяц', colors.blue, 740, 120, 340),
      card('ret-m1', 'Subscriber Retention', 'M1 Retention', 'Возврат через 1 месяц', colors.purple, 1100, 120, 340),
      card('ret-m3', 'Subscriber Retention', 'M3 Retention', 'Возврат через 3 месяца', colors.amber, 1460, 120, 440, 'M3 Observed Subscriptions'),
      chart('ret-trend', 'lineChart', 'Возвращаемость по месяцам после оплаты', { table: 'Subscriber Retention', field: 'Month Number' }, [{ table: 'Subscriber Retention', field: 'Retention Rate' }], 20, 240, 920, 330, [colors.green], [{ table: 'Subscriber Retention', field: 'Observed Subscriptions' }, { table: 'Subscriber Retention', field: 'Retained Subscribers' }]),
      chart('ret-plan-bars', 'clusteredColumnChart', 'Возврат через 1 и 3 месяца по тарифам', { table: 'Subscriber Retention', field: 'Plan' }, [{ table: 'Subscriber Retention', field: 'M1 Retention' }, { table: 'Subscriber Retention', field: 'M3 Retention' }], 960, 240, 940, 330, [colors.purple, colors.amber]),
      matrix('ret-cohort', 'Удержание по месяцу первой оплаты', 'Subscriber Retention', ['Cohort Month'], ['Month Number'], [{ table: 'Subscriber Retention', field: 'Retention Rate' }], 20, 590, 1880, 270),
      textbox('ret-note', 'По всем данным, январь–июнь: через 3 месяца возвращается меньшая доля подписок, чем через 1; состав наблюдаемых групп различается. Рекомендация: изучить причины ухода до третьего месяца. Вывод не пересчитывается фильтрами.\nМесяц 0 - старт (100%), не повторный визит. Пусто - срок ещё не наступил; 0% - никто не вернулся. Учитываются только полные сроки наблюдения.', 20, 880, 1880, 100, 16, colors.muted, 'normal'),
      ...navigator('ret-nav', 'retention')
    ]
  },
  {
    key: 'activation-experiment', displayName: 'Проверка новой настройки', visuals: [
      textbox('exp-title', 'Проверка новой настройки', 20, 18, 900, 52),
      textbox('exp-subtitle', 'Сравнение обычной настройки и настройки с подсказками', 20, 68, 1040, 40, 14, colors.muted, 'normal'),
      slicer('exp-plan', 'Activation Experiment', 'Plan', 'Тариф', 1420, 20, 220),
      slicer('exp-channel', 'Activation Experiment', 'Sales Channel', 'Канал продаж', 1660, 20, 240),
      card('exp-control', 'Activation Experiment', 'Control Activation Rate', 'Активация · обычная настройка', colors.blue, 20, 120, 340),
      card('exp-treatment', 'Activation Experiment', 'Treatment Activation Rate', 'Активация · с подсказками', colors.teal, 380, 120, 340),
      card('exp-abs', 'Activation Experiment', 'Absolute Lift', 'Разность · процентные пункты', colors.text, 740, 120, 340),
      card('exp-rel', 'Activation Experiment', 'Relative Lift', 'Относительное изменение', colors.purple, 1100, 120, 340),
      card('exp-n', 'Activation Experiment', '# Experiment Subscriptions', 'Размер эксперимента', colors.amber, 1460, 120, 440),
      card('exp-control-n', 'Activation Experiment', 'Control Sample', 'Участники · обычная настройка', colors.blue, 20, 236, 340),
      card('exp-treatment-n', 'Activation Experiment', 'Treatment Sample', 'Участники · с подсказками', colors.teal, 380, 236, 340),
      card('exp-lower', 'Activation Experiment', 'Lift CI Lower', 'Нижняя граница оценки (95%)', colors.text, 740, 236, 340),
      card('exp-upper', 'Activation Experiment', 'Lift CI Upper', 'Верхняя граница оценки (95%)', colors.text, 1100, 236, 340),
      card('exp-p', 'Activation Experiment', 'Activation P Value', 'Проверка различий (p)', colors.text, 1460, 236, 440),
      chart('exp-activation', 'clusteredColumnChart', 'Активация по варианту настройки', { table: 'Activation Experiment', field: 'Onboarding Variant' }, [{ table: 'Activation Experiment', field: 'Experiment Activation Rate' }], 20, 354, 610, 260, [colors.teal]),
      chart('exp-link', 'clusteredColumnChart', 'Получение ссылки по варианту', { table: 'Activation Experiment', field: 'Onboarding Variant' }, [{ table: 'Activation Experiment', field: 'Experiment Link Fetch Rate' }], 650, 354, 610, 260, [colors.purple]),
      chart('exp-sample', 'clusteredColumnChart', 'Размер выборки', { table: 'Activation Experiment', field: 'Onboarding Variant' }, [{ table: 'Activation Experiment', field: '# Experiment Subscriptions' }], 1280, 354, 620, 260, [colors.blue]),
      matrix('exp-matrix', 'Сравнение результатов', 'Activation Experiment', ['Onboarding Variant'], [], [
        { table: 'Activation Experiment', field: '# Experiment Subscriptions' },
        { table: 'Activation Experiment', field: 'Experiment Activation Rate' },
        { table: 'Activation Experiment', field: 'Experiment Link Fetch Rate' },
      ], 20, 634, 1880, 216),
      textbox('exp-note', 'По всей выборке, январь–июнь: улучшение пока не доказано - диапазон оценки включает 0. Рекомендация: не объявлять победителя; заранее задать достаточную выборку и контролировать ошибки. Вывод не пересчитывается фильтрами.\nДля выбранного сегмента смотрите его диапазон и p: при p ≥ 0,05 различие не подтверждено. Для малых групп оценка скрыта (-). Срезы - предварительные проверки без поправки на множественные сравнения. Синтетические данные не раскрывают эффект исходного проекта.', 20, 872, 1880, 108, 16, colors.muted, 'normal'),
      ...navigator('exp-nav', 'activation-experiment')
    ]
  }
];

const themeName = 'VPNAnalyticsDark-a91c4e72.json';
const theme = {
  name: themeName,
  dataColors: [colors.blue, colors.teal, colors.green, colors.purple, colors.amber, colors.red, '#60A5FA', '#F472B6'],
  good: colors.green, neutral: colors.amber, bad: colors.red,
  maximum: colors.green, center: colors.amber, minimum: colors.red, null: colors.muted,
  firstLevelElements: colors.text,
  secondLevelElements: '#D1D5DB',
  thirdLevelElements: colors.grid,
  fourthLevelElements: colors.muted,
  background: colors.panel,
  secondaryBackground: '#243244',
  tableAccent: colors.blue,
  textClasses: {
    callout: { fontSize: 28, fontFace: 'Segoe UI Semibold', color: colors.text },
    title: { fontSize: 12, fontFace: 'Segoe UI Semibold', color: colors.text },
    header: { fontSize: 12, fontFace: 'Segoe UI Semibold', color: colors.text },
    label: { fontSize: 10, fontFace: 'Segoe UI', color: colors.text }
  },
  visualStyles: {
    '*': { '*': {
      title: [{ show: true, fontFamily: 'Segoe UI Semibold', fontSize: 13, fontColor: { solid: { color: colors.text } } }],
      background: [{ show: true, color: { solid: { color: colors.panel } }, transparency: 0 }],
      border: [{ show: true, color: { solid: { color: colors.border } }, radius: 8, width: 1 }],
      padding: [{ top: 8, bottom: 8, left: 8, right: 8 }],
      visualHeader: [{ show: false }]
    } },
    cardVisual: { '*': { background: [{ show: true, color: { solid: { color: colors.panel } }, transparency: 0 }], border: [{ show: true, color: { solid: { color: colors.border } } }] } },
    tableEx: { '*': { columnHeaders: [{ autoSizeColumnWidth: true, columnAdjustment: 'growToFit' }] } },
    pivotTable: { '*': { columnHeaders: [{ autoSizeColumnWidth: true, columnAdjustment: 'growToFit' }] } }
  }
};

async function main() {
  if (process.platform === 'win32') {
    const windows = execFileSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command',
      "Get-Process | Where-Object { $_.ProcessName -eq 'PBIDesktop' } | Select-Object -ExpandProperty MainWindowTitle"
    ], { encoding: 'utf8', windowsHide: true });
    if (/vpn-analytics|VPN Analytics/i.test(windows)) {
      throw new Error('Close the target Power BI Desktop report before generating its layout.');
    }
  }
  const previous = await readJsonIfExists(managedPath);
  const managed = Object.fromEntries(pageDefinitions.map((page) => [id(`page-${page.key}`), page.visuals.map((item) => item.name)]));
  // Only IDs recorded by the previous generation belong to this script. Keep manual visuals.
  const stale = [];
  for (const [pageId, visualIds] of Object.entries(previous)) {
    if (!/^[a-f0-9]{20}$/.test(pageId) || !Array.isArray(visualIds) || visualIds.some((name) => !/^[a-f0-9]{20}$/.test(name))) {
      throw new Error('Invalid generated-visual manifest; refusing to remove files.');
    }
    if (!managed[pageId]) throw new Error('Removing a generated page requires explicit migration of its manual content.');
    for (const visualId of visualIds) {
      if (!managed[pageId].includes(visualId)) stale.push(path.join(pagesRoot, pageId, 'visuals', visualId));
    }
  }
  for (const [file, schema] of [
    [path.join(repo, 'powerbi', 'vpn-analytics.pbip'), 'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json'],
    [path.join(path.dirname(definition), 'definition.pbir'), 'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json']
  ]) {
    const manifest = JSON.parse(await readFile(file, 'utf8'));
    manifest.$schema ??= schema;
    await writeFile(file, `${JSON.stringify(manifest, null, 2)}\n`);
  }
  const resolvedPages = path.resolve(pagesRoot);
  if (!resolvedPages.startsWith(path.resolve(definition) + path.sep) || path.basename(resolvedPages) !== 'pages') {
    throw new Error(`Refusing to replace unexpected directory: ${resolvedPages}`);
  }
  await mkdir(resolvedPages, { recursive: true });
  await mkdir(resourcesRoot, { recursive: true });

  const pageOrder = [];
  for (const page of pageDefinitions) {
    const pageId = id(`page-${page.key}`);
    pageOrder.push(pageId);
    const pageDir = path.join(resolvedPages, pageId);
    await mkdir(path.join(pageDir, 'visuals'), { recursive: true });
    const pageJson = {
      $schema: pageSchema,
      name: pageId,
      displayName: page.displayName,
      displayOption: 'FitToPage',
      height: 1080,
      width: 1920,
      objects: {
        background: [{ properties: { color: fill(colors.bg), transparency: lit('0D') } }],
        outspace: [{ properties: { color: fill('#0B1220'), transparency: lit('0D') } }]
      }
    };
    const pagePath = path.join(pageDir, 'page.json');
    const existingPage = await readJsonIfExists(pagePath);
    await writeFile(pagePath, `${JSON.stringify({ ...pageJson, ...existingPage, displayName: page.displayName }, null, 2)}\n`);
    for (const item of page.visuals) {
      const visualDir = path.join(pageDir, 'visuals', item.name);
      await mkdir(visualDir, { recursive: true });
      const visualPath = path.join(visualDir, 'visual.json');
      const existing = await readJsonIfExists(visualPath);
      const previousVisual = existing.visual?.visualType === item.visual.visualType ? existing.visual : {};
      const merged = {
        ...existing, ...item, $schema: existing.$schema ?? item.$schema,
        visual: {
          ...previousVisual, ...item.visual,
          objects: { ...previousVisual.objects, ...item.visual.objects },
          visualContainerObjects: { ...previousVisual.visualContainerObjects, ...item.visual.visualContainerObjects }
        }
      };
      await writeFile(visualPath, `${JSON.stringify(merged, null, 2)}\n`);
    }
  }

  await writeFile(path.join(resolvedPages, 'pages.json'), `${JSON.stringify({ $schema: pagesSchema, pageOrder, activePageName: pageOrder[0] }, null, 2)}\n`);
  await writeFile(path.join(resourcesRoot, themeName), `${JSON.stringify(theme, null, 2)}\n`);

  const reportPath = path.join(definition, 'report.json');
  const report = JSON.parse(await readFile(reportPath, 'utf8'));
  report.themeCollection.customTheme = {
    name: themeName,
    reportVersionAtImport: report.themeCollection.baseTheme.reportVersionAtImport,
    type: 'RegisteredResources'
  };
  report.resourcePackages = report.resourcePackages.filter((p) => p.name !== 'RegisteredResources');
  report.resourcePackages.push({ name: 'RegisteredResources', type: 'RegisteredResources', items: [{ name: themeName, path: themeName, type: 'CustomTheme' }] });
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`);

  for (const folder of stale) {
    const resolved = path.resolve(folder);
    if (!resolved.startsWith(path.resolve(pagesRoot) + path.sep)) throw new Error('Unsafe visual removal path');
    await rm(resolved, { recursive: true, force: true });
  }
  let actualVisuals = 0;
  for (const pageId of pageOrder) {
    for (const entry of await readdir(path.join(pagesRoot, pageId, 'visuals'), { withFileTypes: true })) {
      if (entry.isDirectory() && Object.keys(await readJsonIfExists(path.join(pagesRoot, pageId, 'visuals', entry.name, 'visual.json'))).length) actualVisuals++;
    }
  }
  const expectedVisuals = pageDefinitions.reduce((sum, page) => sum + page.visuals.length, 0);
  if (pageOrder.length !== 4 || actualVisuals < expectedVisuals) throw new Error('Unexpected report structure');
  await writeFile(managedPath, `${JSON.stringify(managed, null, 2)}\n`);
  console.log(JSON.stringify({ pages: pageOrder.length, visuals: actualVisuals, generatedVisuals: expectedVisuals, theme: themeName }));
}

async function readJsonIfExists(file) {
  try { return JSON.parse(await readFile(file, 'utf8')); }
  catch (error) { if (error.code === 'ENOENT') return {}; throw error; }
}

await main();
