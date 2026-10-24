"""Search public GitHub Issues for potential contract work. NOT verified leads."""
from datetime import datetime, timezone, timedelta
import re
import requests

ENDPOINT = "https://api.github.com/search/issues"
QUERIES = {
    "Hiring / contract": '("looking for developer" OR "hiring contractor")',
    "AI automation": '("AI automation" OR "LLM integration")',
    "Python / backend": '("python developer" OR "backend contractor")',
    "Freelance": '("freelance developer" OR "paid contributor")',
    "Web development": '("web developer" OR "website developer")',
}
# These are candidate signals, not verified paid opportunities.
POSITIVE = ("hiring", "looking for", "seeking", "freelance", "contractor needed",
            "paid", "budget", "bounty", "contract work", "help wanted", "outsourc")
NEGATIVE = ("contractor dashboard", "contractor management", "contractor portal",
            "tree contractor", "construction contractor", "remove contractor",
            "contractor license", "contractor payment", "contractor status")

def search_opportunities(category="Hiring / contract", days=30, limit=15):
    if category not in QUERIES:
        raise ValueError("Unknown category")
    days = max(1, min(int(days), 365))
    limit = max(1, min(int(limit), 30))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    query = f'{QUERIES[category]} is:issue is:open created:>={since}'
    try:
        response = requests.get(ENDPOINT, params={"q": query, "sort": "created", "order": "desc", "per_page": min(100, max(30, limit * 3))},
            headers={"Accept": "application/vnd.github+json", "User-Agent": "AgentForge-Growth-Research/0.3.1"}, timeout=25)
    except requests.RequestException as exc:
        raise RuntimeError(f"GitHub connection failed: {exc}") from exc
    if response.status_code in (403, 429):
        remaining = response.headers.get("X-RateLimit-Remaining", "unknown")
        raise RuntimeError(f"GitHub HTTP {response.status_code}; remaining search requests: {remaining}. Wait and retry later.")
    response.raise_for_status()
    found = []
    for item in response.json().get("items", []):
        if "pull_request" in item:
            continue
        author = item.get("user") or {}
        if author.get("type") == "Bot" or "[bot]" in author.get("login", "").lower():
            continue
        title = (item.get("title") or "").strip()
        body = (item.get("body") or "")[:3000]
        combined = (title + " " + body).lower()
        if not title or any(term in combined for term in NEGATIVE):
            continue
        signals = [term for term in POSITIVE if term in combined]
        if not signals:
            continue
        url = item.get("html_url") or ""
        if not url.startswith("https://github.com/"):
            continue
        found.append({
            "source_id": f"github-issue:{item['id']}",
            "title": title[:300],
            "body": body,
            "published_at": item.get("created_at") or "",
            "source_url": url,
            "external_url": "",
            "category": category,
            "review_note": "Unverified keyword signal: " + ", ".join(signals[:4]) + ". Check the issue for an explicit paid engagement, buyer, budget, and allowed contact channel. No automatic outreach."
        })
        if len(found) >= limit:
            break
    return found
