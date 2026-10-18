# LetterLens live demo script

Persona: **Chen Yu-lan (陈玉兰), 74, Flushing, Queens, Mandarin speaker.** Target: under 3 minutes for
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
  the entire sign-in/FIND/APPLY/KEEP/PROTECT flow against the real backend in under a
  second and prints a full transcript. Have a terminal window ready as a
  safety net.

## The pitch frame (say this before you start clicking)

> "Chen Yu-lan is 74, lives in Flushing, and speaks Mandarin. She gets
> English letters from Social Security and has no idea she's leaving
> about $2,400 a year on the table. New York has roughly 877,000 people
> eligible for SNAP who aren't enrolled, and nationally 6.6 million older
> adults are missing out on Medicare Savings Programs. They aren't
> ineligible. The process is in English, it's confusing, and they assume
> their savings or their home disqualifies them. LetterLens reads her
> letters, tells her in Chinese what she qualifies for, then **fills in
> the application for her. Her only job is to say yes.**"

Mention early: **"Every number here is checked against SSA/NY State
limits by a deterministic Python rules engine. The AI never decides
eligibility; it only explains."**

## Walkthrough

**1. Language picker**: tap 中文 (it's first). *"Five languages, built
Chinese-first for Flushing and Chinatown."*

**2. Sign in**: type any 10-digit number, tap 给我发验证码, type the code
shown in the green box, tap 登录. *"Before she uploads anything personal,
we verify it's her phone. That's how we answer 'why should I trust this
app with my documents?' In production it's a real text message; for the
demo the code is shown on screen."*

**3. Upload the SSA letter** (`ssa_benefit_letter_sample.jpg`): tap 📷.
*"OCI Document Understanding reads it, OCI Generative AI classifies it,
pulls out the numbers and her name and address, and explains it in
Chinese."* The numbers stay exactly as printed. A mistranslated dollar
amount is a real-world harm.

**4. Upload the bank statement**: *"$40,000 in savings. On paper that
sounds disqualifying. It isn't: New York doesn't count savings for the
Medicare Savings Program. The app says so explicitly."*

**5. 查看可领取的福利 (benefits)**: QMB likely ($202.90/mo, $2,434.80/yr),
Extra Help automatic via QMB, SNAP likely. Expand 原因 / 使用的数字 on one
card: *"Every result shows its numbers, the rule applied, and 'Final
decision is made by NY State / HRA / SSA.'"*

**6. Tap 申请 MSP + Extra Help**: this is the moment. Point at the green
box: **"已经根据您的信件自动填好 4 项." Four of nine answers came from her
letters and her sign-in.** The app only asks the five it couldn't find.
- Tap 🎤 按一下，开始说话 and *say* "一九五二年三月五日". It becomes
  1952-03-05. *"She just talks. Mandarin or Cantonese; there's a toggle."*
  (Tap 🔊 to read the question aloud.)
- Type or say the rest: Medicare number `1EG4TE5MK73`, 没有 (not
  married), 一个人, 没有 (no work income).

**7. Review**: *"Every answer, and where it came from: 来自您的社会安全局信件,
from her Social Security letter; 您告诉我们的, she told us."* She can
tap 修改 on anything. Sign with a finger, then tap **是的，帮我提交 (Yes,
send it for me)**. *"The AI does the work. She reviews once and says
yes."*

**8. Status: 社工正在检查 (a caseworker is checking)**. *"She doesn't
have her Medicare card photo yet. Instead of failing, the app routes
her application to a human."*

**9. Caseworker view**: open `/caseworker` in a second tab (laptop).
Type a note like "请拍一下您的医疗保险卡" and tap **Request info**.
Back on her screen, refresh: 社工需要您补充材料 with the note. Tap 补充后
重新提交, add the four photos (any image works in the demo), sign, and
send. **已提交, with a confirmation number and a timeline** (sent → state
review → decision letter within 45 days). Or just tap **Approve & send**
in the caseworker tab for the short version.

Be upfront about the grey "演示" note on that screen: *"No agency
accepts filings from apps today. In production this goes through an
authorized-representative partner, like a community organization."*

**10. (If time) PROTECT**: toggle 我已加入 QMB on Home, upload
`medical_bill_sample.jpg`. The $20 copay is flagged, with a dispute
letter in English and Chinese side by side.

## If a judge asks...

- **"What happens if OCI Document Understanding is down?"** → Point at
  `MOCK_MODE`. Every OCI call (OCR, classify, extract, explain, draft,
  translate) has an offline deterministic fallback, same API surface.
  The demo never depends on live network access to Oracle Cloud.
- **"How do you stop the AI from hallucinating a wrong dollar amount?"**
  → `app/number_guard.py` — every GenAI explanation is checked against
  its source facts; an invented number raises an error before it ever
  reaches the user.
- **"Does it really submit?"** → No, and the app says so on screen. No NY
  State / HRA / SSA API accepts third-party filings. Everything up to the
  send is real: the pre-filled form, the signature, the caseworker
  handoff. The last hop would go through an authorized-representative
  partner.
- **"How do you know it's really her?"** → Phone one-time code before
  any upload. Today the code is shown on screen (no SMS provider wired);
  swapping in a real SMS sender is one function, `app/auth/service.py`
  `send_code()`.
- **"What's still missing?"** → Be honest: SMS delivery for the sign-in
  code, real agency filing, caseworker accounts (one shared key today),
  no letter type captures current QMB enrollment (hence the manual
  toggle; age now comes from the application interview), SNAP's
  asset-test nuance for non-elderly households is simplified. All flagged inline in the code, not hidden.

## Time budget

Steps 1–9 above run in roughly 2 minutes of actual clicking if you
don't pause to narrate every line — practice it once end to end so the
live version isn't the first time you've done it back to back.
