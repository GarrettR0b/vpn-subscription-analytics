# Event dictionary

| Event | Actor | Meaning | Required properties |
|---|---|---|---|
| `signup_completed` | user | регистрация завершена | channel, country |
| `app_installed` | user/device | приложение установлено | platform, app_version |
| `app_opened` | user/device | первое открытие | platform |
| `server_list_viewed` | user/device | просмотр списка локаций | recommended_server_id |
| `protocol_selected` | user/device | выбран VPN-протокол | protocol, automatic |
| `vpn_connection_succeeded` | user/device | туннель успешно поднят | server_id, protocol |
| `vpn_connection_failed` | user/device | подключение завершилось ошибкой | error_code, protocol |
| `trial_started` | user | начат trial | plan |
| `subscription_converted` | user | trial перешёл в оплату | plan, price_usd |

События имеют уникальный `event_id`, UTC timestamp и связаны с user/device. Точный факт
подключения и технические меры хранятся в `core.vpn_sessions`.
