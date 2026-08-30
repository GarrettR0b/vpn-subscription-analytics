# Week 1 acceptance criteria

Вертикальный срез считается готовым, когда выполняются все условия:

- генерация `small` воспроизводится одним и тем же seed;
- каждый CSV проходит Python QA без ошибок;
- PostgreSQL поднимается через Docker Compose;
- core tables загружаются с сохранением PK/FK и временной логики;
- `analytics.mart_workspace_activation` содержит одну строку на eligible workspace;
- SQL data-quality checks возвращают только `PASS`;
- notebook выполняется сверху вниз без ручного вмешательства;
- в README явно указано, что все данные и результаты синтетические.

Команда полного локального прогона после активации `.venv`:

```powershell
.\scripts\run_week1.ps1 -Profile small
```
