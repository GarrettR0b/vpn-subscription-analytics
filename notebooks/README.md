# Notebooks

`01_activation_starter.ipynb` is generated from validated CSV files and executed top-to-bottom.
`01_activation_starter.html` is the portable offline rendering for reviewers without Jupyter.

Rebuild it after regenerating data:

```powershell
.\.venv\Scripts\python.exe scripts\create_starter_notebook.py
```

The notebook is a reproducible analytical companion. Production-facing metrics should be read
from PostgreSQL marts rather than reimplemented ad hoc.
