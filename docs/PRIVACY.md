# LetterLens document & data handling

How a letter photo moves through LetterLens, what is kept, what is
discarded, and the limits of those promises. "Unverified" marks anything
we have not confirmed ourselves; we don't promise zero retention by
others.

## 1. Lifecycle of an uploaded letter

1. **Before upload** the app shows who will process the photo, what will
   be kept, and that the photo is discarded after reading
   (`frontend/src/context/ScanContext.jsx`, also at `/privacy`).
2. **In the browser** the photo is re-encoded to at most 2000 px JPEG
   (`frontend/src/shrinkImage.js`). This keeps it under 1 MB in normal
   cases (see 4) and drops photo metadata such as GPS location. If the
   browser can't do this, the original file is sent.
3. **Reading** — `POST /letters/read` (`app/docs/router.py`):
   - the upload is copied into a buffer LetterLens controls and the
     framework's upload handle is closed immediately (`app/uploads.py`);
   - the photo is sent for OCR, then the text for classification,
     extraction and an explanation (see 3);
   - the photo's file name is sent too; it's used only in demo mode (to
     pick which sample letter to show) and is never stored or logged;
   - **nothing is written to the database** — the result is a *draft*
     returned to the browser, signed so it can't be altered or used by
     another account, valid 30 minutes (`app/docs/drafts.py`);
   - when the request ends — success, failure, or the client
     disconnecting (cancellation) — the buffer is overwritten with zeros
     and the handle is (already) closed.
4. **Checking** — the user sees what was read on "Check what we read",
   can correct the facts, and chooses whether to keep their name and
   address (off by default). The draft lives only in the page's memory —
   not in localStorage, sessionStorage or browser history.
5. **Saving** — `POST /letters/confirm` saves only the confirmed facts the
   app uses (`app/privacy.py` `SAVED_FIELDS`), then updates the
   eligibility profile, reminders and bill check. "Don't save" or leaving
   the page saves nothing.

Document photos added to an application (`POST /applications/{id}/documents/{key}`)
follow the same upload handling, but the photo isn't read or sent
anywhere: only "a photo was provided" is recorded. A provided photo is
**not** a verified document (see 6).

## 2. What is kept

| Kept (until you delete it) | Not kept |
|---|---|
| Confirmed facts per letter type: SSA benefit amounts and effective date; bank ending balance and deposit amounts (descriptions removed); HRA program, deadline and requested documents; medical bill provider, charges and Medicare-claim flag | The photo itself |
| Name and address from an SSA letter **only if you tick the box** (used to fill in your application) | Full OCR text of the letter |
| The explanation shown for the letter (generated without your name/address) and which facts you corrected | Free-text summaries of unrecognized letters |
| Whether the letter was a demo **sample** | Bank deposit descriptions |
| Answers to "More information needed" questions; the eligibility profile built from letters and answers | Unconfirmed drafts (they exist only in your browser tab, and expire after 30 minutes) |
| Reminders created from renewal notices | |
| Applications (answers incl. Medicare number, date of birth, phone; signature image; status) | |
| Your phone number (sign-in), sign-in sessions (30 days), recent sign-in codes (10 minutes) | |

In the browser, localStorage holds: the sign-in token, user id and phone
number; language; text size; whether you dismissed the scan notice.
Signing out removes the sign-in data. The offline app cache (service
worker) stores only the app's own files, never API responses.

## 3. External processors

| Processor | When | What is sent | Retention / logging |
|---|---|---|---|
| **None** | `MOCK_MODE=true` (demo) | Nothing — the photo is never read; canned sample results are returned and labeled "Sample". | — |
| **Oracle Cloud — OCI Document Understanding** (`AnalyzeDocument`, text extraction) | `MOCK_MODE=false` | The photo, inline (base64) in the request. No Object Storage bucket is used. | **Unverified.** Governed by Oracle's terms for the account in use. OCI Audit records API calls (metadata). We have not confirmed whether or how long Oracle retains request content. |
| **Oracle Cloud — OCI Generative AI** (Cohere chat, on-demand) | `MOCK_MODE=false` | The OCR text (classify, extract); the extracted facts **without** name/address (explanations); flagged bill lines (dispute letter). | **Unverified**, as above. Check Oracle's Generative AI data-handling documentation and your contract before using real letters. |
| SMS provider | — | None exists yet; sign-in codes are only shown on screen in `DEMO_MODE`. | — |
| Analytics | — | None. LetterLens has no analytics or tracking. | — |

