# CLASSROOM PORTAL TODO (Base: livekit-examples/meet.git)

GOAL

- Convert Meet into a "Classroom Portal" optimized for PHYSICAL classrooms:
  - Main UI = transcription + translation (big, readable)
  - No large participant grid
  - Participants list only in sidebar tab
  - Students are MUTED BY DEFAULT (do not publish mic on join)
  - Students may speak ONLY after:
      (1) Raise Hand
      (2) Teacher approves (temporary mic permission)
  - Students should NOT hear teacher’s original audio from the app
    (teacher is physically audible in the room)
  - Optional: students can hear translation TTS (headphones recommended)

REFERENCE NOTES (why these choices)

- Tokens encode permissions/capabilities and are signed JWTs. :contentReference[oaicite:2]{index=2}
- LiveKit lets you update participant permissions after they are connected; revoking CanPublish unpublishes tracks. :contentReference[oaicite:3]{index=3}
- ParticipantPermission supports canPublish/canPublishData/canPublishSources. :contentReference[oaicite:4]{index=4}
- RoomAudioRenderer plays ALL remote participant audio tracks. For classroom we should NOT do that. :contentReference[oaicite:5]{index=5}

--------------------------------------------------------------------------------

PHASE 0 — Repo Orientation (no refactor; just map the code)

[ ] Confirm local dev runs (per repo README):
    - pnpm install
    - copy .env.example -> .env.local
    - pnpm dev
    (The repo’s README documents this flow.) :contentReference[oaicite:6]{index=6}

[ ] Identify the key touchpoints in your clone using grep (fast + deterministic):
    A) Find the token endpoint / token creation logic
       - rg -n "AccessToken|token|api/.*token|createToken|grant" app lib
    B) Find the "Join" / "PreJoin" / landing screen
       - rg -n "Join|PreJoin|roomName|connect" app
    C) Find the in-room layout (where participant grid/audio renderer/control bar live)
       - rg -n "LiveKitRoom|RoomAudioRenderer|VideoConference|ParticipantTile|ControlBar" app lib
    D) Find current participant list / sidebar patterns
       - rg -n "Participants|Sidebar|Tabs|Drawer" app lib

Deliverable:

- You know EXACTLY where to apply changes without guessing file names.

--------------------------------------------------------------------------------

PHASE 1 — Add “Classroom Mode” Route (keep existing Meet intact)

[ ] Add a new route for classroom mode (do NOT break existing Meet route):
    - Example: /classroom/[roomId]
    - Classroom route renders a separate layout component (ClassroomShell)

[ ] Add a mode flag in room state:
    - mode = "meeting" | "classroom"
    - Classroom route hard-sets mode="classroom"

Deliverable:

- /classroom/... loads a dedicated UI shell (even if still placeholder content)

--------------------------------------------------------------------------------

PHASE 2 — Roles + Join Flows (Teacher vs Student)

Roles:

- TEACHER: can publish mic (for STT), can approve student mic, can moderate
- STUDENT: joins as listener by default; can raise hand; may be granted mic temporarily

[ ] Add role selection on entry:
    - Teacher path: “Create Classroom”
    - Student path: “Join Classroom”

[ ] Create a join code strategy (simple + fast):
    - Teacher creates a roomId + joinCode (store in memory or DB later)
    - Students join via joinCode → resolves to roomId

Deliverables:

- Teacher enters classroom as TEACHER
- Students enter classroom as STUDENT

--------------------------------------------------------------------------------

PHASE 3 — Token Policy (Muted by default, but can be granted mic later)

IMPORTANT: This is the corrected requirement:

- Students are NOT blocked forever.
- Students start with mic publishing DISALLOWED, then teacher can enable it mid-session.

[ ] Update token minting to embed:
    - metadata: { role: "teacher" | "student", classroomMode: true, preferredLang?: "..." }
    - grants:
        STUDENT default:
          - canSubscribe = true
          - canPublish = false            (mute-by-default: cannot publish tracks at join)
          - canPublishData = true         (needed for Raise Hand signaling)
        TEACHER:
          - canSubscribe = true
          - canPublish = true
          - canPublishData = true
          - (server-side) must have ability to call UpdateParticipant (via API key/secret backend)

    (Permissions and capabilities in tokens are core LiveKit behavior.) :contentReference[oaicite:7]{index=7}

Deliverable:

- Students join without browser mic prompt (because we won’t attempt mic capture at join)
- Students can still send “raise hand” data messages

--------------------------------------------------------------------------------

PHASE 4 — Classroom UI Layout (Replace grid with text-first classroom UX)

[ ] Build ClassroomShell layout:
    CENTER PANEL (primary)
    - Live Transcription (original language)
    - Live Translation (student language)
    - Segment list + “live partial line” area
    - Clear speaker indicator (Teacher / Approved Student)

    RIGHT SIDEBAR (tabs)
    - Participants
    - Hands Raised (teacher only)
    - Settings

[ ] Participants list rules:
    - No large tiles
    - No auto video
    - Show role badges (Teacher/Student)
    - Show mic state (disabled / requesting / approved / speaking)
    - Show language (student preferred)

Deliverable:

- Classroom Mode looks like a classroom portal, not a meeting.

--------------------------------------------------------------------------------

PHASE 5 — Audio Rules (Stop the “overlap” problem)

Core classroom principle:

- Students should NOT hear teacher’s original audio from the app.
- Only translation TTS (optional) should play.

[ ] REMOVE global remote audio rendering in Classroom Mode:
    - Do not use RoomAudioRenderer in classroom mode (it plays all remote audio). :contentReference[oaicite:8]{index=8}

