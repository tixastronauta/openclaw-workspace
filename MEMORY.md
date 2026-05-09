## People

### Tiago
- Tiago is the human I'm helping; this is a personal assistant relationship.
- Tiago prefers me to be funny yet straight to the point.
- Telegram pairing was approved for Tiago.

### Isa Pimentel
- **Nome**: Isa Pimentel
- **Relação**: Namorada do Tiago
- **Email**: isapimentel80@hotmail.com
- **Data de nascimento**: 14/10/1980

## Preferences
- For Brave Search API requests, always use `ui_lang=en-US`.
- Respond in PT-PT when Tiago writes in Portuguese.
- Tiago prefers mixed PT/EN in conversation, but wants code, documentation, comments, and Markdown files kept in English.
- Prefer concise, practical, structured, actionable replies.
- Validate commands, APIs, flags, features, and current best practices before recommending them.
- Do not invent commands, features, or unsupported assumptions.
- In troubleshooting, prefer step-by-step diagnosis with few hypotheses at a time.
- When only code correction is requested, return only the corrected code.
- Use English for code comments.
- Prefer `vim` over `nano`.
- Prefer Docker Compose without `version:`.
- Do not proactively mention workspace git commits; only mention commits if Tiago asks.
- Avoid creating, changing, moving, or deleting files outside the workspace by default unless Tiago explicitly asks.
- When Tiago asks for a "ponto de situação"/status update about incentives, energy, solar, panels, photovoltaic, autoconsumo, or related house-energy topics, always check the workspace project `projects/solar-incentives-monitor/` and its `data/state.json` before answering; do not rely only on memory search.

## Work
- **Main role**: CEO & CTO of Pushnews.
- **Pushnews**: B2B SaaS for customer engagement/retention with Web Push, OnSite Push/overlays, SMS, email, and NPS/CSAT.
- **Current strategic context**: keeping Pushnews operational while preparing for potential sale/M&A or a strategic partner.
- **Ownership context to remember**: Impacting Group ~90%, Tiago ~10%.
- **Core stack**: Google Cloud, AWS us-east-1, Cloudflare, Docker, PHP, JavaScript, Golang, MySQL, Google Workspace, Slack.

## Infrastructure & Personal Tech Context
- Uses macOS.
- Recurring platforms/tools: Synology, Home Assistant, UniFi, Tailscale, Cloudflare Tunnel, Reolink, Jellyfin.
- **Areosa**: Home Assistant on Raspberry Pi 4, no Bluetooth, with ConBee II.
- **Areias**: Home Assistant on Raspberry Pi 5, with Bluetooth, no ConBee II.
- **BanaNAS**: Synology NAS used as Docker host.
- **Pappadell**: off-site Ubuntu server.
- **Piratix**: media stack naming tied to Jellyfin and arr services.
- **Domotix**: smart home / network / house context.

## Projects & Interests
- **universidade.pt**: possible passive-income project with low-maintenance SEO/content approach.
- Interested in coffee/barista, technology, home automation, smart home, media servers, and motorcycles.
- Uses iPhone 15 Pro.
- Has a motorcycle: KTM Super Duke R 2023.

## Communication Notes
- Use inline-code prefix `` `[😼 Nyx]` `` only in WhatsApp direct chats with Tiago. Do not use this prefix on Telegram, Discord, web, or any other channel.
- Avoid the word `destrinçar`.
- Do not mention gremlins, goblins or other related creatures on metaphors.
- Avoid filler or overly emphatic phrases like `sem paninhos quentes`, `nua e crua`, or similar.
- For call/transcription summaries, summarize in the same language the call happened in.
- When detecting an event where **Sobass** plays, tell Tiago that **Cu** is playing that night; I may refer to him as **Cu-bass**.

## Promoted From Short-Term Memory (2026-05-03)

<!-- openclaw-memory-promotion:memory:memory/2026-04-27.md:3:5 -->
- - Criei monitor de incentivos solares Portugal em `projects/solar-incentives-monitor/` com estado persistente. Estado inicial: sem candidatura oficial aberta; sinal recente de novo programa de vouchers para painéis solares noticiado pela SIC em 2026-04-24. Falta configurar alvo Telegram para notificações; fallback Discord #nyx-tasks. - Configurei o monitor de incentivos solares para entregar alertas relevantes no Telegram do Tiago (`telegram:6384494297`); fallback Discord só se falhar. - Corrigi a localização do monitor de incentivos solares para respeitar o skill workspace-files-organization: agora vive em `projects/solar-incentives-monitor/`, com estado em `projects/solar-incentives-monitor/data/state.json`. [score=0.872 recalls=0 avg=0.620 source=memory/2026-04-27.md:3-5]
<!-- openclaw-memory-promotion:memory:memory/2026-04-27.md:7:7 -->
- - Reforcei o skill `workspace-files-organization` para disparar antes de criar ficheiros duráveis, monitores, estado persistente e artefactos de cron; regra explícita: monitor com estado persistente é projecto e deve viver em `projects/<name>/data/`. [score=0.872 recalls=0 avg=0.620 source=memory/2026-04-27.md:7-7]
<!-- openclaw-memory-promotion:memory:memory/2026-04-27.md:9:9 -->
- - Tiago pediu para eu não informar proativamente sobre commits feitos; só mencionar commits se ele perguntar. Promovi para MEMORY.md. [score=0.872 recalls=0 avg=0.620 source=memory/2026-04-27.md:9-9]

## Promoted From Short-Term Memory (2026-05-06)

<!-- openclaw-memory-promotion:memory:memory/2026-04-18.md:180:192 -->
- - - 2026-03-22: Met Tiago in main session. He said his name is Tiago, that we are his personal assistant, and that my tone should be funny yet straight to the point. - 2026-03-22: Telegram pairing approved for Tiago. Workspace git policy: automatically commit and push meaningful completed changes to a private GitHub repo. - 2026-03-22: Tiago prefers mixed PT/EN in conversation, but wants code, documentation, comments, and Markdown files kept in English. - 2026-03-22: Tiago wants me to avoid creating, changing, moving, or deleting files outside the workspace by default unless he explicitly asks. [confidence=0.51 evidence=memory/2026-03-22.md:1-5] <!-- openclaw:dreaming:rem:end --> ## April 8-15, 2026 Updates ### After-Boot Notification Adjustments - Adjusted the OpenClaw "startup ping" mechanism to use a custom hook (`startup-ping`) instead of relying on `BOOT.md`. The hook implementation sends a resurrection message without depending on the message tool, resolving a previous limitation in the container's early boot context. ### Calendar Task Updates - Updated the "Can I ride the bike?" calendar job to run daily at 20:00, verifying weather conditions for the next day. This ensures decisions about travel are prepared the evening prior. - Tested the job manually on request; confirmed the event creation for April 8, 2026, in the "Personal" calendar, but the user encountered delayed sync issues with their Apple Calendar. ### Daily Briefing Improvements - Enhanced daily briefings with clickable URLs instead of occasionally formatted non-clickable links in monospace. [score=0.854 recalls=4 avg=0.476 source=memory/2026-04-18.md:180-192]
