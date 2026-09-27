# Week 1 acceptance criteria

- генерация профиля `small` воспроизводится одним seed;
- каждый CSV проходит Python QA без ошибок;
- PostgreSQL поднимается через Docker Compose;
- PK/FK и временная логика core tables сохраняются;
- `analytics.mart_user_activation` содержит одну строку на eligible user;
- SQL checks возвращают только `PASS`;
- Python и SQL дают одинаковые activation counts;
- notebook выполняется сверху вниз без ручного вмешательства;
- README явно маркирует данные и результаты как synthetic.

Полный локальный прогон после активации `.venv`:

```powershell
.\scripts\run_week1.ps1 -Profile small
```
