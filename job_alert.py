"""
============================================================
  JOB ALERT SCRIPT
  Pulls jobs from JSearch (LinkedIn/Indeed/Glassdoor),
  filters by your criteria, and emails a clean daily digest.
============================================================
  SETUP (one-time):
    pip install requests python-dotenv

  Your .env file should contain:
    JSEARCH_API_KEY=your_rapidapi_key
    SENDGRID_API_KEY=your_sendgrid_key
    ALERT_EMAIL=you@example.com
    FROM_EMAIL=your_verified_sender@example.com
============================================================
"""

import os
import requests
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# ============================================================
#  YOUR PREFERENCES — edit these anytime, no coding needed
# ============================================================

JOB_TITLES = [
    "Support Engineer",
    "Product Support Specialist",
    "Entry Level Software Engineer",
    "Associate Software Engineer",
    "Technical Support Engineer",
]

SALARY_MIN = 80000          # Annual minimum in USD
REQUIRE_SALARY_LISTED = True  # True = skip jobs with no salary info
LOCATION = "90804"          # Zip code for on-site/hybrid roles
DISTANCE_MILES = 25         # Radius around your zip code
RESULTS_PER_TITLE = 10      # How many results to fetch per title
DAYS_OLD_MAX = 1            # Only show jobs posted in the last N days

# Work types to include — remove any you don't want
EMPLOYMENT_TYPES = ["FULLTIME"]   # Options: FULLTIME, PARTTIME, CONTRACTOR

# Words in job titles that should EXCLUDE the role
EXCLUDE_TITLE_WORDS = [
    "senior", "sr.", "lead", "principal", "director",
    "manager", "staff", "graduate program", "intern",
    "health safety", "warehouse", "logistics", "sr",
    "nursing", "clinical", "iv ", "iii ", "ii "
]

# ============================================================
#  JSEARCH API FETCH
# ============================================================

def fetch_jobs(title: str) -> list[dict]:
    api_key = os.getenv("JSEARCH_API_KEY")

    if not api_key:
        raise ValueError("Missing JSEARCH_API_KEY in .env file")

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    params = {
        "query": f"{title} in {LOCATION}",
        "page": "1",
        "num_pages": "1",
        "results_per_page": str(RESULTS_PER_TITLE),
        "date_posted": "today" if DAYS_OLD_MAX == 1 else "3days",
        "employment_types": ",".join(EMPLOYMENT_TYPES),
        "radius": str(DISTANCE_MILES),
    }

    try:
        resp = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers=headers,
            params=params,
            timeout=15
        )
        resp.raise_for_status()
        return resp.json().get("data", [])
    except requests.RequestException as e:
        print(f"  ⚠️  Error fetching '{title}': {e}")
        return []


# ============================================================
#  FILTERING
# ============================================================

def get_normalized_salary(job: dict) -> float:
    """Returns an annualized salary value, or 0 if not listed."""
    lo = job.get("job_min_salary") or 0
    hi = job.get("job_max_salary") or 0
    period = (job.get("job_salary_period") or "").lower()
    salary = hi or lo

    if not salary:
        return 0

    if period == "hourly":
        salary = salary * 2080
    elif period == "monthly":
        salary = salary * 12
    elif period == "weekly":
        salary = salary * 52

    return salary


def is_valid_job(job: dict) -> bool:
    title = job.get("job_title", "").lower()

    # Exclude if title contains seniority/exclusion words
    for word in EXCLUDE_TITLE_WORDS:
        if word.lower() in title:
            return False

    salary = get_normalized_salary(job)

    # Exclude jobs with no salary listed
    if REQUIRE_SALARY_LISTED and not salary:
        return False

    # Exclude jobs below salary minimum
    if salary and salary < SALARY_MIN:
        return False

    return True


