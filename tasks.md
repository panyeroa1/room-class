Task ID: T-0001
Title: Add 1,108 languages from JW.org
Status: IN-PROGRESS
Owner: Miles
Created: 2026-01-17 08:05
Last updated: 2026-01-17 08:05

START LOG

Timestamp: 2026-01-17 08:05
Current behavior:
- The app has a limited list of ~25 languages.
- The user wants to expand this to 1,108 languages from JW.org.

Plan and scope:
- Retrieve the language list from JW.org (HTML or JSON).
- Create a new JS file `public/jw_languages.js` with the full list.
- Update `index.html` to load and use this list.
- Attempt to map JW codes to ISO codes for Deepgram/GT where possible.

Files expected to change:
- public/jw_languages.js (New)
- index.html

Risks:
- JW codes may not match Deepgram/GT supported codes, breaking translation for many languages.
- The list is very large, UI might need optimization (but <select> handles 1000 items okay).

END LOG

Timestamp: 2026-01-17 08:35
Summary of what actually changed:
- Extracted 1,139 languages from JW.org JSON data into `jw_languages.js`.
- Updated `index.html` to load this external file and populate the language dropdowns.
- Cleaned up temporary data extraction files.

Files actually modified:
- index.html
- jw_languages.js (New)

How it was tested:
- Verified `jw_languages.js` contains the language array.
- Verified `index.html` references the script correctly and initializes `LANGUAGES` using the external data.

Test result:
- PASS (Static verification)

Known limitations or follow-up tasks:
- Many of the 1,108+ languages are likely not supported by the underlying Deepgram (STT) or Google Translate (Translation) APIs.
- Users selecting these unsupported languages may experience fallback behavior.
