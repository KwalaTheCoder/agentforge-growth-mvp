"""Bounded, explicit HTTPS homepage research. No crawling, qualification or CRM writes."""
import http.client
import ipaddress
import re
import socket
import ssl
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit

MAX_BYTES = 160_000


def validate_site(url):
    p = urlsplit(str(url or '').strip())
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Only public HTTPS websites on port 443 are supported.')
    host = p.hostname.lower().rstrip('.')
    if len(host) > 253 or '.' not in host or not re.fullmatch(r'[a-z0-9.-]+', host):
        raise ValueError('Invalid public domain.')
    if any(not x or x.startswith('-') or x.endswith('-') for x in host.split('.')):
        raise ValueError('Invalid domain labels.')
    if host.endswith(('.local', '.internal', '.localhost', '.test', '.invalid')):
        raise ValueError('Private or non-public host rejected.')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError('IP-address URLs are not supported.')
    return host, (p.path or '/') + (('?' + p.query) if p.query else '')


def public_ips(host):
    ips = {x[4][0] for x in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError('DNS did not resolve exclusively to public addresses.')
    return sorted(ips)


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, hostname, ip, timeout=8):
        super().__init__(hostname, port=443, timeout=timeout, context=ssl.create_default_context())
        self._pinned_ip = ip

    def connect(self):
        sock = socket.create_connection((self._pinned_ip, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0
        self.title = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'svg'):
            self.skip += 1
        if tag == 'title':
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg') and self.skip:
            self.skip -= 1
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if not self.skip:
            if self.in_title:
                self.title.append(data)
            self.parts.append(data)


def inspect_homepage(url, *, connector=PinnedHTTPS, resolver=public_ips):
    """One HTTPS GET to DNS-pinned public IP, no redirects, no proxy, bounded body."""
    host, path = validate_site(url)
    ip = resolver(host)[0]
    if not ipaddress.ip_address(ip).is_global:
        raise ValueError('Unsafe destination.')
    conn = connector(host, ip, timeout=8)
    try:
        conn.request('GET', path, headers={'Host': host, 'User-Agent': 'AgentForge-Research/4.6',
                                          'Accept': 'text/html', 'Connection': 'close'})
        response = conn.getresponse()
        if 300 <= response.status < 400:
            raise ValueError('Website redirects are not followed; inspect its final URL manually.')
        if response.status != 200:
            raise ValueError(f'Website returned HTTP {response.status}.')
        if 'text/html' not in response.getheader('Content-Type', '').lower():
            raise ValueError('Website did not return HTML.')
        length = response.getheader('Content-Length')
        if length and int(length) > MAX_BYTES:
            raise ValueError('Website page exceeds size limit.')
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError('Website page exceeds size limit.')
    finally:
        conn.close()
    parser = TextOnly()
    parser.feed(body.decode('utf-8', errors='replace'))
    text = re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()[:6000]
    return {'source_url': url, 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
            'page_title': re.sub(r'\s+', ' ', ' '.join(parser.title)).strip()[:200],
            'public_page_excerpt': text,
            'status': 'Public website content captured; NOT independent proof of identity or buyer demand',
            'next_action': 'Human review: confirm site ownership, specific paid need, and permitted contact channel.'}
