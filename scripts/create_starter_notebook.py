from __future__ import annotations

import argparse
import json
from pathlib import Path

import nbformat as nbf
import pandas as pd

from vpn_analytics.metrics import monthly_business_records, subscriber_activation_records


def _arguments() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Create and execute the VPN analytics notebook.")
    parser.add_argument("--input-dir", type=Path, default=project_root / "data" / "generated")
    parser.add_argument(
        "--output", type=Path, default=project_root / "notebooks" / "01_vpn_activation.ipynb"
    )
    parser.add_argument(
        "--html-output",
        type=Path,
        default=project_root / "notebooks" / "01_vpn_activation.html",
    )
    parser.add_argument("--no-execute", action="store_true")
    return parser.parse_args()


def _rate_text(value: float) -> str:
    return f"{value:.1%}".replace(".", ",")


def build_notebook(input_dir: Path) -> nbf.NotebookNode:
    activation = pd.DataFrame(subscriber_activation_records(input_dir))
    monthly = pd.DataFrame(monthly_business_records(input_dir))
    activation_rate = float(activation["activated_7d"].mean())
    link_fetched_7d = activation["first_link_fetched_at"].notna() & (
        activation["first_link_fetched_at"]
        < activation["subscription_started_at"] + pd.to_timedelta(7, unit="D")
    )
    link_fetch_rate = float(link_fetched_7d.mean())
    channel_rates = activation.groupby("sales_channel")["activated_7d"].mean()

    notebook = nbf.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
    }
    notebook["cells"] = [
        nbf.v4.new_markdown_cell(
            "# Аналитика подписочного VPN через HAPP\n\n"
            "Воспроизводимый анализ синтетического сервиса `ShieldRoute`: продажи через сайт и "
            "Telegram-бот, выдача ссылки подписки, её загрузка в HAPP и использование прокси."
        ),
        nbf.v4.new_markdown_cell(
            "## Краткий вывод\n\n"
            f"- Стабильное платящее ядро — **{int(monthly['regular_paid_users'].min())}** "
            "пользователей в каждом полном месяце; новые и временные пользователи считаются сверх него.\n"
            f"- Всего активных платящих пользователей по месяцам: "
            f"**{int(monthly['monthly_active_paid_users'].min())}–"
            f"{int(monthly['monthly_active_paid_users'].max())}**.\n"
            f"- Среди **{len(activation)}** новых оплаченных подписок полная 7-дневная активация — "
            f"**{_rate_text(activation_rate)}**, загрузка ссылки в HAPP — "
            f"**{_rate_text(link_fetch_rate)}**.\n"
            f"- Активация по каналу продажи: Telegram-бот "
            f"**{_rate_text(float(channel_rates['telegram_bot']))}**, сайт "
            f"**{_rate_text(float(channel_rates['website']))}**. Это описательное сравнение."
        ),
        nbf.v4.new_markdown_cell(
            "## Контекст и метод\n\n"
            "Путь пользователя: **сайт / Telegram-бот → оплата → персональная ссылка → HAPP → "
            "прокси-сессии**. Собственного клиентского приложения у сервиса нет.\n\n"
            "Подписка активирована за 7 дней, если ссылка загружена в HAPP, проведено не менее "
            "трёх успешных прокси-сессий в два разных UTC-дня и накоплено не менее 30 минут "
            "защищённого трафика.\n\n"
            "Стабильное ядро — пользователи, чья подписка началась до периода наблюдения и "
            "оставалась активной до его конца. Все данные и результаты синтетические."
        ),
        nbf.v4.new_code_cell(
            "import json\n"
            "from pathlib import Path\n\n"
            "import matplotlib.pyplot as plt\n"
            "import pandas as pd\n\n"
            "from vpn_analytics.data_quality import validate_dataset\n"
            "from vpn_analytics.metrics import monthly_business_records, subscriber_activation_records\n\n"
            'ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()\n'
            'DATA_DIR = ROOT / "data" / "generated"\n'
            'plt.style.use("seaborn-v0_8-whitegrid")\n'
            'COLORS = {"base": "#173F5F", "total": "#F2A900", "accent": "#2A9D8F"}'
        ),
        nbf.v4.new_markdown_cell("## Данные и контроль качества"),
        nbf.v4.new_code_cell(
            'manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))\n'
            "quality = pd.DataFrame(\n"
            '    [{"check": item.check_name, "failures": item.failure_count, '
            '"status": item.status} for item in validate_dataset(DATA_DIR)]\n'
            ")\n"
            'assert quality["failures"].sum() == 0\n'
            'display(pd.Series(manifest["counts"], name="rows").to_frame())\n'
            "display(quality)"
        ),
        nbf.v4.new_code_cell(
            "activation = pd.DataFrame(subscriber_activation_records(DATA_DIR))\n"
            "monthly = pd.DataFrame(monthly_business_records(DATA_DIR))\n"
            'activation["link_fetched_7d"] = activation["first_link_fetched_at"].notna() & (\n'
            '    activation["first_link_fetched_at"]\n'
            '    < activation["subscription_started_at"] + pd.to_timedelta(7, unit="D")\n'
            ")\n"
            'monthly["month"] = pd.to_datetime(monthly["month_start"]).dt.strftime("%b %Y")\n'
            "activation.head(3)"
        ),
        nbf.v4.new_markdown_cell("## Результаты"),
        nbf.v4.new_code_cell(
            'link = activation["link_fetched_7d"]\n'
            'success = activation["first_successful_connection_at"].notna()\n'
            "funnel = pd.Series({\n"
            '    "Оплачено": len(activation),\n'
            '    "Ссылка загружена в HAPP": link.sum(),\n'
            '    "Есть успешное подключение": (link & success).sum(),\n'
            '    "3+ успешных сессии": (link & activation["successful_sessions_7d"].ge(3)).sum(),\n'
            '    "Также 2+ активных дня": (link & activation["successful_sessions_7d"].ge(3) & activation["active_days_7d"].ge(2)).sum(),\n'
            '    "Активация за 7 дней": activation["activated_7d"].sum(),\n'
            '}, name="subscriptions").to_frame()\n'
            'funnel["share_of_paid"] = funnel["subscriptions"] / len(activation)\n'
            "funnel"
        ),
        nbf.v4.new_code_cell(
            'ax = funnel.iloc[::-1]["subscriptions"].plot.barh(figsize=(9, 5), color=COLORS["base"])\n'
            'ax.set(title="Путь новых подписок к 7-дневной активации", xlabel="Подписки", ylabel="")\n'
            "ax.set_xlim(0, len(activation) * 1.08)\n"
            "for bar in ax.patches:\n"
            '    ax.text(bar.get_width() + 3, bar.get_y() + bar.get_height() / 2, f"{bar.get_width():.0f}", va="center")\n'
            "plt.tight_layout();"
        ),
        nbf.v4.new_code_cell(
            "monthly_view = monthly[[\n"
            '    "month", "active_paid_subscribers", "monthly_active_paid_users",\n'
            '    "regular_paid_users", "new_paid_users", "churned_users",\n'
            '    "cash_revenue_rub", "normalized_mrr_rub", "connection_failure_rate", "traffic_gb",\n'
            "]].copy()\n"
            "monthly_view"
        ),
        nbf.v4.new_code_cell(
            'ax = monthly.set_index("month")[["regular_paid_users", "monthly_active_paid_users"]].plot(\n'
            '    kind="bar", figsize=(10, 5), color=[COLORS["base"], COLORS["total"]]\n'
            ")\n"
            'ax.set(title="Стабильное ядро и все активные платящие пользователи", xlabel="", ylabel="Пользователи")\n'
            'ax.legend(["Стабильное ядро", "Всего активных платящих"])\n'
            'ax.set_ylim(0, monthly["monthly_active_paid_users"].max() * 1.15)\n'
            "plt.xticks(rotation=0)\n"
            "plt.tight_layout();"
        ),
        nbf.v4.new_code_cell(
            'channels = activation.groupby("sales_channel").agg(\n'
            '    paid_subscriptions=("subscription_id", "size"),\n'
            '    link_fetch_rate=("link_fetched_7d", "mean"),\n'
            '    activation_rate=("activated_7d", "mean"),\n'
            ').sort_values("activation_rate", ascending=False)\n'
            "channels"
        ),
        nbf.v4.new_code_cell(
            'ax = channels["activation_rate"].plot.bar(figsize=(7, 4), color=COLORS["accent"])\n'
            'ax.set(title="7-дневная активация по каналу продажи", xlabel="", ylabel="Доля")\n'
            "ax.set_ylim(0, 1)\n"
            'ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")\n'
            "plt.xticks(rotation=0)\n"
            "plt.tight_layout();"
        ),
        nbf.v4.new_markdown_cell(
            "## Выводы\n\n"
            f"1. Генератор удерживает заданное стабильное ядро в **"
            f"{int(monthly['regular_paid_users'].min())}** пользователей ежемесячно.\n"
            f"2. Основной резерв находится после оплаты: полная активация составляет "
            f"**{_rate_text(activation_rate)}** при загрузке ссылки в HAPP у "
            f"**{_rate_text(link_fetch_rate)}** новых подписок.\n"
            "3. Telegram-бот выглядит сильнее сайта по активации, но синтетическое "
            "наблюдательное сравнение не является причинным эффектом.\n"
            "4. Для эксплуатации рядом с ростом базы нужно контролировать failure rate, "
            "трафик, cash revenue и нормализованный MRR."
        ),
    ]
    return notebook


def main() -> int:
    args = _arguments()
    notebook = build_notebook(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, args.output)
    if not args.no_execute:
        from nbclient import NotebookClient

        notebook = NotebookClient(
            notebook,
            timeout=180,
            kernel_name="python3",
            resources={"metadata": {"path": str(args.output.parent)}},
        ).execute()
        nbf.write(notebook, args.output)

        from nbconvert import HTMLExporter

        html_body, _ = HTMLExporter(template_name="lab").from_notebook_node(notebook)
        args.html_output.write_text(html_body, encoding="utf-8")
    print(
        json.dumps(
            {
                "notebook": str(args.output),
                "html": str(args.html_output) if not args.no_execute else None,
                "executed": not args.no_execute,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
