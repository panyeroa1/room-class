# Orbit Deployment Guide 🚢🌍

This guide covers the deployment of the Orbit components to production environments.

## 1. 🎥 Deploying Orbit Meet (Frontend)

**Recommended Platform**: Vercel (seamless Next.js support)

1.  **Push Code**: Ensure your `meet-orb` directory is pushed to a Git repository (GitHub/GitLab).
2.  **Import to Vercel**:
    -   Go to Vercel Dashboard -> Add New -> Project.
    -   Select your repository.
    -   **Root Directory**: Set this to `meet-orb`.
3.  **Environment Variables**:
    Add the following variables in the Vercel Project Settings:
    -   `LIVEKIT_API_KEY`: (From your LiveKit Dashboard)
    -   `LIVEKIT_API_SECRET`: (From your LiveKit Dashboard)
    -   `LIVEKIT_URL`: `wss://your-project.livekit.cloud`
    -   `NEXT_PUBLIC_LK_TOKEN_ENDPOINT`: `/api/connection-details` (Default)
4.  **Deploy**: Click **Deploy**. Vercel will build and serve the application.

---

## 2. 🧠 Deploying Orbit Onyx (AI Assistant)

**Recommended Platform**: Vercel (Frontend) + VPS/Cloud Run (Backend)

### Frontend (Web)
1.  **Import to Vercel**: Select the `orbit-onyx` repo.
2.  **Root Directory**: Set to `orbit-onyx/web`.
3.  **Environment Variables**:
    -   `NEXT_PUBLIC_OLLAMA_BASE_URL`: The URL of your Ollama instance (e.g., `http://your-vps-ip:11434`).
    -   `NEXT_PUBLIC_API_URL`: URL of your deployed Orbit Onyx Backend.

### Backend (API)
Orbit Onyx Backend requires a Python environment.
1.  **Docker Deployment**:
    ```bash
    cd orbit-onyx/backend
    docker build -t orbit-onyx-backend .
    docker run -p 8080:8080 -e OLLAMA_BASE_URL=http://host.docker.internal:11434 orbit-onyx-backend
    ```
2.  **VPS**: You can run it directly on a VPS using `uvicorn`.

---

## 3. ⚡ Deploying Services (TTS/STT)

These Python microservices are best deployed via Docker on a GPU-enabled VPS for performance.

### TTS Server
```bash
cd services/tts-server
docker build -t orbit-tts .
docker run -d -p 8000:8000 orbit-tts
```

### STT Server
```bash
cd services/stt-server
docker build -t orbit-stt .
docker run -d -p 8001:8001 --gpus all orbit-stt
```

---

## 🔐 Security Notes
-   **Never** commit `.env.local` files to public repositories.
-   Ensure your LiveKit API Secret is kept private.
-   Restrict CORS origins on your backend services to only allow requests from your deployed `meet-orb` and `orbit-onyx` domains.
