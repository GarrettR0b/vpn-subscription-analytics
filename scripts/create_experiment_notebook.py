from __future__ import annotations

import argparse
import json
from pathlib import Path

import nbformat as nbf

from vpn_analytics.metrics import (
    activation_experiment_records,
    activation_experiment_statistics,
)


def _arguments() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Create the activation A/B-test notebook.")
    parser.add_argument("--input-dir", type=Path, default=root / "data" / "generated")
    parser.add_argument(
        "--output", type=Path, default=root / "notebooks" / "02_activation_experiment.ipynb"
    )
    parser.add_argument(
        "--html-output",
        type=Path,
        default=root / "notebooks" / "02_activation_experiment.html",
    )
    parser.add_argument("--no-execute", action="store_true")
    return parser.parse_args()


def _percent(value: float) -> str:
    return f"{value:.1%}".replace(".", ",")


def build_notebook(input_dir: Path) -> nbf.NotebookNode:
    records = activation_experiment_records(input_dir)
    result = activation_experiment_statistics(records)
    decision = (
        "эффект подтверждён"
        if result["statisticallySignificant"] and result["ciLow"] > 0
        else "данных недостаточно для запуска на всех пользователей"
    )

    notebook = nbf.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
    }
    notebook["cells"] = [
        nbf.v4.new_markdown_cell(
            "# A/B-тест онбординга VPN через HAPP\n\n"
            "Синтетический рандомизированный эксперимент после покупки подписки: стандартная "
            "выдача ссылки против автоматического напоминания с короткой инструкцией настройки."
        ),
        nbf.v4.new_markdown_cell(
            "## tl;dr\n\n"
            f"- Control: **{result['controlSubscriptions']}** подписок, activation "
            f"**{_percent(result['controlActivationRate'])}**.\n"
            f"- Treatment: **{result['treatmentSubscriptions']}** подписок, activation "
            f"**{_percent(result['treatmentActivationRate'])}**.\n"
            f"- Наблюдаемый эффект: **{result['absoluteEffect'] * 100:+.1f} п.п.**, "
            f"95% ДИ **[{result['ciLow'] * 100:+.1f}; {result['ciHigh'] * 100:+.1f}] п.п.**, "
            f"p-value **{result['pValue']:.3f}**.\n"
            f"- Решение: **{decision}**; для MDE 12 п.п. требуется около "
            f"**{result['requiredSampleSize']}** участников."
        ),
        nbf.v4.new_markdown_cell(
            "## Context & Methods\n\n"
            "**Гипотеза:** напоминание с инструкцией HAPP повышает 7-day activation. "
            "Primary metric — доля подписок, которые за 7 дней загрузили ссылку, провели не "
            "менее трёх успешных сессий в два UTC-дня и набрали 30 минут трафика. "
            "Secondary metrics — загрузка ссылки и time-to-value; guardrail — доля ошибок.\n\n"
            "Распределение 50/50 выполняется после покупки. Используется двусторонний z-тест "
            "двух долей, α=0,05, 95% ДИ для разности долей и планирование размера выборки с "
            "power=80%. Все данные синтетические."
        ),
        nbf.v4.new_code_cell(
            "from pathlib import Path\n\n"
            "import matplotlib.pyplot as plt\n"
            "import pandas as pd\n\n"
            "from vpn_analytics.metrics import (\n"
            "    activation_experiment_records, activation_experiment_statistics,\n"
            ")\n\n"
            'ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()\n'
            'DATA_DIR = ROOT / "data" / "generated"\n'
            'plt.style.use("seaborn-v0_8-whitegrid")\n'
            'COLORS = {"control": "#64748B", "treatment": "#2A9D8F"}'
        ),
        nbf.v4.new_markdown_cell("## Data"),
        nbf.v4.new_code_cell(
            "experiment = pd.DataFrame(activation_experiment_records(DATA_DIR))\n"
            'result = activation_experiment_statistics(experiment.to_dict(orient="records"))\n'
            'balance = experiment.groupby("onboarding_variant").agg(\n'
            '    subscriptions=("subscription_id", "size"),\n'
            '    activation_rate=("activated_7d", "mean"),\n'
            ").reset_index()\n"
            'assert set(balance["onboarding_variant"]) == {"control", "treatment"}\n'
            "balance"
        ),
        nbf.v4.new_markdown_cell("## Results"),
        nbf.v4.new_code_cell(
            'pd.Series(result, name="value").to_frame().loc[[\n'
            '    "observedSampleSize", "requiredSampleSize", "absoluteEffect",\n'
            '    "relativeLift", "ciLow", "ciHigh", "pValue", "statisticallySignificant",\n'
            "]]"
        ),
        nbf.v4.new_code_cell(
            "fig, axes = plt.subplots(1, 2, figsize=(11, 4))\n"
            "axes[0].bar(\n"
            '    balance["onboarding_variant"], balance["activation_rate"],\n'
            '    color=[COLORS[value] for value in balance["onboarding_variant"]],\n'
            ")\n"
            'axes[0].set(title="7-day activation по варианту", ylabel="Доля", xlabel="")\n'
            "axes[0].set_ylim(0, 1)\n"
            'axes[0].yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")\n'
            'effect = result["absoluteEffect"] * 100\n'
            "axes[1].errorbar(\n"
            "    effect, 0,\n"
            '    xerr=[[effect - result["ciLow"] * 100], [result["ciHigh"] * 100 - effect]],\n'
            '    fmt="o", color=COLORS["treatment"], capsize=6, markersize=8,\n'
            ")\n"
            'axes[1].axvline(0, color="#334155", linewidth=1)\n'
            'axes[1].set(title="Эффект treatment и 95% ДИ", xlabel="Разница, п.п.", yticks=[])\n'
            'axes[1].text(effect, 0.08, f"{effect:+.1f} п.п.; p={result["pValue"]:.3f}", ha="center")\n'
            "plt.tight_layout();"
        ),
        nbf.v4.new_code_cell(
            'experiment["link_fetched_7d"] = experiment["first_link_fetched_at"].notna() & (\n'
            '    experiment["first_link_fetched_at"]\n'
            '    < experiment["subscription_started_at"] + pd.to_timedelta(7, unit="D")\n'
            ")\n"
            'diagnostics = experiment.groupby("onboarding_variant").agg(\n'
            '    link_fetch_rate=("link_fetched_7d", "mean"),\n'
            '    median_time_to_value_hours=("time_to_first_value_hours", "median"),\n'
            '    failed_attempts=("failed_attempts_7d", "sum"),\n'
            '    total_attempts=("total_attempts_7d", "sum"),\n'
            ")\n"
            'diagnostics["connection_failure_rate"] = (\n'
            '    diagnostics["failed_attempts"] / diagnostics["total_attempts"]\n'
            ")\n"
            'diagnostics[["link_fetch_rate", "median_time_to_value_hours", "connection_failure_rate"]]'
        ),
        nbf.v4.new_markdown_cell(
            "## Takeaways\n\n"
            f"1. Treatment дал наблюдаемый uplift **{result['absoluteEffect'] * 100:+.1f} п.п.**, "
            "но доверительный интервал пересекает ноль.\n"
            "2. Нельзя объявлять победителя только по положительному point estimate: текущая выборка "
            f"**{result['observedSampleSize']}** меньше расчётной **{result['requiredSampleSize']}**.\n"
            "3. Эксперимент следует продолжить до плановой выборки, контролируя ошибки подключения; "
            "останавливать его по промежуточному p-value нельзя."
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
        from nbconvert import HTMLExporter

        notebook = NotebookClient(
            notebook,
            timeout=180,
            kernel_name="python3",
            resources={"metadata": {"path": str(args.output.parent)}},
        ).execute()
        nbf.write(notebook, args.output)
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
