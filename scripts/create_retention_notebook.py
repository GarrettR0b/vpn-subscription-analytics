from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import nbformat as nbf
import pandas as pd

from vpn_analytics.metrics import subscriber_retention_records


def _arguments() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Create the retention cohort notebook.")
    parser.add_argument("--input-dir", type=Path, default=root / "data" / "generated")
    parser.add_argument(
        "--output", type=Path, default=root / "notebooks" / "03_retention_cohorts.ipynb"
    )
    parser.add_argument(
        "--html-output",
        type=Path,
        default=root / "notebooks" / "03_retention_cohorts.html",
    )
    parser.add_argument("--no-execute", action="store_true")
    return parser.parse_args()


def _percent(value: float) -> str:
    return f"{value:.1%}".replace(".", ",")


def build_notebook(input_dir: Path, output_dir: Path) -> nbf.NotebookNode:
    data_path = Path(os.path.relpath(input_dir.resolve(), output_dir.resolve())).as_posix()
    retention = pd.DataFrame(subscriber_retention_records(input_dir))
    overall = retention.groupby("month_number").agg(
        eligible=("subscription_id", "size"),
        returned=("retained", "sum"),
        rate=("retained", "mean"),
    )
    m1 = retention[retention["month_number"].eq(1)]

    m1_rate = overall.loc[1, "rate"]
    m2_rate = overall.loc[2, "rate"]
    m3_rate = overall.loc[3, "rate"]
    activated_rate = m1.loc[m1["activated_7d"], "retained"].mean()
    not_activated_rate = m1.loc[~m1["activated_7d"], "retained"].mean()
    pro_rate = m1.loc[m1["plan"].eq("pro"), "retained"].mean()
    basic_rate = m1.loc[m1["plan"].eq("basic"), "retained"].mean()
    telegram_rate = m1.loc[m1["sales_channel"].eq("telegram_bot"), "retained"].mean()
    website_rate = m1.loc[m1["sales_channel"].eq("website"), "retained"].mean()

    notebook = nbf.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
    }
    notebook["cells"] = [
        nbf.v4.new_markdown_cell(
            "# Retention и cohort-анализ VPN через HAPP\n\n"
            "Анализ возврата новых платящих подписок к использованию прокси-сервиса после "
            "покупки. Часть показательного кейса на основе реального проекта автора. "
            "Для соблюдения конфиденциальности данные и численные показатели публичной "
            "версии воссозданы синтетически."
        ),
        nbf.v4.new_markdown_cell(
            "## tl;dr\n\n"
            f"- Usage retention составляет **{_percent(m1_rate)} в M1**, "
            f"**{_percent(m2_rate)} в M2** и **{_percent(m3_rate)} в M3**. "
            "Знаменатели различаются из-за зрелости когорт.\n"
            f"- Самый большой наблюдаемый M1-разрыв связан с 7-day activation: "
            f"**{_percent(activated_rate)} против {_percent(not_activated_rate)}** "
            f"(**{(activated_rate - not_activated_rate) * 100:+.1f} п.п.**).\n"
            f"- Pro показывает **{_percent(pro_rate)}** против **{_percent(basic_rate)}** у Basic; "
            f"Telegram-бот - **{_percent(telegram_rate)}** против **{_percent(website_rate)}** "
            "у сайта. Это описательные различия, а не причинные эффекты.\n"
            "- Следующая проверка для реального кейса: динамика одних и тех же зрелых когорт "
            "и гипотеза связи раннего онбординга с удержанием."
        ),
        nbf.v4.new_markdown_cell(
            "## Context & Methods\n\n"
            "**Вопрос:** где сервису сфокусировать работу над удержанием платящих подписчиков?\n\n"
            "Когорта - eligible-подписки по месяцу начала подписки. `M0` - месяц покупки и "
            "базовый уровень 100%. В `M1+` подписка считается вернувшейся, если в полном "
            "календарном UTC-месяце была хотя бы одна успешная прокси-сессия. Это usage "
            "retention, а не непрерывное survival-удержание: пользователь может вернуться "
            "после неактивного месяца. Незрелые периоды не заполняются нулями.\n\n"
            "Источник: `data/generated/*.csv`; независимый Python-расчёт повторяет логику "
            "`analytics.mart_subscriber_retention`. Общий `engagement_score` генератора "
            "влияет на раннюю активацию, длительность подписки и последующее использование. "
            "Связь этих показателей частично заложена в модель; различия каналов и тарифов "
            "также зависят от настроек симуляции."
        ),
        nbf.v4.new_markdown_cell(
            "### Key Assumptions\n\n"
            "- Данные полностью синтетические и показывают аналитический подход, а не реальные "
            "результаты компании.\n"
            "- Сегменты сравниваются описательно; самоотбор по тарифу, каналу и факту активации "
            "не позволяет делать причинные выводы.\n"
            "- Ранние когорты малы, а новые ещё не достигли M2–M3; вместе с rate всегда "
            "показывается размер наблюдаемой группы."
        ),
        nbf.v4.new_code_cell(
            """from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter

from vpn_analytics.metrics import subscriber_retention_records

DATA_DIR = Path(__DATA_PATH__).resolve()
plt.style.use("seaborn-v0_8-whitegrid")
COLORS = {"primary": "#2563EB", "secondary": "#94A3B8", "text": "#334155"}
MONTHS_RU = {
    1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
    7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек",
}""".replace("__DATA_PATH__", repr(data_path))
        ),
        nbf.v4.new_markdown_cell("## Data\n\n### 1. Load and validate cohort rows"),
        nbf.v4.new_code_cell(
            """retention = pd.DataFrame(subscriber_retention_records(DATA_DIR))
retention["cohort_month"] = pd.to_datetime(retention["cohort_month"])
retention["activity_month"] = pd.to_datetime(retention["activity_month"])

assert not retention.empty
assert retention.loc[retention["month_number"].eq(0), "retained"].all()
assert retention.groupby(["subscription_id", "month_number"]).size().eq(1).all()

retention.head()"""
        ),
        nbf.v4.new_markdown_cell("## Results\n\n### 2. Weighted retention by cohort age"),
        nbf.v4.new_code_cell(
            """overall = (
    retention.groupby("month_number", as_index=False)
    .agg(
        eligible_subscriptions=("subscription_id", "size"),
        retained_subscriptions=("retained", "sum"),
        retention_rate=("retained", "mean"),
    )
)
overall_display = overall.assign(
    period=overall["month_number"].map(lambda value: f"M{value}"),
    retention=overall["retention_rate"].map(lambda value: f"{value:.1%}"),
)[["period", "eligible_subscriptions", "retained_subscriptions", "retention"]]
overall_display"""
        ),
        nbf.v4.new_code_cell(
            """age_curve = overall[overall["month_number"].gt(0)]
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.plot(
    age_curve["month_number"], age_curve["retention_rate"],
    color=COLORS["primary"], marker="o", linewidth=2.2,
)
for row in age_curve.itertuples():
    ax.annotate(
        f"{row.retention_rate:.1%} · n={row.eligible_subscriptions}",
        (row.month_number, row.retention_rate), xytext=(0, 10),
        textcoords="offset points", ha="center", color=COLORS["text"],
    )
ax.set(
    title="Usage retention по возрасту когорты",
    xlabel="Полных календарных месяцев после покупки",
    ylabel="Доля исходной когорты",
    xticks=age_curve["month_number"],
    ylim=(0, 0.65),
)
ax.set_xticklabels([f"M{value}" for value in age_curve["month_number"]])
ax.yaxis.set_major_formatter(PercentFormatter(1))
plt.tight_layout();"""
        ),
        nbf.v4.new_markdown_cell(
            f"M3-бенчмарк равен **{_percent(m3_rate)}**, но его знаменатель меньше, чем у M1: "
            "поздние когорты ещё не успели созреть. Поэтому график показывает проблемный "
            "период жизненного цикла, а не точный последовательный отток одной и той же группы."
        ),
        nbf.v4.new_markdown_cell("### 3. Cohort heatmap"),
        nbf.v4.new_code_cell(
            """cohorts = (
    retention.groupby(["cohort_month", "month_number"], as_index=False)
    .agg(
        eligible_subscriptions=("subscription_id", "size"),
        retained_subscriptions=("retained", "sum"),
        retention_rate=("retained", "mean"),
    )
)
cohort_matrix = (
    cohorts.pivot(index="cohort_month", columns="month_number", values="retention_rate")
    .sort_index()
)
cohort_sizes = retention.loc[retention["month_number"].eq(0)].groupby("cohort_month").size()

cmap = plt.colormaps["Blues"].copy()
cmap.set_bad("#F8FAFC")
fig, ax = plt.subplots(figsize=(10, 5.2))
image = ax.imshow(cohort_matrix.to_numpy(), aspect="auto", cmap=cmap, vmin=0, vmax=1)
ax.set_xticks(range(len(cohort_matrix.columns)), [f"M{value}" for value in cohort_matrix.columns])
ax.set_yticks(
    range(len(cohort_matrix.index)),
    [
        f"{MONTHS_RU[value.month]} {value.year} · n={cohort_sizes.loc[value]}"
        for value in cohort_matrix.index
    ],
)
ax.set(title="Usage retention по месяцу покупки", xlabel="Возраст когорты", ylabel="Когорта")
for row_index in range(cohort_matrix.shape[0]):
    for column_index in range(cohort_matrix.shape[1]):
        value = cohort_matrix.iloc[row_index, column_index]
        label = "-" if pd.isna(value) else f"{value:.0%}"
        color = "#94A3B8" if pd.isna(value) else ("white" if value >= 0.55 else COLORS["text"])
        ax.text(column_index, row_index, label, ha="center", va="center", color=color)
colorbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.03)
colorbar.ax.yaxis.set_major_formatter(PercentFormatter(1))
colorbar.set_label("Retention")
plt.tight_layout();"""
        ),
        nbf.v4.new_markdown_cell(
            "Крупные мартовская и апрельская когорты показывают M1 около 54–56%; ранние "
            "январь и февраль сильнее колеблются из-за размеров 15 и 13 подписок. Пустые клетки "
            "- незрелые периоды, а не нулевой retention."
        ),
        nbf.v4.new_markdown_cell("### 4. M1 retention by segment"),
        nbf.v4.new_code_cell(
            """m1 = retention[retention["month_number"].eq(1)].copy()

def segment_summary(column, dimension, labels):
    result = (
        m1.groupby(column, as_index=False)
        .agg(
            eligible_subscriptions=("subscription_id", "size"),
            retained_subscriptions=("retained", "sum"),
            retention_rate=("retained", "mean"),
        )
    )
    return result.assign(
        dimension=dimension,
        segment=result[column].map(labels),
    )[["dimension", "segment", "eligible_subscriptions", "retained_subscriptions", "retention_rate"]]

segments = pd.concat(
    [
        segment_summary(
            "activated_7d", "7-day activation",
            {False: "Не активировались", True: "Активировались"},
        ),
        segment_summary("plan", "Тариф", {"basic": "Basic", "pro": "Pro"}),
        segment_summary(
            "sales_channel", "Канал продажи",
            {"website": "Сайт", "telegram_bot": "Telegram-бот"},
        ),
    ],
    ignore_index=True,
)
segment_display = segments.assign(
    retention=segments["retention_rate"].map(lambda value: f"{value:.1%}")
).drop(columns="retention_rate")
segment_display"""
        ),
        nbf.v4.new_code_cell(
            """fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), sharex=True)
for ax, dimension in zip(axes, ["7-day activation", "Тариф", "Канал продажи"]):
    rows = segments[segments["dimension"].eq(dimension)].sort_values("retention_rate")
    colors = [COLORS["secondary"], COLORS["primary"]]
    bars = ax.barh(rows["segment"], rows["retention_rate"], color=colors)
    for bar, row in zip(bars, rows.itertuples()):
        ax.text(
            row.retention_rate + 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{row.retention_rate:.1%} · n={row.eligible_subscriptions}",
            va="center", color=COLORS["text"],
        )
    ax.set_title(dimension)
    ax.set_xlim(0, 0.82)
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.set_xlabel("M1 usage retention")
fig.suptitle("M1 retention по ключевым сегментам", y=1.03, fontsize=14)
plt.tight_layout();"""
        ),
        nbf.v4.new_markdown_cell(
            "## Takeaways\n\n"
            f"1. **M2 и M3 имеют разный состав зрелых когорт:** агрегаты равны "
            f"**{_percent(m2_rate)}** и **{_percent(m3_rate)}**. По их разности нельзя "
            "определить главный момент оттока. Сначала нужно сравнить одни и те же когорты "
            "по возрастам и проверить причины прекращения использования.\n"
            f"2. **Связь активации с retention частично задана генератором:** M1 равен "
            f"**{_percent(activated_rate)}** у активировавшихся и "
            f"**{_percent(not_activated_rate)}** у остальных. Это демонстрация сегментации; "
            "полезность HAPP-инструкций для удержания требует проверки на реальных данных.\n"
            "3. **Различия Pro/Basic и каналов зависят от симуляции.** Они не доказывают, "
            "что повышение цены или перевод пользователей в бот увеличит retention.\n"
            "4. **Для реального исследования:** измерить причины отмены и неуспешного "
            "продления, затем спланировать проверку гипотез. Незрелые M2–M3 не заменять нулями."
        ),
    ]
    return notebook


def main() -> int:
    args = _arguments()
    notebook = build_notebook(args.input_dir, args.output.parent)
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
        args.html_output.parent.mkdir(parents=True, exist_ok=True)
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
