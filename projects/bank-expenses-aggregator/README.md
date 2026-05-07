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

Main script:

```bash
python3 projects/bank-expenses-aggregator/process_expenses.py
```

Default Drive folder and Sheet IDs are defined in the script, with CLI flags available for overrides.

Supported source formats at the moment:

- Credit-card PDFs: ActivoBank, CGD, Unibanco, Universo
- Current-account CSVs: ActivoBank, CGD
