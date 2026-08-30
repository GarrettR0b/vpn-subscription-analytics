from __future__ import annotations

import argparse
import json
from pathlib import Path

import nbformat as nbf
import pandas as pd

from ai_saas_analytics.metrics import activation_records


def _arguments() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Create and execute the activation notebook.")
    parser.add_argument("--input-dir", type=Path, default=project_root / "data" / "generated")
    parser.add_argument(
        "--output", type=Path, default=project_root / "notebooks" / "01_activation_starter.ipynb"
    )
    parser.add_argument("--no-execute", action="store_true")
    return parser.parse_args()


def _rate_text(value: float) -> str:
    return f"{value:.1%}".replace(".", ",")


def build_notebook(input_dir: Path) -> nbf.NotebookNode:
    frame = pd.DataFrame(activation_records(input_dir))
    activation_rate = float(frame["activated_7d"].mean())
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
            "# Диагностика 7-дневной активации AI SaaS\n\n"
            "Воспроизводимый стартовый анализ на полностью синтетических данных. "
            "Единое определение метрики хранится в `docs/metric_dictionary.md`, "
            "а SQL-реализация — в `sql/marts/001_mart_workspace_activation.sql`."
        ),
        nbf.v4.new_markdown_cell(
            "## tl;dr\n\n"
            f"- В выборке **{len(frame):,}** eligible workspaces; 7-дневная активация — "
            f"**{_rate_text(activation_rate)}**.\n"
            f"- В синтетическом эксперименте: control **{_rate_text(control_rate)}**, "
            f"treatment **{_rate_text(treatment_rate)}**, разница **{lift_pp:+.1f} п.п.**\n"
            "- Эти числа демонстрируют аналитический метод и не являются результатами реальной компании."
        ),
        nbf.v4.new_markdown_cell(
            "## Context & Methods\n\n"
            "**Решение:** определить главный провал onboarding funnel и проверить, связан ли guided onboarding "
            "с ростом активации. Единица анализа — workspace.\n\n"
            "**Каноническая активация:** knowledge base подключена, teammate приглашён и не менее трёх "
            "AI-подсказок принято в течение 7 дней; первое принятие происходит после setup milestones.\n\n"
            "Сравнение experiment variants ниже описательное: данные синтетические, а статистический вывод "
            "будет добавлен после проверки SRM и доверительных интервалов."
        ),
        nbf.v4.new_code_cell(
            "import json\n"
            "from pathlib import Path\n\n"
            "import matplotlib.pyplot as plt\n"
            "import pandas as pd\n\n"
            "from ai_saas_analytics.data_quality import validate_dataset\n"
            "from ai_saas_analytics.metrics import activation_records\n\n"
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
            "activation = pd.DataFrame(activation_records(DATA_DIR))\nactivation.head(3)"
        ),
        nbf.v4.new_markdown_cell("## Results"),
        nbf.v4.new_code_cell(
            "funnel = pd.Series(\n"
            "    {\n"
            '        "Eligible workspaces": len(activation),\n'
            '        "KB connected <7d": activation["knowledge_base_connected_at"].notna().sum(),\n'
            '        "Teammate invited <7d": activation["teammate_invited_at"].notna().sum(),\n'
            '        "3+ accepted suggestions <7d": activation["accepted_suggestions_7d"].ge(3).sum(),\n'
            '        "Activated <7d": activation["activated_7d"].sum(),\n'
            "    },\n"
            '    name="workspaces",\n'
            ").to_frame()\n"
            'funnel["share_of_eligible"] = funnel["workspaces"] / len(activation)\n'
            "funnel"
        ),
        nbf.v4.new_code_cell(
            'ax = funnel["share_of_eligible"].sort_values().plot.barh(figsize=(8, 4), color="#3B82F6")\n'
            'ax.set(title="7-day onboarding funnel", xlabel="Share of eligible workspaces", ylabel="")\n'
            'ax.xaxis.set_major_formatter(lambda value, _: f"{value:.0%}")\n'
            "plt.tight_layout();"
        ),
        nbf.v4.new_code_cell(
            "experiment = (\n"
            '    activation.dropna(subset=["experiment_variant"])\n'
            '    .groupby("experiment_variant")["activated_7d"]\n'
            '    .agg(workspaces="size", activated="sum", activation_rate="mean")\n'
            ")\n"
            "experiment"
        ),
        nbf.v4.new_code_cell(
            "segments = (\n"
            '    activation.groupby("acquisition_channel")["activated_7d"]\n'
            '    .agg(workspaces="size", activation_rate="mean")\n'
            '    .sort_values("activation_rate", ascending=False)\n'
            ")\n"
            "segments"
        ),
        nbf.v4.new_markdown_cell(
            "## Takeaways\n\n"
            f"1. Baseline activation равна **{_rate_text(activation_rate)}** — это стартовая точка, а не KPI реальной компании.\n"
            f"2. В сгенерированном сценарии treatment выше control на **{lift_pp:+.1f} п.п.**; "
            "перед продуктовым решением нужны SRM, доверительный интервал и guardrails.\n"
            "3. Следующий аналитический шаг — локализовать выпадение между knowledge-base setup, teammate invite "
            "и первым принятием AI-подсказки, затем перенести проверенную витрину в DataLens."
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

        executed = NotebookClient(
            notebook,
            timeout=180,
            kernel_name="python3",
            resources={"metadata": {"path": str(args.output.parent)}},
        ).execute()
        nbf.write(executed, args.output)
    print(
        json.dumps(
            {"notebook": str(args.output), "executed": not args.no_execute}, ensure_ascii=False
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
