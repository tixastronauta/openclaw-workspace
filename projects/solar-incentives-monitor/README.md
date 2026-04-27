# Solar Incentives Monitor

Started: 2026-04-27

Monitor for Portuguese incentives/candidaturas related to residential solar panels, photovoltaic/autoconsumo, and energy-efficiency support relevant to Tiago's house.

Current scope:
- keep persistent state in `data/state.json`;
- check official sources first: Fundo Ambiental / Agência para o Clima, Portugal.gov.pt, DGEG, ADENE, PRR/Recuperar Portugal, Portugal 2030;
- treat press coverage as a signal only, not final confirmation;
- notify Tiago on Telegram when there is a relevant change.

Alert criteria:
- new official notice;
- candidaturas open or opening date/time announced;
- application form/platform becomes available;
- eligibility, budget, voucher, reimbursement, or deadline details published for residential solar/autoconsumo support.
