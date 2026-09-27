# Business problem

## Product

`ShieldRoute` — синтетический B2C VPN-сервис с trial, месячными и годовыми подписками.
Единица продуктового решения — `user`: именно пользователь регистрируется, подключает
устройства, создаёт VPN-сессии и оплачивает подписку.

## Decision

Product manager должен понять, где новые пользователи выпадают между регистрацией,
установкой приложения и регулярным защищённым использованием. Первая гипотеза — smart
location onboarding, автоматически предлагающий подходящий сервер и протокол, повышает
7-day activation.

## Audience

- Product Manager — onboarding и trial conversion;
- Growth — acquisition channels и paid conversion;
- Operations — connection failures, latency и server load;
- Finance — выручка и инфраструктурная себестоимость;
- Data/BI — единые определения, витрины и контроль качества.

## Week 1 scope

Первый вертикальный срез отвечает на один вопрос: можно ли воспроизводимо рассчитать
7-day activation одинаково в Python и PostgreSQL. Retention, unit economics, полноценный
experiment readout и DataLens следуют после устойчивого базового слоя.
