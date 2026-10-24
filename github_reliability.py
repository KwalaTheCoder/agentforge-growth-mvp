"""Conservative GitHub HTTP cache and circuit breaker; no credentials or CRM writes."""
import hashlib
import json
import os
from pathlib import Path
import random
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
import requests

CACHE_DIR = Path(__file__).resolve().parent / '.agentforge_cache' / 'github'
LOCK = threading.RLock()
class RateLimited(RuntimeError):
    def __init__(self, message, until=None):
        super().__init__(message)
        self.until = until

class GitHubClient:
    def __init__(self, session=None, cache_dir=None, now=None, sleep=None):
        self.session = session or requests.Session()
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self.now = now or time.time
        self.sleep = sleep or time.sleep
        self.blocked_until = 0
        self.last_rate = {}

    def _path(self, url, params):
        key = json.dumps([url, sorted((params or {}).items())], sort_keys=True)
        return self.cache_dir / (hashlib.sha256(key.encode()).hexdigest() + '.json')

    def _read(self, path):
        try:
            obj=json.loads(path.read_text(encoding='utf-8'))
            return obj if isinstance(obj,dict) and 'data' in obj else None
        except (OSError, ValueError, TypeError):
            return None

    def _write(self,path,data,etag=None):
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_name(path.name+'.'+str(os.getpid())+'.tmp')
        try:
            tmp.write_text(json.dumps({'saved':self.now(),'data':data,'etag':etag}),encoding='utf-8')
            os.replace(tmp,path)
        finally:
            try: tmp.unlink(missing_ok=True)
            except OSError: pass

    def _wait_until(self,response):
        now=self.now()
        raw=response.headers.get('Retry-After','')
        if raw:
            try: return now+max(0,float(raw))
            except ValueError:
                try: return max(now,parsedate_to_datetime(raw).timestamp())
                except (ValueError,TypeError,OverflowError): pass
        reset=response.headers.get('X-RateLimit-Reset','')
        try:
            if reset: return max(now,float(reset))
        except ValueError: pass
        return now+60

    def get(self,url,params=None,ttl=3600,allow_stale=False):
        p=urlparse(url)
        if p.scheme!='https' or p.hostname!='api.github.com':
            raise ValueError('Only https://api.github.com is permitted')
        path=self._path(url,params)
        cached=self._read(path)
        now=self.now()
        if cached and now-cached['saved']<ttl:
            return cached['data']
        if now<self.blocked_until:
            if allow_stale and cached: return cached['data']
            raise RateLimited('GitHub rate limit active; retry after reset.',self.blocked_until)
        headers={'Accept':'application/vnd.github+json','User-Agent':'AgentForge-ReadOnly/2.8'}
        token=os.environ.get('GITHUB_TOKEN','').strip()
        if token: headers['Authorization']='Bearer '+token
        if cached and cached.get('etag'): headers['If-None-Match']=cached['etag']
        for attempt in range(3):
            try:
                response=self.session.get(url,params=params,headers=headers,timeout=(7,20),allow_redirects=False)
            except (requests.Timeout,requests.ConnectionError) as exc:
                if attempt<2:
                    self.sleep(min(4,2**attempt)+random.uniform(0,0.15)); continue
                if allow_stale and cached: return cached['data']
                raise RuntimeError('GitHub network error after limited retries.') from exc
            self.last_rate={k:response.headers.get(k) for k in ('X-RateLimit-Limit','X-RateLimit-Remaining','X-RateLimit-Reset')}
            if response.status_code==304 and cached:
                self._write(path,cached['data'],cached.get('etag'))
                return cached['data']
            if response.status_code in (403,429):
                # 403 may mean forbidden, not rate limited. Don't retry either automatically.
                self.blocked_until=self._wait_until(response)
                if allow_stale and cached: return cached['data']
                raise RateLimited('GitHub API returned 403/429; requests paused to avoid repeated failures.',self.blocked_until)
            if response.status_code in (500,502,503,504) and attempt<2:
                self.sleep(min(4,2**attempt)+random.uniform(0,0.15)); continue
            response.raise_for_status()
            data=response.json()
            self._write(path,data,response.headers.get('ETag'))
            return data
        raise RuntimeError('GitHub unavailable after limited retries.')

CLIENT=GitHubClient()
