# Putting Saree Books online (with the books in Google Sheets)

About 30 minutes, once. Everything here is free.

When you're done:
- The app lives at a web address (e.g. `https://saree-books.streamlit.app`) and works on
  phone and computer.
- The books are kept in a **Google Sheet** in your Google Drive. You can open it any time
  like an Excel file, Google keeps its version history (File → Version history), and the
  app's **Download Excel copy** button gives you an .xlsx whenever you want one.

> Why Google Sheets? Apps on Streamlit's free hosting lose any files they save whenever
> the app restarts, so the books can't live inside the app.

---

## Step 1 — Create the Google Sheet

1. Go to <https://sheets.new> (signed in with the Google account that should own the books).
2. Name it **Saree Books**. Leave it empty — the app fills in the sheets and headings.
3. Keep this tab open; you'll need its link.

## Step 2 — Give the app a Google "robot" account (service account)

The app signs in to Google with its own account that can only open sheets you share with it.

> **No payment needed.** Google will keep offering a "$300 free trial" — ignore it
> (close / Dismiss). Nothing here uses the trial or needs a card: the project, the service
> account and the Sheets/Drive APIs are free on a normal Gmail account. If creating the
> project asks for a billing account, choose **No billing account**.

1. Go to <https://console.cloud.google.com/> and accept the terms if asked.
2. Top bar → project picker → **New project** → name it `saree-books` → **Create**, and select it.
3. Turn on the two APIs (click each, then **Enable**):
   - <https://console.cloud.google.com/apis/library/sheets.googleapis.com>
   - <https://console.cloud.google.com/apis/library/drive.googleapis.com>
4. Go to **IAM & Admin → Service Accounts** → **Create service account**.
   Name: `saree-books` → **Create and continue** → skip the optional steps → **Done**.
5. Click the new service account → **Keys** tab → **Add key → Create new key → JSON → Create**.
   A `.json` file downloads. **Treat it like a password** — don't email it or upload it anywhere
   except Streamlit's Secrets box in Step 4.
6. Copy the service account's email (looks like `saree-books@saree-books-12345.iam.gserviceaccount.com`).

## Step 3 — Share the sheet with the robot

In the Google Sheet: **Share** → paste the service account email → **Editor** → untick
"Notify people" → **Share**.

## Step 4 — Make the settings file, then deploy on Streamlit

First, in Terminal, in this folder, run (use the path of the key file you downloaded):

```
.venv/bin/python make_secrets.py ~/Downloads/saree-books-xxxxxxxx.json
```

It asks for the Google Sheet link and an app password, writes `.streamlit/secrets.toml`
on this computer (never uploaded), checks it can open the sheet, and offers to copy the
settings for Streamlit. Then delete the downloaded `.json` file.


1. The code is in the **private** GitHub repository `sreeram-revoori/saree-books`.
   `.gitignore` keeps the Excel file, backups and `secrets.toml` out of GitHub.
2. Go to <https://share.streamlit.io>, sign in with GitHub. When GitHub asks what Streamlit
   may access, **allow private repositories** (otherwise `saree-books` won't be listed).
   Click **Create app → Deploy a public app from GitHub** — "public app" is just
   Streamlit's name for the free option; the repository stays private and the app is made
   private in Step 5. (The free plan allows one private app — this one.)
   - Repository: your repo, Branch: `main`, Main file: `app.py`
   - App URL: pick a name, e.g. `saree-books`
   - **Advanced settings** → Python version **3.12**, and in **Secrets** paste what
     `make_secrets.py` copied (or the contents of `.streamlit/secrets.toml`).
     Never type real values into `secrets.toml.example` or any file on GitHub.
3. **Deploy**. First start takes a few minutes.

## Step 5 — Keep it private

In Streamlit: your app → **Share** → make sure it is **only accessible to people invited**, and
invite your relative's email (they sign in with that Google/GitHub/email account).
The `app_password` is a second lock on top.

---

## Using the same Google Sheet from the app on this computer (optional)

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` in this folder and fill it
in the same way. The desktop app then reads and writes the same Google Sheet as the online
app, so everything stays in one place. Without that file, the desktop app keeps using
`saree_books.xlsx`.

## Moving existing Excel records into the Google Sheet

If records were already entered in `saree_books.xlsx`: open the Excel file, and for each of
the **Purchases**, **Sales** and **Expenses** sheets copy everything (including the header row)
into a sheet of the same name in the Google Sheet. Then press **Reload** in the app — it
rebuilds Stock and Monthly Summary on the next save.

## If something goes wrong

- *"Could not save"* / *PERMISSION_DENIED*: the sheet isn't shared with the service account email
  as **Editor** (Step 3), or the Sheets/Drive APIs aren't enabled (Step 2.3).
- *App shows the Excel file in the sidebar instead of Google Sheet*: the Secrets are missing
  `spreadsheet` or the `[gcp_service_account]` section.
- *Undo a mistake*: in the Google Sheet, **File → Version history → See version history**,
  pick a time, **Restore this version**, then press **Reload** in the app.
