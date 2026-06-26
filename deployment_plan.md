# Step-by-Step Deployment Plan (Free Tier)

This document provides a step-by-step deployment guide for **QueueStorm Investigator** using completely free cloud hosting. It compares available free hosting platforms, details the chosen platform setup, and outlines automated CI/CD deployment.

---

## 1. Cloud Provider Comparison (Free Tier)

| Hosting Provider | Pricing / Limits | Inactivity Sleep (Cold Start) | Card Required? | Key Pros & Cons |
| :--- | :--- | :--- | :--- | :--- |
| **Render** | **Free Web Service**<br>• 0.1 vCPU<br>• 512 MB RAM<br>• 100 GB Bandwidth/mo | Yes (sleeps after 15 mins of inactivity, takes ~50s to wake up) | **No** | **Pros:** Extremely easy GitHub integration, Docker support.<br>**Cons:** Cold start delay on inactivity. |
| **Koyeb** | **Free Nano Instance**<br>• 0.1 vCPU<br>• 512 MB RAM | **No** (always-on service) | Yes (for identity verification) | **Pros:** Runs continuously, no cold starts, supports Docker.<br>**Cons:** Sign-up requires card verification. |
| **Hugging Face Spaces** | **Free Docker Space**<br>• Shared CPU<br>• 16 GB RAM | Yes (sleeps after 48 hours of inactivity) | **No** | **Pros:** Large memory limit, stays active longer than Render.<br>**Cons:** Public-facing dashboard, requires port 7860 binding. |
| **Railway** | **Trial Tier**<br>• $5.00 one-time credit | No | Yes | **Pros:** Excellent deployment CLI and dashboard.<br>**Cons:** Free tier is a one-time trial credit, not monthly recurring. |
| **Vercel** | **Free Serverless Functions**<br>• Generous free tier | No | **No** | **Pros:** Instant scaling, no cold starts.<br>**Cons:** **10-second timeout limit** on free tier (violates our 15s LLM budget). |

### ✅ Recommendation: **Render (Free Tier)**
Render is the ideal choice for this hackathon because **no credit card is required** for registration, it supports standard Docker-based deployments natively, and it integrates directly with GitHub.

> [!TIP]
> **To bypass Render's 15-minute inactivity sleep:** Use a free monitoring service like [UptimeRobot](https://uptimerobot.com/) to ping the `GET /health` endpoint of your Render app every 10 minutes. This will keep the service awake and prevent any cold start delays during evaluation.

---

## 2. Prerequisites & Environment Setup

Before starting the deployment, ensure you have:
1. A GitHub repository containing the codebase.
2. A free [Render account](https://render.com/).
3. A Google Gemini API Key.

---

## 3. Step-by-Step Manual Deployment on Render

### Step 3.1: Create Render Web Service
1. Log in to the [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub account and select your repository (`Sust-Hack-Mythos`).

### Step 3.2: Configure Web Service Parameters
Set the following options in the Render configuration pane:
- **Name**: `queuestorm-investigator-mythos` (or any unique name)
- **Region**: Select the closest region (e.g., `Singapore` or `Oregon`)
- **Branch**: `main`
- **Runtime**: **`Docker`** (Render will automatically detect the `Dockerfile` at the repository root)
- **Instance Type**: **`Free`**

### Step 3.3: Set Environment Variables
Scroll down to the **Advanced** section and add the following Environment Variables:
- `GEMINI_API_KEY`: *Your Google Gemini API Key*
- `PORT`: `8000` (Render will automatically bind its HTTP router to this port)
- `PYTHONUNBUFFERED`: `1`

Click **Create Web Service**. Render will pull the repository, build the Docker container, and deploy it.

### Step 3.4: Verify Deployment
Once the build completes and the dashboard status turns green (Live):
1. Copy the public URL (e.g., `https://queuestorm-investigator-mythos.onrender.com`).
2. Test the health endpoint:
   ```bash
   curl https://queuestorm-investigator-mythos.onrender.com/health
   # Expected Output: {"status": "ok"}
   ```

---

## 4. Automated CI/CD Pipeline

To enable automated testing and continuous deployment, we set up **GitHub Actions**. On every push to the `main` branch:
1. GitHub Actions spins up a runner.
2. Installs Python dependencies and runs `pytest` integration tests.
3. If all tests pass, it triggers Render's deploy hook to pull and deploy the latest commit.

### Setup Steps:
1. In your Render Web Service dashboard, scroll to **Deploy Hook** and copy the unique URL (e.g., `https://api.render.com/deploy/srv-xxxxxxxxxxxx?key=yyyyyyyyyyyy`).
2. Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
3. Create a **New repository secret**:
   - **Name**: `RENDER_DEPLOY_HOOK_URL`
   - **Value**: *Paste the Deploy Hook URL copied from Render*
4. Create a second repository secret (for test validation):
   - **Name**: `GEMINI_API_KEY`
   - **Value**: *Your Google Gemini API Key* (optional, fallback tests run without it, but full integration tests benefit from a valid key)
