# Deploying FastAPI Backend to Hugging Face Spaces (No Docker)

You can easily deploy a FastAPI application to Hugging Face Spaces **without writing a Dockerfile**. 

The secret is to use the **Gradio SDK** space environment. Hugging Face's Gradio environment is built to automatically detect a FastAPI instance named `app` inside an `app.py` file and run it natively!

> [!NOTE]
> I have already created the required `app.py` file for you and pushed it to your GitHub repository. It simply imports your backend and exposes it for Hugging Face to find.

Here is the step-by-step guide to getting your backend running:

### Step 1: Create the Space on Hugging Face
1. Go to [Hugging Face Spaces](https://huggingface.co/spaces) and log in.
2. Click the **Create new Space** button.
3. Fill in the required details:
   - **Space name:** `nutrition-vqa-backend` (or whatever you prefer)
   - **License:** Openrail or MIT (Optional)
   - **Select the Space SDK:** Select **Gradio** (This is crucial, do *not* select Docker).
   - **Space Hardware:** Select the Free CPU (or a GPU if your Mistral usage requires it).
4. Click **Create Space**.

### Step 2: Push Your Code to the Space
Since your code is currently on GitHub, you need to push it to this new Hugging Face Space repository.

Open your local terminal in your project directory (or I can run these for you if you provide the Hugging Face Space URL) and run the following commands:

```bash
# 1. Add your Hugging Face Space as a new git remote 
# Replace YOUR_USERNAME and YOUR_SPACE_NAME with your actual Hugging Face details
git remote add huggingface https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME

# 2. Push your code to Hugging Face
git push huggingface main
```
*(Note: It will ask for your Hugging Face username and a Hugging Face Access Token as your password. You can generate an access token in your Hugging Face Settings -> Access Tokens).*

### Step 3: Add Your Environment Variables
Your backend requires a `.env` file (like your `MISTRAL_API_KEY` and MongoDB URI). You must add these securely to the Space.

1. On your Hugging Face Space page, click on the **Settings** tab.
2. Scroll down to the **Variables and secrets** section.
3. Click **New secret**.
4. Add your variables one by one just like they are in your `.env` file (e.g., Name: `MISTRAL_API_KEY`, Value: `your_key_here`).

### Step 4: Watch it Build!
Once you push your code and add your secrets, Hugging Face will automatically:
1. Install everything from your `requirements.txt`
2. Find the `app.py` file I created for you.
3. Launch your FastAPI backend!

You can watch the logs in the "Build" tab. Once it says "Running", your backend is fully deployed without Docker!
