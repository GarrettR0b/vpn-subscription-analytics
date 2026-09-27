# Source dictionary

| Source fact | Origin | Analytical use |
|---|---|---|
| user registration | сайт / Telegram-бот | acquisition и signup source |
| subscription purchase | платёжный backend | тариф, канал продажи, start/end |
| link issued | backend подписок | доступность конфигурации |
| link first fetched | subscription endpoint, user agent HAPP | первый шаг после покупки |
| payment attempt | платёжный backend | cash revenue и ошибки оплаты |
| proxy session | серверные access logs | активность, качество и трафик |
| proxy server | инфраструктурный реестр | страна, протокол и capacity |

У проекта нет client-side event stream: HAPP является внешним приложением. Поэтому
аналитический контракт опирается только на серверные факты, доступные владельцу сервиса.
