# Full-Stack Deployment Guide

Yes! You can definitely deploy your backend to **Hugging Face Spaces** and your frontend to **Vercel**. Your project is actually already perfectly configured to support this out-of-the-box thanks to the `vercel.json` file in your root directory!

Here is the step-by-step guide to get everything live without any issues.

---

## Part 1: Deploy Backend to Hugging Face Spaces

Hugging Face Spaces is perfect for hosting your FastAPI backend because it naturally supports the heavy AI models (PyTorch/FAISS/Transformers) your project uses.

### 1. Create a New Space
1. Go to [Hugging Face Spaces](https://huggingface.co/spaces) and click **Create new Space**.
2. **Space name:** `nutrition-vqa-backend` (or whatever you prefer).
3. **License:** Choose one (e.g., MIT).
4. **Select the Space SDK:** Choose **Docker** -> **Blank**.
5. **Space Hardware:** The free tier (`CPU basic - 2 vCPU · 16 GB`) is usually enough, though responses may be slightly slower. If you have a Pro account, a small GPU is better.
6. Click **Create Space**.

### 2. Upload Your Backend Code
You can either link your GitHub repository or upload files manually. Upload the following files/folders from your local project to the Hugging Face Space:
- `backend/` (entire folder)
- `Dockerfile`
- `requirements.txt`

> [!IMPORTANT]
> **Environment Variables:**
> Go to your Space's **Settings**, scroll down to **Variables and secrets**, and add your secrets (from your local `.env` file):
> - `MISTRAL_API_KEY`
> - `MONGO_URI`
> - *You no longer need Twilio variables since we removed OTP.*

### 3. Build and Wait
Once the files are uploaded, Hugging Face will automatically detect the `Dockerfile` and start building your image. Wait for the status to change from "Building" to "Running".
- **Your Backend URL will look like:** `https://yourusername-nutrition-vqa-backend.hf.space`

---

## Part 2: Deploy Frontend to Vercel

Vercel is the ideal host for your vanilla HTML/JS frontend.

### 1. Push Code to GitHub
Vercel works best by connecting to a Git repository. Push your entire project (including the `frontend/` folder and `vercel.json`) to a public or private GitHub repository.

### 2. Update `vercel.json` (If needed)
Check your `vercel.json` file. It currently points to `https://sathvik-cs-nutrition-vqa-backend.hf.space`. 

```json
{
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://<YOUR_HF_SPACE_URL>/api/$1"
    },
    {
      "source": "/",
      "destination": "/frontend/index.html"
    },
    {
      "source": "/(.*)",
      "destination": "/frontend/$1"
    }
  ]
}
```
*If your Hugging Face space URL is different from the one above, update line 5 to match your new Hugging Face space URL.*

### 3. Deploy on Vercel
1. Go to [Vercel](https://vercel.com/) and log in with GitHub.
2. Click **Add New... -> Project**.
3. Import the GitHub repository you just created.
4. **Framework Preset:** Leave it as "Other" or "Vite" (Vercel will auto-detect it's a static site).
5. **Root Directory:** Leave this as the default root (`./`). Do **not** set it to `/frontend`, because Vercel needs to read the `vercel.json` in the root folder to handle API routing!
6. Click **Deploy**.

---

## 🛠️ How It Works Together
You will **not get any CORS errors** or deployment issues because of how `vercel.json` is configured:
- When a user visits your Vercel site (`your-site.vercel.app`), Vercel serves the files from the `/frontend` directory.
- When your frontend code makes a request to `/api/...`, the Vercel edge network **intercepts** it and secretly forwards it to your Hugging Face backend. 
- The browser thinks it's talking to the same domain, entirely bypassing any cross-origin restrictions!
