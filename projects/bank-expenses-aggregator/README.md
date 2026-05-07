# Bank Expenses Aggregator

Started: 2026-05-07

Aggregates bank expenses from a specific Google Drive folder into a Google Sheet.

Current production flow:

- Discover source files in the Drive folder.
- Parse credit-card statement PDFs named `YYYYMM-ExtratoCartao-<Bank>.pdf`.
- Parse current-account movement CSVs named `YYYYMM-Movimentos-<Bank>.csv`.
- Keep debit/expense rows only, with `Valor` always positive.
- Apply user-maintained exclusion rules from the Sheet tab `Regras Exclusao` (for example card payments from current accounts).
- Apply user-maintained categorisation rules from the Sheet tab `Regras Catalogacao`.
- Overwrite the Sheet tab `Movimentos` with all processed months.

Main scripts:

```bash
python3 projects/bank-expenses-aggregator/process_expenses.py
python3 projects/bank-expenses-aggregator/import_card_statement_emails.py
```

`import_card_statement_emails.py` reads the `Email Import Config` Sheet tab, searches Gmail for monthly card statement emails, imports available PDF attachments into the Drive source folder, and reports banks that require manual download. By default it targets the previous calendar month; override with `--yyyymm YYYYMM` if needed.

Default Drive folder and Sheet IDs are defined in the scripts, with CLI flags available for overrides.

Supported source formats at the moment:

- Credit-card PDFs: ActivoBank, CGD, Unibanco, Universo
- Current-account CSVs: ActivoBank, CGD