Region: whatever `OCI_REGION` / the OCI config sets (usually `us-chicago-1`).

## 4. Temporary-file and memory audit

Audited against starlette 1.8.0, FastAPI 0.143.3, python-multipart 0.0.32:

- Starlette stores each uploaded file in a `SpooledTemporaryFile` that
  stays **in memory up to 1 MB**; larger uploads **roll over to an
  anonymous temporary file in the OS temp directory**. On macOS/Linux
  that file has no name (unlinked at creation) but its data is on disk
  until closed, and closing frees the space **without overwriting it**.
- FastAPI closes uploads only after the response is sent. LetterLens
  closes them itself, as soon as it has copied the data, in a `finally`
  block, so success, failure and cancellation all release them
  (`app/uploads.py`; tested in `tests/test_privacy.py`, including a 2 MB
  upload that really is spooled to disk).
- `del` only removes a variable name; it erases nothing. LetterLens
  instead overwrites **its own** buffer with zeros when processing ends.
  Copies it can't reach — the multipart parser's chunks, base64 encoding
  for OCI, the OCI SDK's HTTP buffers, the OCR text inside the reading
  function — are freed by Python's garbage collector at an unspecified
  time and may remain in process memory (or swap) until reused.
- Uploads are capped at 10 MB.

## 5. Logs

LetterLens logs failures as the error **type** and OCI status/code only
(`app/privacy.py` `describe_failure`), never the error message or
traceback, because validation and service errors can repeat a letter's
contents (tested). Uvicorn's access log records the request line
(e.g. `POST /letters/read 200`, `GET /letters/12`) and client IP — no
letter contents. Logs go to the console; LetterLens doesn't ship them
anywhere, but whoever hosts it may collect console output.

## 6. Not verification

Reading a letter is OCR plus AI extraction. It does **not** verify the
user's identity or that a letter or document is genuine, and the app
never calls it verification. An application document is "verified" only
when a caseworker records that they saw the original. Users should keep
their original letters and documents for any agency or counselor that
asks for them.

## 7. Deleting

- **Originals**: nothing to delete — they are never saved (see 1).
- **Saved information**: "Delete my saved information" on the Privacy
  page (`POST /me/delete-data`, signed-in user only, explicit confirm)
  deletes that user's saved letter facts, eligibility profile, answers,
  reminders, applications (drafts and sent, with signatures), sign-in
  sessions and pending sign-in codes, then signs them out. It never
  touches another user's records (tested).
- **Backups**: LetterLens itself makes no backups, but any copy of the
  database made outside the app (server/disk backups, snapshots, or a
  manual copy such as `letterlens.backup-*.db`) is **not** reached by the
  delete button and keeps the data until that copy is removed. SQLite may
  also leave deleted bytes in free pages of the database file until they
  are reused or the file is `VACUUM`ed.
- Anything already sent to an agency (not possible in this demo) or to
  Oracle (see 3) is outside LetterLens's control.

## 8. Known limitations

- No guarantee that memory or disk is erased; see 4.
- Oracle-side retention unverified; see 3.
- Database encryption at rest depends on the host's disk; LetterLens
  doesn't encrypt the SQLite file itself.
- Drafts are signed with a random per-process key unless
  `LETTERLENS_SECRET` is set, so a server restart invalidates unsaved
  drafts (they must be scanned again).
- Records saved before this lifecycle existed (earlier demo data) may
  still contain names/addresses and were saved without confirmation;
  "Delete my saved information" removes them for that user.