[ ] Implement selective audio rendering strategy:
    Option A (recommended): render ONLY the “translation agent” audio track
      - Translation TTS is published by a dedicated participant identity, e.g. identity starts with "tts-"
      - Student clients render only that participant’s audio track

    Option B: if you must render more audio
      - Render ONLY currently-approved student mic (at most 1 at a time)
      - Still DO NOT render teacher audio

Deliverables:

- No teacher voice comes out of the app on student devices
- Translation audio can still be played (clean)

--------------------------------------------------------------------------------

PHASE 6 — Raise Hand Signaling (Student → Teacher)

[ ] Student “Raise Hand” button:
    - publishData(topic="classroom.raise_hand", payload={ identity, name, preferredLang, ts })
    - This requires canPublishData=true (we grant it in student token). :contentReference[oaicite:9]{index=9}

[ ] Teacher “Hands Raised Queue” UI:
    - show ordered list with timestamp + language
    - actions:
        [Allow Mic 30s] [Allow Mic] [Deny]
    - enforce “one speaker at a time” policy:
        - when teacher approves a student, auto-revoke any previously approved student

Deliverables:

- Teacher sees requests instantly
- Teacher can manage a speaking queue

--------------------------------------------------------------------------------

PHASE 7 — Teacher Grants Mic Publish (Server-side UpdateParticipant)

This is the heart of your requirement.

[ ] Add backend endpoint: POST /api/classroom/approve-mic
    Input: { roomId, studentIdentity, durationSec? }
    Action:
    - Call LiveKit server API UpdateParticipant to set:
        permission.canPublish = true
        permission.canPublishSources = [MICROPHONE]  (mic only)
        permission.canPublishData = true
        permission.canSubscribe = true
    (ParticipantPermission supports these fields.) :contentReference[oaicite:10]{index=10}

[ ] Add backend endpoint: POST /api/classroom/revoke-mic
    - UpdateParticipant permission.canPublish=false
    - LiveKit behavior: revoking CanPublish unpublishes their published tracks. :contentReference[oaicite:11]{index=11}

[ ] Optional timer handling (recommended):
    - If durationSec provided:
        - schedule revoke after durationSec
    - Also add teacher-side manual “Revoke now”

Deliverables:

- Student is muted by default but can be temporarily authorized to publish mic
- Teacher can revoke anytime; tracks are auto-unpublished on revoke :contentReference[oaicite:12]{index=12}

--------------------------------------------------------------------------------

PHASE 8 — Student Mic UX (No mic permission until approved)

[ ] Student joins with mic disabled and NO mic prompt:
    - Ensure classroom route does not attempt to capture mic on mount
      (do not call getUserMedia; do not set LiveKitRoom audio capture on by default)

[ ] When teacher approves:
    - Student UI shows “You may speak now” + enables mic toggle
    - On student mic toggle ON:
        - call local mic enable (this triggers browser permission prompt only now)
        - web browsers prompt when app first attempts to access microphone. :contentReference[oaicite:13]{index=13}

[ ] When teacher revokes:
    - force mic toggle OFF in UI
    - stop local capture + ensure mic is disabled immediately

Deliverables:

- Zero mic permission prompts at join
- Mic prompts only happen when teacher explicitly grants permission and student chooses to speak

--------------------------------------------------------------------------------

PHASE 9 — Transcription + Translation Rendering (Classroom Center Panel)

[ ] Define message schema for transcript segments (Data channel):
    topic="classroom.transcript"
    payload={
      segmentId, tsStart, tsEnd,
      speaker: "teacher" | "student",
      speakerIdentity,
      langSource,
      textPartial?: string,
      textFinal?: string
    }

[ ] Define message schema for translation segments (Data channel):
    topic="classroom.translation"
    payload={
      segmentId,
      targetLang,
      translatedTextPartial?: string,
      translatedTextFinal?: string,
      recipientIdentity?: string (if per-student targeting)
    }

[ ] Decide pipeline approach:
    A) Implement your own STT/translate service (your existing plan)
    B) Use a LiveKit Agent that subscribes to the teacher mic and publishes text/audio back
       (Agents framework is built for realtime AI pipelines.) :contentReference[oaicite:14]{index=14}

[ ] UI behavior:
    - Show partial line as “typing”
    - When final arrives, commit to scroll log
    - Keep transcript + translation aligned by segmentId

Deliverables:

- Center panel displays realtime transcript + translation cleanly

--------------------------------------------------------------------------------

PHASE 10 — Translation TTS (Optional, clean playback)

[ ] Publish TTS from a dedicated participant identity (e.g., "tts-agent"):
    - This isolates audio so student clients can render ONLY the translation track.

[ ] Student playback rules:
    - Queue vs interrupt policy:
        - Default: queue
        - Optional: “interrupt on new segment”
    - Provide volume slider for translation audio only

Deliverables:

- Students can hear translation without hearing teacher audio

--------------------------------------------------------------------------------

PHASE 11 — QA / Definition of Done (must pass)

[ ] Physical classroom test (20 students):
    - Students join, no echo loops
    - No “teacher audio replay” from app (critical)
    - Raise Hand works
    - Teacher approval enables student mic publishing
    - Revoke disables + unpublishes student mic (immediate) :contentReference[oaicite:15]{index=15}
    - Only one student can be approved at a time (floor control)

[ ] Browser permission sanity:
    - Students are not prompted for mic at join
    - Mic permission prompt only appears after teacher approval and student toggles mic :contentReference[oaicite:16]{index=16}

DONE WHEN:

- Classroom route is text-first (transcript + translation center)
- Participant grid removed from classroom mode
- Students muted by default, can raise hand, teacher can temporarily grant mic publish
- Teacher original audio is not rendered on student devices
- Translation delivery works (text now; TTS optional)