def is_perfect_match(job: dict) -> bool:
    """
    A perfect match means ALL of the following are true:
      - Job title exactly matches one of your JOB_TITLES (case-insensitive)
      - Salary is listed AND meets SALARY_MIN
      - Role is remote or hybrid (job_is_remote = True)
    """
    title = job.get("job_title", "").lower().strip()
    exact_titles = [t.lower().strip() for t in JOB_TITLES]
    if title not in exact_titles:
        return False

    salary = get_normalized_salary(job)
    if not salary or salary < SALARY_MIN:
        return False

    if not job.get("job_is_remote", False):
        return False

    return True


def deduplicate(jobs: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for job in jobs:
        job_id = job.get("job_id") or job.get("job_apply_link")
        if job_id and job_id not in seen:
            seen.add(job_id)
            unique.append(job)
    return unique


# ============================================================
#  BUILD EMAIL
# ============================================================

def format_salary(job: dict) -> str:
    lo = job.get("job_min_salary")
    hi = job.get("job_max_salary")
    period = (job.get("job_salary_period") or "").lower()

    if period == "hourly":
        if lo: lo = lo * 2080
        if hi: hi = hi * 2080
    elif period == "monthly":
        if lo: lo = lo * 12
        if hi: hi = hi * 12

    if lo and hi:
        return f"${int(lo):,} – ${int(hi):,}"
    elif hi:
        return f"Up to ${int(hi):,}"
    elif lo:
        return f"From ${int(lo):,}"
    return "Not listed"


def format_work_type(job: dict) -> str:
    is_remote = job.get("job_is_remote", False)
    city = job.get("job_city", "")
    state = job.get("job_state", "")

    if is_remote:
        return "Remote"
    elif city and state:
        return f"{city}, {state}"
    return "On-site"


def build_email_html(jobs: list[dict]) -> str:
    today = datetime.now().strftime("%B %d, %Y")
    count = len(jobs)

    cards = ""
    for job in jobs:
        title = job.get("job_title", "N/A")
        company = job.get("employer_name", "Unknown Company")
        work_type = format_work_type(job)
        is_remote = job.get("job_is_remote", False)
        salary = format_salary(job)
        url = job.get("job_apply_link") or job.get("job_google_link", "#")
        description = job.get("job_description", "")[:240] + "..." if job.get("job_description") else ""
        source = job.get("job_publisher", "")

        # Perfect match detection
        perfect = is_perfect_match(job)

        # Location pill color
        location_color = "#b07d8a" if is_remote else "#8a7db0"
        location_bg = "#f9f0f3" if is_remote else "#f3f0f9"
        location_icon = "✦ Remote" if is_remote else f"◎ {work_type}"

        # Card styling — extra glow for perfect matches
        card_bg = "linear-gradient(145deg, #fff8f0, #fff2ee)" if perfect else "linear-gradient(145deg, #fffaf8, #fff6f4)"
        card_border = "2px solid #c9956e" if perfect else "1px solid #f0ddd8"
        card_shadow = "0 4px 20px rgba(200,140,100,0.18)" if perfect else "0 2px 12px rgba(180,120,110,0.07)"

        # Perfect match badge
        perfect_badge = """
          <div style="
            display: inline-block;
            background: linear-gradient(135deg, #c9956e, #e8b48a);
            color: #fff;
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            padding: 4px 14px;
            border-radius: 20px;
            margin-bottom: 14px;
            font-family: 'Gill Sans','Trebuchet MS',sans-serif;
            box-shadow: 0 2px 8px rgba(180,120,80,0.3);
          ">✦ &nbsp; Perfect Match</div>
        """ if perfect else ""

        cards += f"""
        <div style="
          background: {card_bg};
          border: {card_border};
          border-radius: 16px;
          padding: 28px 28px 22px;
          margin-bottom: 18px;
          box-shadow: {card_shadow};
        ">
          {perfect_badge}
          <!-- Top row: title + salary -->
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;margin-bottom:10px;">
            <div style="flex:1;min-width:0;">
              <h3 style="
                margin: 0 0 5px;
                font-size: 18px;
                color: #2c1810;
                font-family: 'Cormorant Garamond', 'Garamond', 'Georgia', serif;
                font-weight: 600;
                letter-spacing: 0.01em;
                line-height: 1.3;
              ">{title}</h3>
              <p style="margin:0;color:#8a6a62;font-size:13.5px;font-family:'Gill Sans','Trebuchet MS',sans-serif;letter-spacing:0.03em;">
                {company}
                {"<span style='color:#d4b8b2;margin:0 6px;'>·</span><span style='color:#aaa;font-size:12px;'>" + source + "</span>" if source else ""}
              </p>
            </div>
            <div style="
              background: linear-gradient(135deg, #c9a96e, #e8c98a);
              color: #fff;
              padding: 6px 14px;
              border-radius: 20px;
              font-size: 12.5px;
              font-weight: 700;
              font-family: 'Gill Sans','Trebuchet MS',sans-serif;
              letter-spacing: 0.04em;
              white-space: nowrap;
              box-shadow: 0 2px 8px rgba(180,140,80,0.25);
            ">{salary}</div>
          </div>

          <!-- Location pill -->
          <div style="margin-bottom:14px;">
            <span style="
              background:{location_bg};
              color:{location_color};
              font-size:12px;
              font-family:'Gill Sans','Trebuchet MS',sans-serif;
              letter-spacing:0.05em;
              padding:4px 12px;
              border-radius:20px;
              border:1px solid {location_color}33;
              text-transform:uppercase;
            ">{location_icon}</span>
          </div>

          <!-- Description -->
          <p style="
            margin: 0 0 20px;
            color: #7a5a54;
            font-size: 13.5px;
            line-height: 1.7;
            font-family: 'Gill Sans','Trebuchet MS',sans-serif;
          ">{description}</p>

          <!-- CTA -->
          <a href="{url}" style="
            display: inline-block;
            background: linear-gradient(135deg, #c97b8a, #d4959f);
            color: #fff;
            text-decoration: none;
            padding: 11px 24px;
            border-radius: 25px;
            font-size: 13px;
            font-weight: 600;
            font-family: 'Gill Sans','Trebuchet MS',sans-serif;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            box-shadow: 0 3px 12px rgba(180,100,110,0.3);
          ">View & Apply →</a>
        </div>
        """

    if not cards:
        cards = """
        <div style="text-align:center;padding:48px 20px;color:#b09090;font-size:15px;
                    font-family:'Gill Sans','Trebuchet MS',sans-serif;letter-spacing:0.02em;">
          No new matching roles today, darling.<br>
          <span style="font-size:13px;color:#c8b0b0;">Check back tomorrow ✦</span>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:#f7ede8;font-family:'Gill Sans','Trebuchet MS',sans-serif;">

  <div style="max-width:620px;margin:0 auto;padding:32px 16px 48px;">

    <!-- Header -->
    <div style="
      background: linear-gradient(160deg, #3a1c24 0%, #5c2d38 50%, #7a3d48 100%);
      border-radius: 20px 20px 0 0;
      padding: 44px 36px 38px;
      text-align: center;
      position: relative;
      overflow: hidden;
    ">
      <!-- Decorative circles -->
      <div style="position:absolute;top:-30px;right:-30px;width:120px;height:120px;
                  border-radius:50%;background:rgba(220,160,140,0.12);"></div>
      <div style="position:absolute;bottom:-20px;left:-20px;width:80px;height:80px;
                  border-radius:50%;background:rgba(220,160,140,0.08);"></div>

      <p style="
        margin: 0 0 10px;
        color: #d4a090;
        font-size: 11px;
        letter-spacing: 0.25em;
        text-transform: uppercase;
        font-family: 'Gill Sans','Trebuchet MS',sans-serif;
      ">✦ &nbsp; Daily Digest &nbsp; ✦</p>

      <h1 style="
        margin: 0 0 8px;
        color: #fdf0ec;
        font-size: 30px;
        font-family: 'Cormorant Garamond', 'Garamond', 'Georgia', serif;
        font-weight: 500;
        letter-spacing: 0.02em;
        line-height: 1.2;
      ">{count} Role{"s" if count != 1 else ""} Curated<br>
        <span style="font-size:22px;color:#d4a8a0;font-style:italic;">for You</span>
      </h1>

      <p style="margin:14px 0 0;color:#b08880;font-size:12.5px;letter-spacing:0.08em;
                font-family:'Gill Sans','Trebuchet MS',sans-serif;">
        {today.upper()}
      </p>
    </div>

    <!-- Filter summary bar -->
    <div style="
      background: #fff0ec;
      border-left: 1px solid #f0ddd8;
      border-right: 1px solid #f0ddd8;
      padding: 14px 28px;
      text-align: center;
    ">
      <p style="margin:0;color:#b08880;font-size:12px;letter-spacing:0.06em;
                font-family:'Gill Sans','Trebuchet MS',sans-serif;">
        REMOTE &nbsp;·&nbsp; HYBRID &nbsp;·&nbsp; ON-SITE WITHIN {DISTANCE_MILES}MI &nbsp;·&nbsp;
        ${SALARY_MIN:,}+ &nbsp;·&nbsp; SALARY REQUIRED
      </p>
    </div>

    <!-- Cards -->
    <div style="
      background: #fdf5f2;
      border: 1px solid #f0ddd8;
      border-top: none;
      border-radius: 0 0 20px 20px;
      padding: 28px 24px 32px;
    ">
      {cards}
    </div>

    <!-- Footer -->
    <div style="text-align:center;padding:28px 0 0;">
      <p style="margin:0;color:#c4a09a;font-size:11.5px;letter-spacing:0.08em;
                font-family:'Gill Sans','Trebuchet MS',sans-serif;">
        YOUR PERSONAL JOB ALERT &nbsp;✦&nbsp; POWERED BY JSEARCH
      </p>
    </div>

  </div>
</body>
</html>"""


# ============================================================
#  SEND EMAIL VIA SENDGRID
# ============================================================

def send_email(html_body: str, job_count: int):
    api_key = os.getenv("SENDGRID_API_KEY")
    to_email = os.getenv("ALERT_EMAIL")
    from_email = os.getenv("FROM_EMAIL")

    if not api_key or not to_email or not from_email:
        raise ValueError("Missing SENDGRID_API_KEY, ALERT_EMAIL, or FROM_EMAIL in .env file")

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": "Your Job Digest ✦"},
        "subject": f"✦ {job_count} role{'s' if job_count != 1 else ''} curated for you today",
        "content": [{"type": "text/html", "value": html_body}],
    }

    resp = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
        timeout=10,
    )

    if resp.status_code == 202:
        print(f"  ✅ Email sent to {to_email}")
    else:
        print(f"  ❌ SendGrid error {resp.status_code}: {resp.text}")


