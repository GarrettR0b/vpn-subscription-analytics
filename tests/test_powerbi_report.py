import json
import re
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1] / "powerbi/vpn-analytics.Report"


def pages():
    result = {}
    for folder in (REPORT / "definition/pages").iterdir():
        if folder.is_dir():
            page = json.loads((folder / "page.json").read_text(encoding="utf-8"))
            visuals = [
                json.loads(file.read_text(encoding="utf-8"))
                for file in (folder / "visuals").glob("*/visual.json")
            ]
            result[page["displayName"]] = (page, visuals)
    return result


def fields(visual, role):
    projections = visual["visual"].get("query", {}).get("queryState", {}).get(role, {})
    return {
        next(iter(item["field"].values()))["Property"]
        for item in projections.get("projections", [])
    }


def test_business_has_all_seven_kpis():
    _, visuals = pages()["Обзор бизнеса"]
    actual = set().union(*(fields(v, "Data") for v in visuals))
    assert actual == {
        "Revenue",
        "MRR",
        "Ending Subscribers",
        "New Paying Users",
        "Churned Subscribers",
        "Traffic",
        "Latest Connection Failure Rate",
    }


def test_retention_uses_explicit_age_and_observation_counts():
    _, visuals = pages()["Удержание подписчиков"]
    cards = set().union(*(fields(v, "Data") for v in visuals))
    assert "Retention Rate" not in cards
    assert {"M1 Retention", "M3 Retention", "M1 Observed Subscriptions"} <= cards
    curve = next(v for v in visuals if v["visual"]["visualType"] == "lineChart")
    assert fields(curve, "Category") == {"Month Number"}
    assert fields(curve, "Tooltips") == {"Observed Subscriptions", "Retained Subscribers"}


def test_required_filters_and_experiment_uncertainty_are_present():
    report_pages = pages()
    for page_name, expected in [
        ("Активация подписки", "Вариант настройки"),
        ("Удержание подписчиков", "Ранняя активация"),
    ]:
        _, visuals = report_pages[page_name]
        assert expected in set().union(*(fields(v, "Values") for v in visuals))
    _, visuals = report_pages["Проверка новой настройки"]
    cards = set().union(*(fields(v, "Data") for v in visuals))
    assert {
        "Control Sample",
        "Treatment Sample",
        "Lift CI Lower",
        "Lift CI Upper",
        "Activation P Value",
    } <= cards


def test_visuals_have_unique_ids_valid_bounds_and_numeric_literals():
    all_ids = []
    for page, visuals in pages().values():
        for visual in visuals:
            all_ids.append(visual["name"])
            box = visual["position"]
            assert 0 <= box["x"] <= page["width"] - box["width"]
            assert 0 <= box["y"] <= page["height"] - box["height"]
            assert not re.search(r"\"Value\":\s*\"'-?\d+(?:\.\d+)?[DL]'\"", json.dumps(visual))
    assert len(all_ids) == len(set(all_ids))


def test_visible_names_are_russian_and_navigation_targets_exist():
    report_pages = pages()
    page_ids = {page["name"] for page, _ in report_pages.values()}
    for page, visuals in report_pages.values():
        assert re.search("[А-Яа-я]", page["displayName"])
        buttons = [v for v in visuals if v["visual"]["visualType"] == "actionButton"]
        assert len(buttons) == 4
        destinations = set()
        for button in buttons:
            action = button["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
            destinations.add(action["navigationSection"]["expr"]["Literal"]["Value"].strip("'"))
            assert action["type"]["expr"]["Literal"]["Value"] == "'PageNavigation'"
            for toggle in ["fill", "text"]:
                assert any(
                    "selector" not in entry
                    and entry["properties"]
                    .get("show", {})
                    .get("expr", {})
                    .get("Literal", {})
                    .get("Value")
                    == "true"
                    for entry in button["visual"]["objects"][toggle]
                )
        assert destinations == page_ids
        for visual in visuals:
            for role in visual["visual"].get("query", {}).get("queryState", {}).values():
                for projection in role.get("projections", []):
                    assert re.search("[А-Яа-я]", projection["displayName"])


def test_periods_static_conclusions_and_slicer_contrast_are_explicit():
    for name, (_, visuals) in pages().items():
        copy = "\n".join(
            run["value"]
            for visual in visuals
            if visual["visual"]["visualType"] == "textbox"
            for paragraph in visual["visual"]["objects"]["general"][0]["properties"][
                "paragraphs"
            ]
            for run in paragraph["textRuns"]
        )
        assert "Рекомендация:" in copy
        assert "не пересчитывается фильтр" in copy
        if name == "Обзор бизнеса":
            assert "Выручка - выбранный период" in copy
            assert "последний выбранный месяц" in copy
            assert "по умолчанию - июнь" in copy
        for visual in visuals:
            if visual["visual"]["visualType"] == "slicer":
                items = visual["visual"]["objects"]["items"][0]["properties"]
                assert items["fontColor"] != items["background"]
