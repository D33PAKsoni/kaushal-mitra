# KaushalMitra (ಕೌಶಲ ಮಿತ್ರ) — Skill Companion

**AI SkillFit: Video Assessment for Workforce Fitment** *Developed for the Directorate of Electronic Delivery of Citizen Services (EDCS), Karnataka Government*.

KaushalMitra is a mobile-first, voice-native AI assessment platform designed specifically for Karnataka's workforce. It addresses the challenge of identifying job-ready blue-collar and polytechnic-skilled candidates in a standardized, scalable way, particularly for users who may be semi-literate or unfamiliar with formal digital workflows.

---

## 🌟 Core Features

* **Kannada-First Design**: Built around the primary engineering challenge of dialect coverage (Belagavi, Dharwad, Coastal, and more) rather than being a generic bot with a translation layer.
* **Voice & Video Native**: The entire experience is driven by voice and video — candidates never need to type.
* **Adaptive AI Agent**: Uses a three-layer prompt architecture to conduct dynamic interviews that branch based on candidate responses.
* **Multi-Signal Integrity**: In-browser face detection (MediaPipe), audio continuity checks, and face embedding deduplication (DeepFace) to prevent fraud.
* **Govt-Grade Explainability**: Generates bilingual (English + Kannada) "reason cards" for every candidate, designed for district officers without data science backgrounds.

---

## 🖥️ Local Setup & Installation

### Prerequisites

| Tool | Required Version | Note |
| :--- | :--- | :--- |
| **Node.js** | 18+ | Required for the Next.js frontend. |
| **Python** | 3.10+ | Required for the FastAPI backend. |
| **WSL2** | Ubuntu 22.04 | **Mandatory for Windows users**; native Windows breaks audio libraries like `librosa`. |
| **Supabase** | Cloud/Local | Database and storage. |
| **Redis** | Upstash (Free) | Required for the async scoring pipeline. |

### Step 1 — Clone & Environment Setup
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/D33PAKsoni/kaushal-mitra
    cd kaushal-mitra
    ```
2.  **Configure `.env`**: Copy `.env.example` to `.env` and fill in your API keys.
    * **LLM**: `GROQ_API_KEY` (Free tier, ~200ms latency for demos).
    * **ASR**: `HF_API_TOKEN` and `HF_INDIC_WHISPER_URL` (`https://api-inference.huggingface.co/models/vasista22/whisper-kannada-medium`).
    * **TTS**: `BHASHINI_API_KEY` and `BHASHINI_USER_ID`.

### Step 2 — Backend Setup (WSL2/Linux)
1.  **Navigate to backend and install dependencies:**
    ```bash
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Initialize Database & Start Server:**
    ```bash
    python scripts/setup_db.py
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    *API Docs available at: `http://localhost:8000/docs`*

### Step 3 — Frontend Setup
1.  **Install and run:**
    ```bash
    cd frontend
    npm install
    npm run dev
    ```
    *Live at: `http://localhost:3000`*

### Step 4 — Redis Worker (Async Scoring)
1.  **Start the scoring pipeline worker:**
    ```bash
    cd backend
    source venv/bin/activate
    python -m workers.scoring_worker
    ```

---

## 🛠️ Technical Architecture

* **ASR Pipeline**: Primary ASR uses **IndicWhisper** fine-tuned on Indian languages, with a **Whisper large-v3** fallback triggered by a confidence router.
* **Adaptive State Machine**: Interviews progress through Background → Technical L1 → Technical L2 (Conditional) → Situational phases.
* **Scoring Logic**: A 3-stage pipeline involving an **Integrity Gate**, **Skill Score Computation** (55% domain, 25% communication, 20% integrity), and a **Fitment Classifier**.

---