# ============================================================
#  MAIN
# ============================================================

def main():
    print(f"\n✦ Running job alert — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Titles: {', '.join(JOB_TITLES)}")
    print(f"  Salary min: ${SALARY_MIN:,} | Salary required: {REQUIRE_SALARY_LISTED}")
    print(f"  Location: {LOCATION} ({DISTANCE_MILES}mi radius)\n")

    all_jobs = []
    for title in JOB_TITLES:
        print(f"  Fetching: {title}...")
        jobs = fetch_jobs(title)
        filtered = [j for j in jobs if is_valid_job(j)]
        print(f"    → {len(jobs)} found, {len(filtered)} passed filters")
        all_jobs.extend(filtered)

    all_jobs = deduplicate(all_jobs)

    # Sort: perfect matches first, then the rest
    all_jobs.sort(key=lambda j: (0 if is_perfect_match(j) else 1))
    perfect_count = sum(1 for j in all_jobs if is_perfect_match(j))
    print(f"\n  📋 Total unique matching jobs: {len(all_jobs)} ({perfect_count} perfect match{'es' if perfect_count != 1 else ''})")

    html = build_email_html(all_jobs)

    if all_jobs:
        send_email(html, len(all_jobs))
    else:
        print("  ℹ️  No matches today — skipping email.")

    print("\nDone. ✦\n")


if __name__ == "__main__":
    main()
