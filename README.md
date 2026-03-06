# ✦ Daily Job Digest

A personal job alert script that cuts through the noise — no more irrelevant emails from LinkedIn, Indeed, and Glassdoor. This script pulls roles that actually match your criteria, scores them, and delivers a beautiful daily digest straight to your inbox.

Built for women in tech who are tired of sifting through 50 mediocre job alerts to find 2 good ones.

---

## What it does

- 🔍 Searches JSearch (aggregates LinkedIn, Indeed, Glassdoor & more) daily
- 💸 Filters by minimum salary — and skips roles with no salary listed
- 📍 Supports remote, hybrid, and on-site roles within your location radius
- 🚫 Auto-excludes senior, manager, and irrelevant roles by keyword
- ✦ Highlights **Perfect Match** roles (exact title + salary + remote) at the top
- 💌 Sends a polished, beautifully designed HTML email digest once a day

---

## What a Perfect Match looks like

A role earns the ✦ **Perfect Match** badge when it hits all three:
- Job title is an **exact match** to one in your list
- Salary is **listed** and meets your minimum
- Role is **fully remote**

Perfect match cards are sorted to the top of your digest automatically.

---

## Setup

### 1. Clone this repo

```bash
git clone https://github.com/yourusername/daily-job-digest.git
cd daily-job-digest
```

### 2. Install dependencies

```bash
pip install requests python-dotenv
```

### 3. Get your API keys

| Service | What it's for | Free tier |
|---|---|---|
| [JSearch via RapidAPI](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) | Job data (LinkedIn, Indeed, Glassdoor) | 200 requests/month |
| [SendGrid](https://sendgrid.com) | Sending the email digest | 100 emails/day |

For JSearch, sign up at RapidAPI and subscribe to the **JSearch - OpenWeb Ninja** plan (free tier).

For SendGrid, verify your sender email under **Settings → Sender Authentication**.

### 4. Create your `.env` file

In the project folder, create a file named `.env` (no extension) with the following:

```
JSEARCH_API_KEY=your_rapidapi_key_here
SENDGRID_API_KEY=your_sendgrid_key_here
ALERT_EMAIL=you@gmail.com
FROM_EMAIL=your_verified_sender@email.com
```

> ⚠️ Never commit your `.env` file to GitHub. It's already in `.gitignore`.

### 5. Run it

```bash
python job_alert.py
```

You should see it fetch jobs, filter them, and send your digest within ~30 seconds.

---

## Customizing your filters

All preferences live at the top of `job_alert.py` in the **YOUR PREFERENCES** section — no deep code changes needed.

```python
JOB_TITLES = [
    "Support Engineer",
    "Technical Support Specialist",
    "Entry Level Software Engineer",
    "Junior Software Engineer",
    "Technical Support Engineer",
]

SALARY_MIN = 80000          # Annual minimum in USD
REQUIRE_SALARY_LISTED = True  # True = skip jobs with no salary listed
LOCATION = "92101"          # Your zip code
DISTANCE_MILES = 25         # Radius for on-site/hybrid roles
DAYS_OLD_MAX = 1            # 1 = today's postings only, 3 = last 3 days

EXCLUDE_TITLE_WORDS = [
    "senior", "sr.", "lead", "principal", "director", ...
]
```

---

## Scheduling (run automatically every day)

### Option A — Render.com (recommended)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New → Cron Job**
3. Connect your GitHub repo
4. Set the command to: `python job_alert.py`
5. Set the schedule to: `0 8 * * *` *(every day at 8am UTC)*
6. Add your `.env` values under **Environment Variables**
7. Deploy ✦

### Option B — Railway.app

Same steps at [railway.app](https://railway.app) → New Project → Deploy from GitHub → add cron schedule under Settings.

---

## Project structure

```
daily-job-digest/
├── job_alert.py      # The main script — edit YOUR PREFERENCES section here
├── .env              # Your API keys (never commit this!)
├── .gitignore        # Keeps .env out of GitHub
└── README.md         # You're here
```

---

## Cost

Everything used here is **free**:
- JSearch API: free tier (200 req/month)
- SendGrid: 100 emails/day free forever
- Render / Railway: free tier for cron jobs

---

## Tech stack

- **Python 3.10+**
- **JSearch API** via RapidAPI — job aggregation
- **SendGrid** — email delivery
- **python-dotenv** — environment variable management

---

*Built with love for women navigating the tech job market. May your inbox only contain roles worth your time. ✦*
