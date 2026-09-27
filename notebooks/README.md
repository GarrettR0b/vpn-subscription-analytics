# Notebooks

`01_vpn_activation.ipynb` — выполненный сверху вниз анализ onboarding и 7-day activation.
`01_vpn_activation.html` — автономная версия для просмотра без Jupyter.

Пересборка после генерации данных:

```powershell
.\.venv\Scripts\python.exe scripts\create_starter_notebook.py
```

Reader-facing метрики должны поступать из PostgreSQL marts; Python-реализация используется
как независимая сверка SQL-контракта.
