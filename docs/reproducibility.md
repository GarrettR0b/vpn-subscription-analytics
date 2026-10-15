# Воспроизведение проекта

Основной сценарий установки и открытия Power BI описан в [README](../README.md).
Результаты проверок и контрольные показатели - в [validation.md](validation.md).

## Чистое окружение

Используйте новую копию репозитория и новую виртуальную среду Python 3.11+:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --no-cache-dir -e ".[analysis,dev]"
python -m pip check
```

Для проверки исходников не нужны прежняя `.venv`, generated CSV, notebook-кэши,
локальные данные модели Power BI или React-зависимости. Generated CSV создаются заново.

## Отдельная демонстрационная БД

Подключение указывается через `DATABASE_URL`. Создайте отдельную БД `vpn_analytics`
с UTC; при использовании Docker настройки сервиса и порт 5433 заданы в Compose.
Не направляйте проверочный прогон в БД с нужными данными: loader пересоздаёт `core`
и `analytics`. Подтверждение должно совпадать с именем фактически подключённой БД.

```powershell
$env:DATABASE_URL = "postgresql://analytics:analytics@127.0.0.1:5433/vpn_analytics"
$env:TEST_DATABASE_URL = $env:DATABASE_URL
.\scripts\run_week1.ps1 -Profile small -ResetDatabase vpn_analytics
python scripts/create_experiment_notebook.py
python scripts/create_retention_notebook.py
python -m ruff check src tests scripts
```

Сценарий выполняет генерацию, 25 проверок CSV, транзакционную загрузку, 14 SQL-проверок,
SQL/Python-сверку, первый notebook и тесты. Два остальных notebook запускаются отдельно.
`TEST_DATABASE_URL` включает три дополнительных SQL-теста с SELECT и тестовыми CTE.

## Ядро notebook

Notebook запускается из своего каталога; путь к данным хранится относительно него.
Проверьте, что ядро `python3` использует новую виртуальную среду, а не старую глобальную
регистрацию. При необходимости зарегистрируйте ядро внутри текущей `.venv`:

```powershell
python -m ipykernel install --sys-prefix --name python3 --display-name "Python 3 (VPN analytics)"
python -m jupyter kernelspec list
```

## Публичный состав и секреты

В репозиторий входят код, SQL/DAX, тесты, samples, три выполненных notebook с HTML,
PBIP/PBIR/TMDL и документация. Локальные handoff-файлы, служебный brief, кэши, generated
CSV и резервные копии не входят в публичный состав.

Проверка [Gitleaks](https://github.com/gitleaks/gitleaks) выполняется локально,
без отправки содержимого проекта:

```powershell
gitleaks git . --log-opts="--all --full-history" --redact=100
gitleaks git . --staged --redact=100
```

Проверять нужно и историю, и текущий состав файлов. `.gitleaksignore` содержит одно
точечное исключение для исторической контрольной суммы: значение проверено как SHA-256
исходного файла в том же коммите. Остальные правила сканера остаются включёнными.
Демонстрационные пароли localhost из примеров не являются рабочими учётными данными.

## Границы проверки

Успешная чистая установка подтверждает проверенную версию Python и PostgreSQL, но
не гарантирует все сочетания поддерживаемых версий и ОС. Power BI Desktop требует
отдельной проверки открытия, учётных данных источника и обновления Import-модели.
Перед публикацией перечитайте актуальные ограничения в `validation.md`.
