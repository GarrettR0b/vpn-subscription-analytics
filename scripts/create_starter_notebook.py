from __future__ import annotations

import argparse
import json
from pathlib import Path

import nbformat as nbf
import pandas as pd

from vpn_analytics.metrics import user_activation_records


def _arguments() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Create and execute the VPN activation notebook.")
    parser.add_argument("--input-dir", type=Path, default=project_root / "data" / "generated")
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "notebooks" / "01_vpn_activation.ipynb",
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
    frame = pd.DataFrame(user_activation_records(input_dir))
    activation_rate = float(frame["activated_7d"].mean())
    conversion_by_activation = frame.groupby("activated_7d")["converted_at"].apply(
        lambda values: values.notna().mean()
    )
    activated_conversion = float(conversion_by_activation.get(True, float("nan")))
    nonactivated_conversion = float(conversion_by_activation.get(False, float("nan")))
    experiment = frame.dropna(subset=["experiment_variant"])
    experiment_rates = experiment.groupby("experiment_variant")["activated_7d"].mean()
    control_rate = float(experiment_rates.get("control", float("nan")))
    treatment_rate = float(experiment_rates.get("treatment", float("nan")))
    lift_pp = (treatment_rate - control_rate) * 100

    notebook = nbf.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
    }
    notebook["cells"] = [
        nbf.v4.new_markdown_cell(
            "# Диагностика 7-дневной активации подписочного VPN\n\n"
            "Воспроизводимый стартовый анализ полностью синтетического сервиса `ShieldRoute`. "
            "Metric contract хранится в `docs/metric_dictionary.md`, SQL-реализация — в "
            "`sql/marts/001_mart_user_activation.sql`."
        ),
        nbf.v4.new_markdown_cell(
            "## tl;dr\n\n"
            f"- В выборке **{len(frame):,}** eligible users; 7-day activation — "
            f"**{_rate_text(activation_rate)}**.\n"
            f"- В synthetic experiment: control **{_rate_text(control_rate)}**, treatment "
            f"**{_rate_text(treatment_rate)}**, разница **{lift_pp:+.1f} п.п.**\n"
            f"- Paid conversion: activated **{_rate_text(activated_conversion)}**, non-activated "
            f"**{_rate_text(nonactivated_conversion)}**. Связь описательная, не причинная."
        ),
        nbf.v4.new_markdown_cell(
            "## Context & Methods\n\n"
            "**Решение:** определить главный провал между регистрацией, установкой приложения и "
            "регулярным VPN-использованием; оценить smart-location onboarding. Единица анализа — user.\n\n"
            "**Каноническая активация:** приложение установлено; минимум 3 успешных VPN-сессии "
            "минимум в 2 UTC-дня; не менее 30 protected minutes в первые 7 дней.\n\n"
            "### Key Assumptions\n\n"
            "Порог 30 минут — портфолио-допущение. В production его нужно калибровать по retention. "
            "Все наблюдаемые эффекты и числа созданы генератором и не относятся к реальной компании."
        ),
        nbf.v4.new_code_cell(
            "import json\n"
            "from pathlib import Path\n\n"
            "import matplotlib.pyplot as plt\n"
            "import pandas as pd\n\n"
            "from vpn_analytics.data_quality import validate_dataset\n"
            "from vpn_analytics.metrics import user_activation_records\n\n"
            'ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()\n'
            'DATA_DIR = ROOT / "data" / "generated"\n'
            'plt.style.use("seaborn-v0_8-whitegrid")'
        ),
        nbf.v4.new_markdown_cell("## Data"),
        nbf.v4.new_code_cell(
            'manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))\n'
            "quality = pd.DataFrame(\n"
            "    [\n"
            '        {"check": result.check_name, "failures": result.failure_count, "status": result.status}\n'
            "        for result in validate_dataset(DATA_DIR)\n"
            "    ]\n"
            ")\n"
            'assert quality["failures"].sum() == 0\n'
            'display(pd.Series(manifest["counts"], name="rows").to_frame())\n'
            "display(quality)"
        ),
        nbf.v4.new_code_cell(
            "activation = pd.DataFrame(user_activation_records(DATA_DIR))\nactivation.head(3)"
        ),
        nbf.v4.new_markdown_cell("## Results"),
        nbf.v4.new_code_cell(
            "funnel = pd.Series(\n"
            "    {\n"
            '        "Eligible users": len(activation),\n'
            '        "App installed <7d": activation["app_installed_at"].notna().sum(),\n'
            '        "First successful connection": activation["first_successful_connection_at"].notna().sum(),\n'
            '        "3+ successful sessions": activation["successful_sessions_7d"].ge(3).sum(),\n'
            '        "2+ active days": activation["active_days_7d"].ge(2).sum(),\n'
            '        "30+ protected minutes": activation["protected_minutes_7d"].ge(30).sum(),\n'
            '        "Activated <7d": activation["activated_7d"].sum(),\n'
            "    },\n"
            '    name="users",\n'
            ").to_frame()\n"
            'funnel["share_of_eligible"] = funnel["users"] / len(activation)\n'
            "funnel"
        ),
        nbf.v4.new_code_cell(
            'ax = funnel["share_of_eligible"].sort_values().plot.barh(figsize=(8, 5), color="#2563EB")\n'
            'ax.set(title="VPN 7-day activation funnel", xlabel="Share of eligible users", ylabel="")\n'
            'ax.xaxis.set_major_formatter(lambda value, _: f"{value:.0%}")\n'
            "plt.tight_layout();"
        ),
        nbf.v4.new_code_cell(
            "experiment = (\n"
            '    activation.dropna(subset=["experiment_variant"])\n'
            '    .groupby("experiment_variant")\n'
            "    .agg(\n"
            '        users=("user_id", "size"),\n'
            '        activation_rate=("activated_7d", "mean"),\n'
            '        mean_failure_rate=("failure_rate_7d", "mean"),\n'
            '        median_user_p95_ms=("p95_connection_time_ms", "median"),\n'
            "    )\n"
            ")\n"
            "experiment"
        ),
        nbf.v4.new_code_cell(
            "segments = (\n"
            '    activation.groupby("signup_platform")\n'
            "    .agg(\n"
            '        users=("user_id", "size"),\n'
            '        activation_rate=("activated_7d", "mean"),\n'
            '        paid_conversion=("converted_at", lambda values: values.notna().mean()),\n'
            "    )\n"
            '    .sort_values("activation_rate", ascending=False)\n'
            ")\n"
            "segments"
        ),
        nbf.v4.new_markdown_cell(
            "## Takeaways\n\n"
            f"1. Synthetic baseline activation — **{_rate_text(activation_rate)}**.\n"
            f"2. Treatment выше control на **{lift_pp:+.1f} п.п.**; перед решением нужны SRM, "
            "confidence interval и проверка connection-quality guardrails.\n"
            f"3. Activated users конвертируются в оплату чаще ({_rate_text(activated_conversion)} "
            f"против {_rate_text(nonactivated_conversion)}), но это не доказывает причинность.\n"
            "4. Следующий шаг — retention cohorts и server-level unit economics, затем DataLens."
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

        html_exporter = HTMLExporter(template_name="lab")
        html_body, _ = html_exporter.from_notebook_node(notebook)
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
