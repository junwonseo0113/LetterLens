# LetterLens live demo script

Persona: **Kim Soon-ja, 74, Flushing, Queens.** Target: under 3 minutes for
the core walkthrough, leaving room for Q&A.

## Before you go on stage

**Setup (do this ~10 min before your slot):**

```bash
# Terminal 1 -- backend
cd LetterLens
python3 demo/seed.py          # wipes demo DB, fresh start
MOCK_MODE=true uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 -- frontend
cd LetterLens/frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

- Phone demo: find your Mac's LAN IP (`ifconfig | grep "inet "`), set
  `frontend/.env.local` to `VITE_API_BASE_URL=http://<that-ip>:8000`,
  restart the frontend, open `http://<that-ip>:5173` in **iPhone Safari**
  (not Chrome -- Add to Home Screen only works in Safari).
- **Risk**: some venue/campus Wi-Fi has client isolation and will block
  your phone from reaching your laptop even on the same network. Test
  this *before* you're on stage. If it fails, fall back to presenting
  from the laptop browser at `localhost:5173`, or use the scripted
  transcript below.
- **Fallback if anything breaks live**: `python3 demo/run_demo.py` runs
  the entire FIND/KEEP/PROTECT flow against the real backend in under a
  second and prints a full transcript. Have a terminal window ready as a
  safety net.

## The pitch frame (say this before you start clicking)

> "Kim Soon-ja is 74, lives in Flushing, speaks Korean. She gets an
> English letter from Social Security and has no idea what it means or
> whether she's owed money. LetterLens photographs the letter, explains
> it in her language, and automatically checks her against three
> programs she's probably eligible for but never applied to."

Mention early: **"Every number here is checked against SSA/NY State
limits by a deterministic Python rules engine — the AI never decides
eligibility, it only explains."** This is your strongest differentiator
and worth saying before anyone asks.

## Walkthrough

**1. Language picker** — tap 한국어. *"Five languages, big buttons,
built for someone who doesn't read small English text comfortably."*

**2. Upload the SSA letter** (`ssa_benefit_letter_sample.jpg`) — tap 📷,
pick the file. *"OCI Document Understanding reads the letter, OCI
Generative AI classifies it and extracts the numbers — gross benefit,
Part B deduction, net payment — then explains it in her language."*
Point out: numbers stay in English/Arabic numerals even in the
translated text, never retranslated — that's deliberate, a mistranslated
dollar amount is a real-world harm.

**3. Upload the bank statement** — same flow. *"$40,000 in savings. On
paper that sounds disqualifying. It isn't — New York doesn't count
savings for the Medicare Savings Program. The app says that explicitly,
not just 'you may qualify.'"*

**4. Upload the SNAP renewal notice** (`hra_snap_renewal_notice_sample.jpg`)
— *"This creates a reminder with a real countdown, and a document
checklist. Watch — "* go back to Home, point at the reminder line: it
already shows **1/3 documents ready**, because it cross-checked the SSA
letter she already uploaded against "proof of income." *"Access NYC
tells you what documents you need. We check whether you actually have
them yet, and flag exactly what's missing."* This is your second
differentiator — say it clearly.

**5. Toggle "I'm enrolled in QMB"** on the Home screen. *"In the real
product this would come from her Medicaid card or a QMB notice — for
the demo, imagine she enrolled last month after an earlier FIND pass."*

**6. Upload the medical bill** (`medical_bill_sample.jpg`) — tap "Check
this bill." *"A $20 copay for a Medicare-covered visit. Federal law
says QMB members can't be billed for that. The app flags it and drafts
a dispute letter — in English for the provider, and translated for her
to review side by side, so she knows exactly what she's sending."*

**7. "See benefits found"** — walk through the three cards: **QMB
likely** ($202.90/mo, $2,434.80/yr), **Extra Help** (automatic via QMB —
call out the myth-busting line: *"you can still get this even if your
income looks too high on its own"*), **SNAP likely**. Tap "이유 / 사용된
숫자" on one card to expand it. *"Every single result shows the exact
numbers used, the rule applied, a confidence label, and this line —"*
point at the disclaimer — *"'Final decision is made by NY State / HRA /
SSA, not this app.' The AI explains. It never decides."*

**8. Application pack** — checklist with checkmarks, numbers table in
English next to her language.

**9. Caseworker card** — tap Print. *"A bilingual one-pager she can
hand a caseworker or bring to an interview."*

**10. (If time) Add to Home Screen** on the phone — *"It installs like a
native app. No App Store review, works the moment she gets a letter."*

## If a judge asks...

- **"What happens if OCI Document Understanding is down?"** → Point at
  `MOCK_MODE`. Every OCI call (OCR, classify, extract, explain, draft,
  translate) has an offline deterministic fallback, same API surface.
  The demo never depends on live network access to Oracle Cloud.
- **"How do you stop the AI from hallucinating a wrong dollar amount?"**
  → `app/number_guard.py` — every GenAI explanation is checked against
  its source facts; an invented number raises an error before it ever
  reaches the user.
- **"What's still missing?"** → Be honest: no auth/identity verification
  yet (`user_id` is a free string), no document type captures age or
  current QMB enrollment (hence the manual toggle), SNAP's asset-test
  nuance for non-elderly households is simplified. All flagged inline in
  the code, not hidden.

## Time budget

Steps 1–9 above run in roughly 90 seconds of actual clicking if you
don't pause to narrate every line — practice it once end to end so the
live version isn't the first time you've done it back to back.
