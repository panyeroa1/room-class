# Orbit Ecosystem 🌍🚀

**Orbit** is a next-generation AI-powered communication and collaboration platform. It unifies real-time video conferencing with advanced RAG (Retrieval-Augmented Generation) assistants and specialized AI services.

## 🏗️ Project Structure

The `vidgem` monorepo contains the following core components:

### 1. 🎥 Orbit Meet (`/meet-orb`)

**The Main Frontend & Video Interface.**

- **Tech Stack**: Next.js, LiveKit, React.
- **Purpose**: Provides real-time video calls, screen sharing, and the primary user interface for meetings.
- **Key Features**: Customizable avatars, end-to-end encryption support, and deep integration with Orbit's AI services.

### 2. 🧠 Orbit Onyx (`/orbit-onyx`)

**The AI Intelligence & RAG Backend.**

- **Tech Stack**: Next.js (Web), Python/FastAPI (Backend), Ollama (LLM).
- **Purpose**: Powers the chat assistants, document retrieval, and knowledge management.
- **Key Features**: Connects to your documents (Google Drive, Slack, etc.) and provides accurate, cited answers via chat.

### 3. ⚡ Orbit Services (`/services`)

**specialized AI Microservices.**

- **TTS Server**: rapid text-to-speech generation (Piper, Kokoro).
- **STT Server**: Real-time speech-to-text transcription (Faster-Whisper).

---

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- Docker (optional, for services)
- LiveKit Cloud Account (for video)

### Running Orbit Meet (Frontend)

```bash
cd meet-orb
npm install
npm run dev
# Open http://localhost:3000
```

### Running Orbit Onyx (AI Assistant)

```bash
cd orbit-onyx/web
npm install
npm run dev
# Open http://localhost:3001 (default port may vary)
```

## 📚 Documentation

- Service-specific READMEs are located in their respective directories.
- See `DEPLOYMENT.md` for production deployment instructions.
