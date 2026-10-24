"""Public Remotive contract/freelance feed; research candidates only."""
import html
import re
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse

ENDPOINT = "https://remotive.com/api/remote-jobs"
TYPES = {"contract", "freelance"}
KEYWORDS = re.compile(r"\b(python|fastapi|django|backend|api|automation|ai|llm|machine learning|chatbot|react|next\.?js|full.stack|devops|docker|kubernetes|cloud|security|cybersecurity|scraping|data engineer)\b", re.I)

def clean_html(value):
    value = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", " ", str(value or ""))
    value = re.sub(r"(?s)<[^>]*>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()

def search_contracts(days=30, limit=30):
    """One API request per click; do not poll frequently (provider advises <=4/day)."""
    resp = requests.get(ENDPOINT, params={"limit": 500},
        headers={"User-Agent":"AgentForgeGrowthEngine/0.9 (local manual research)"},
        timeout=35)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("Unexpected Remotive API response")
    now = datetime.now(timezone.utc)
    found = []
    for job in data["jobs"]:
        if not isinstance(job, dict) or str(job.get("job_type") or "").lower() not in TYPES:
            continue
        title = str(job.get("title") or "").strip()
        description = clean_html(job.get("description"))[:3500]
        if not KEYWORDS.search(title + " " + description):
            continue
        url = str(job.get("url") or "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ("remotive.com","www.remotive.com"):
            continue
        date = str(job.get("publication_date") or "")
        if date:
            try:
                published = datetime.fromisoformat(date.replace("Z","+00:00"))
                if published.tzinfo is None: published = published.replace(tzinfo=timezone.utc)
                if (now-published).total_seconds() > days*86400: continue
            except ValueError:
                pass
        jobid = str(job.get("id") or url.rsplit("/",1)[-1])
        location = str(job.get("candidate_required_location") or "")
        salary = str(job.get("salary") or "")
        kind = str(job.get("job_type") or "").lower()
        found.append({
            "source_id": "remotive:" + jobid,
            "title": title[:300], "source_url":url, "external_url":"",
            "description": description,
            "body": description,
            "budget": "", "salary": salary, "contract_type": kind,
            "location": location, "published_at": date,
            "category": "Remotive — contract/freelance (unverified)",
            "review_note": "Source: Remotive (https://remotive.com)\n"
                "UNVERIFIED contract/freelance role; may be ongoing employment-style contract, NOT a fixed-price client project.\n"
                "Company: "+str(job.get("company_name") or "")[:150]+
                "\nJob type: "+kind+"\nSalary (may be annual, not project budget): "+salary[:120]+
                "\nLocation restriction: "+location[:150]+
                "\nDescription: "+description[:2200]
        })
        if len(found)>=limit: break
    return found
