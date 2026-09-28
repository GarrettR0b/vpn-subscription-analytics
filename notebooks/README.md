# Notebooks

`01_vpn_activation.ipynb` — выполненный анализ месячной платящей базы и 7-дневной
активации подписок через HAPP. `01_vpn_activation.html` — автономная версия.

`02_activation_experiment.ipynb` — A/B-тест постоплатной инструкции HAPP с uplift,
доверительным интервалом и расчётом размера выборки.

`03_retention_cohorts.ipynb` — usage retention по возрасту когорты, cohort heatmap,
M1-сегменты, выводы и рекомендации.

Пересборка:

```powershell
python scripts/create_starter_notebook.py
python scripts/create_experiment_notebook.py
python scripts/create_retention_notebook.py
```

Python-метрики служат независимой сверкой одноимённых PostgreSQL-витрин.
