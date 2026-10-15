import json
from datetime import date

import create_experiment_notebook
import create_retention_notebook
import create_starter_notebook
import nbformat
import pytest
from nbclient import NotebookClient

from vpn_analytics.generator import generate_rows, write_rows
from vpn_analytics.settings import GeneratorSettings


@pytest.fixture(scope="module")
def notebook_data(tmp_path_factory):
    directory = tmp_path_factory.mktemp("custom-input")
    settings = GeneratorSettings(20260830, date(2026, 1, 1), 181, 30, 120)
    counts = write_rows(generate_rows(settings), directory)
    (directory / "manifest.json").write_text(json.dumps({"counts": counts}), encoding="utf-8")
    return directory


@pytest.mark.parametrize("builder", [create_starter_notebook, create_experiment_notebook,
                                    create_retention_notebook])
def test_notebook_executes_with_custom_input_and_output(notebook_data, tmp_path, builder):
    output = tmp_path / "custom-output"
    output.mkdir()
    notebook = builder.build_notebook(notebook_data, output)
    notebook.cells.append(nbformat.v4.new_code_cell(
        f"assert DATA_DIR == Path({str(notebook_data)!r}).resolve()"
    ))
    executed = NotebookClient(
        notebook, kernel_name="python3", timeout=120,
        resources={"metadata": {"path": str(output)}},
    ).execute()
    assert not any(
        item.output_type == "error" for cell in executed.cells if cell.cell_type == "code"
        for item in cell.outputs
    )


def test_experiment_notebook_handles_tiny_groups(monkeypatch, tmp_path):
    records = [
        {"onboarding_variant": variant, "activated_7d": True}
        for variant in ("control", "treatment")
    ]
    monkeypatch.setattr(create_experiment_notebook, "activation_experiment_records", lambda _: records)
    notebook = create_experiment_notebook.build_notebook(tmp_path, tmp_path)
    assert "не оценивается" in notebook.cells[1].source
    chart = next(cell.source for cell in notebook.cells
                 if cell.cell_type == "code" and "plt.subplots" in cell.source)
    import matplotlib.pyplot as plt
    import pandas as pd

    from vpn_analytics.metrics import activation_experiment_statistics

    scope = {
        "plt": plt, "pd": pd, "result": activation_experiment_statistics(records),
        "balance": pd.DataFrame({"onboarding_variant": ["control", "treatment"],
                                 "activation_rate": [1, 1]}),
        "COLORS": {"control": "blue", "treatment": "green"},
    }
    exec(chart, scope)  # noqa: S102 -- Execute a trusted, locally generated notebook cell.
    plt.close("all")
