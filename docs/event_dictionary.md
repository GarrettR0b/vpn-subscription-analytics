# Event dictionary

| Event | Actor | Когда фиксируется | Ключевые свойства |
|---|---|---|---|
| `workspace_created` | owner | создан workspace | channel, country |
| `owner_signed_up` | owner | завершена регистрация | device |
| `knowledge_base_connect_started` | owner/admin | начато подключение | source_type |
| `knowledge_base_connected` | owner/admin | источник успешно доступен | source_type |
| `knowledge_base_connect_failed` | owner/admin | подключение завершилось ошибкой | error_code |
| `teammate_invited` | owner/admin | отправлено первое приглашение | invited_role |
| `teammate_joined` | invited user | пользователь присоединился | role |
| `ai_suggestion_generated` | agent | создан draft | model_name, ticket_id |
| `ai_suggestion_accepted` | agent | draft принят | edited, ticket_id |
| `subscription_converted` | owner | trial стал paid | plan |

События имеют уникальный `event_id`, UTC timestamp и связаны с workspace. Event order
проверяется Python и SQL checks.
