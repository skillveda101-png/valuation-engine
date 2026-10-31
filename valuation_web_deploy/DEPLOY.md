# Deploy: Render (Backend) + Netlify (Frontend)

You will deploy **two separate things**:

| What | Where | Folder |
|------|--------|--------|
| Calculation API + Login + PDF | **Render.com** | `backend/` |
| Form UI (website) | **Netlify.com** | `frontend/` |

Both are free. Total time ~15 minutes.

---

## PART A — Deploy Backend on Render

### A1. Put code on GitHub (required by Render)

1. Create a free account on https://github.com
2. Create a **new repository** (e.g. name: `valuation-engine`)
3. Upload the entire `valuation_web` folder contents to that repo  
   (or use GitHub Desktop / `git push`)

Your repo should look like:
```
valuation-engine/
  backend/
    main.py
    calculations.py
    pdf_generator.py
    auth.py
    requirements.txt
    Procfile
    static/
  frontend/
    index.html
    config.js
    netlify.toml
  DEPLOY.md
  README.md
```

### A2. Create Web Service on Render

1. Go to https://dashboard.render.com → Sign up / Log in (free)
2. Click **New +** → **Web Service**
3. Connect your GitHub account and select the `valuation-engine` repo
4. Fill in:

| Setting | Value |
|---------|--------|
| **Name** | `valuation-engine` (any name) |
| **Region** | Singapore (or closest) |
| **Root Directory** | `backend` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | Free |

5. Click **Advanced** → **Add Environment Variable**:
   - Key: `VALUATION_SECRET`
   - Value: type any long random text (example: `MySecretKey2026Jhapa!`)

6. Click **Create Web Service**
7. Wait 3–5 minutes until status is **Live** (green)
8. Copy your URL, example:
   ```
   https://valuation-engine-xxxx.onrender.com
   ```

### A3. Test backend

Open in browser:
```
https://YOUR-RENDER-URL.onrender.com/api/health
```
You should see: `{"status":"ok"}`

> Note: Free Render sleeps after ~15 min idle. First open after sleep can take 30–60 seconds.

---

## PART B — Connect Frontend to Backend

1. Open the file: **`frontend/config.js`**
2. Change it to your Render URL (no slash at the end):

```js
window.VALUATION_API_URL = "https://valuation-engine-xxxx.onrender.com";
```

3. Save the file
4. If you use GitHub, **commit and push** this change

---

## PART C — Deploy Frontend on Netlify

### Option 1 — Drag & Drop (fastest, no GitHub needed)

1. Go to https://app.netlify.com → Sign up / Log in (free)
2. Go to https://app.netlify.com/drop  
   OR Dashboard → **Add new site** → **Deploy manually**
3. Drag the entire **`frontend`** folder onto the page
4. Wait a few seconds → you get a URL like:
   ```
   https://random-name-123.netlify.app
   ```
5. Done!

### Option 2 — From GitHub (better for updates)

1. Netlify Dashboard → **Add new site** → **Import an existing project**
2. Connect GitHub → select `valuation-engine` repo
3. Build settings:

| Setting | Value |
|---------|--------|
| **Base directory** | `frontend` |
| **Build command** | (leave empty) |
| **Publish directory** | `frontend` |

4. Click **Deploy site**
5. Your site URL appears when deploy finishes

---

## PART D — Use the App

1. Open your **Netlify URL**
2. Login:
   - Username: `admin`
   - Password: `admin123`
3. Fill form → **Preview Calculation** → **Generate & Download PDF**

**Important:** Change the admin password after first login (or ask to add a change-password feature).

---

## Checklist if something fails

| Problem | Fix |
|---------|-----|
| Login fails / Network error | Check `config.js` has correct Render URL |
| `/api/health` not working | Wait for Render to finish deploy; check logs in Render dashboard |
| PDF not downloading | Backend may be sleeping — wait 1 minute and try again |
| CORS error | Already open in code; hard-refresh browser (Ctrl+Shift+R) |
| Wrong FMV | Enter areas and rates carefully; use Sq.M. or Kattha as in your Excel |

---

## Folder to upload

Upload / push the whole `valuation_web` folder.

- **Render** uses only the `backend` subfolder (Root Directory = `backend`)
- **Netlify** uses only the `frontend` subfolder
