"""Read official, public RSS job feeds. Listings are not verified freelance contracts."""
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urlparse
import hashlib
import re
import xml.etree.ElementTree as ET
import requests

FEEDS = {
    'WWR — All programming': 'https://weworkremotely.com/categories/remote-programming-jobs.rss',
    'WWR — Backend': 'https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss',
    'WWR — Full-stack': 'https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss',
    'WWR — DevOps': 'https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss',
}
TAG_RE = re.compile(r'<[^>]*>')

def clean_html(s):
    return re.sub(r'\s+', ' ', unescape(TAG_RE.sub(' ', s or ''))).strip()

def read_feed(name, days=30, limit=15):
    if name not in FEEDS:
        raise ValueError('Unknown feed (only approved feed URLs are supported)')
    url = FEEDS[name]
    try:
        response = requests.get(url, headers={'User-Agent': 'AgentForge-Growth-Research/0.5 (RSS attribution)'}, timeout=25)
        response.raise_for_status()
        if len(response.content) > 3_000_000:
            raise ValueError('Feed is too large')
        root = ET.fromstring(response.content)
    except (requests.RequestException, ET.ParseError, ValueError) as exc:
        raise RuntimeError(f'RSS source unavailable: {exc}') from exc
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, min(int(days), 365)))
    out = []
    for entry in root.findall('.//channel/item'):
        def val(tag):
            return (entry.findtext(tag) or '').strip()
        title, link = clean_html(val('title')), val('link')
        if not title or urlparse(link).scheme != 'https' or urlparse(link).hostname not in ('weworkremotely.com', 'www.weworkremotely.com'):
            continue
        published = val('pubDate')
        try:
            dt = parsedate_to_datetime(published).astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            continue
        if dt < cutoff:
            continue
        description = clean_html(val('description'))[:4000]
        source_id = 'wwr-rss:' + hashlib.sha256(link.encode('utf-8')).hexdigest()[:24]
        out.append({
            'source_id': source_id, 'title': title[:300], 'body': description,
            'published_at': dt.isoformat(), 'source_url': link, 'external_url': '',
            'category': 'Remote job RSS — ' + name,
            'review_note': 'Source: We Work Remotely public RSS. Attribution: We Work Remotely. Usually employment, NOT verified freelance work. Check location, eligibility, engagement type, and application terms before proceeding.'
        })
        if len(out) >= max(1, min(int(limit), 30)):
            break
    return out
