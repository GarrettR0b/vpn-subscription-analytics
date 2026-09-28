# BI dashboard contract

BI-инструмент подключается к PostgreSQL analytics marts:

- `analytics.mart_monthly_business` — база, активность, churn, MRR, cash revenue, трафик;
- `analytics.mart_subscriber_activation` — путь от оплаты до использования через HAPP.
- `analytics.mart_subscriber_retention` — usage retention по месяцу покупки и возрасту
  когорты.
- `analytics.mart_activation_experiment` — рандомизированный тест постоплатной инструкции
  HAPP.

Реализованы четыре вкладки: **Business Overview**, **Activation**, **Retention** и
**Experiment**. Вторая показывает
7-day funnel, динамику по месяцу покупки, различия сайта и Telegram-бота, тарифные
сегменты и quality guardrails; третья — M1–M3, когортные кривые и retention по сегментам;
четвёртая — uplift, 95% ДИ, p-value, размер выборки, secondary metrics и guardrail.
В блоке условий тарифов также зафиксирован ограниченный
free trial на 4 дня; trial-to-paid conversion пока не рассчитывается. Публичная версия использует только synthetic data;
выполненный HTML-notebook служит offline backup.
