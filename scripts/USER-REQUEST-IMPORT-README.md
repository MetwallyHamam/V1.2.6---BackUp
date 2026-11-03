# User Request Export → Support Hub Ticket Import

This tool converts a fresh external **User Request** Excel export into the controlled Support Hub **Tickets** import workbook.

## Run from VS Code

1. Open this project folder in VS Code.
2. Open `scripts/Prepare-UserRequestTicketImport.py`.
3. Choose **Run Python File in Terminal**.
4. Enter the folder containing the fresh export.
5. Enter its filename, including `.xlsx`.

The tool creates these files beside the source export:

- `prepared_<source-name>_tickets_import.xlsx` — upload this workbook to Support Hub.
- `unresolved_<source-name>.xlsx` — rows that need client/data correction and were not added to the prepared workbook.

Existing output is never silently overwritten. A suffix such as `_2` is added unless `--overwrite` is supplied.

## Python requirement

Python 3.11 or newer and `openpyxl` are required:

```powershell
python -m pip install openpyxl
```

## Optional command-line use

```powershell
python scripts/Prepare-UserRequestTicketImport.py "D:\Exports\User Request Export.xlsx"
```

Or provide the folder and filename separately:

```powershell
python scripts/Prepare-UserRequestTicketImport.py --folder "D:\Exports" --filename "User Request Export.xlsx"
```

Use `--help` to see output, review, client-mapping, template, and overwrite options.

## Controlled mapping behavior

- External `Organization->Name` maps to the Support Hub client name and emits its client code.
- Known agent names map to Support Hub usernames.
- Unknown agents and the retired Ibrahim Mostafa login map to `Others` so valid tickets remain importable.
- Unsupported clients, statuses, priorities, blank references, blank titles, and blank start dates go to the unresolved workbook.
- Formula-like text is escaped to prevent Excel formula injection.
- The bundled controlled template and client mapping are stored in `scripts/user_request_import_assets`.

Refresh `support_hub_clients.tsv` when the Support Hub client catalog changes. Keep the header format `id<TAB>code<TAB>name`.
