#!/usr/bin/env python3
import argparse
import base64
import datetime as dt
import os
import ssl
import sys
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
import re

NS = {
    'd': 'DAV:',
    'c': 'urn:ietf:params:xml:ns:caldav',
    'cs': 'http://calendarserver.org/ns/',
    'a': 'http://apple.com/ns/ical/',
}

ENV_KEYS = {
    'url': 'APPLE_CALDAV_URL',
    'username': 'APPLE_CALDAV_USERNAME',
    'password': 'APPLE_CALDAV_PASSWORD',
    'calendar': 'APPLE_CALDAV_CALENDAR',
    'mode': 'APPLE_CALDAV_MODE',
}


def load_env_file(path: str | None) -> None:
    if not path:
        return
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f'env file not found: {p}')
    for raw in p.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


class CalDAVClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self._calendar_home_url = None

    def request(self, url: str, method: str = 'PROPFIND', body: bytes | str | None = None, headers: dict | None = None):
        req = urllib.request.Request(url, method=method)
        auth = base64.b64encode(f'{self.username}:{self.password}'.encode()).decode()
        req.add_header('Authorization', f'Basic {auth}')
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        with urllib.request.urlopen(req, data=(body.encode() if isinstance(body, str) else body), context=ssl.create_default_context(), timeout=30) as resp:
            return resp.status, dict(resp.headers), resp.read()

    def propfind(self, url: str, body: str, depth: str = '0'):
        status, headers, data = self.request(
            url,
            method='PROPFIND',
            body=body,
            headers={'Depth': depth, 'Content-Type': 'application/xml; charset=utf-8'},
        )
        return status, headers, ET.fromstring(data)

    def discover_calendar_home(self) -> str:
        if self._calendar_home_url:
            return self._calendar_home_url
        body1 = '''<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:"><d:prop><d:current-user-principal/></d:prop></d:propfind>'''
        _, _, root = self.propfind(self.base_url, body1, '0')
        principal = root.find('.//d:current-user-principal/d:href', NS)
        if principal is None or not principal.text:
            raise RuntimeError('Could not discover current-user-principal')
        principal_url = urllib.parse.urljoin(self.base_url + '/', principal.text)

        body2 = '''<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav"><d:prop><c:calendar-home-set/></d:prop></d:propfind>'''
        _, _, root = self.propfind(principal_url, body2, '0')
        home = root.find('.//c:calendar-home-set/d:href', NS)
        if home is None or not home.text:
            raise RuntimeError('Could not discover calendar-home-set')
        self._calendar_home_url = urllib.parse.urljoin(self.base_url + '/', home.text)
        return self._calendar_home_url

    def list_calendars(self):
        home_url = self.discover_calendar_home()
        body = '''<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav" xmlns:a="http://apple.com/ns/ical/">
  <d:prop><d:displayname/><d:resourcetype/><a:calendar-color/><c:supported-calendar-component-set/></d:prop>
</d:propfind>'''
        _, _, root = self.propfind(home_url, body, '1')
        calendars = []
        for resp in root.findall('d:response', NS):
            href = resp.find('d:href', NS)
            display = resp.find('.//d:displayname', NS)
            resource_type = resp.find('.//d:resourcetype', NS)
            if href is None or resource_type is None or resource_type.find('c:calendar', NS) is None:
                continue
            components = [comp.attrib.get('name') for comp in resp.findall('.//c:supported-calendar-component-set/c:comp', NS) if comp.attrib.get('name')]
            color = resp.find('.//a:calendar-color', NS)
            calendars.append({
                'name': (display.text or '(unnamed)') if display is not None else '(unnamed)',
                'href': href.text,
                'components': sorted(set(components)),
                'color': color.text if color is not None else None,
            })
        return calendars

    def get_calendar(self, name: str | None = None):
        calendars = self.list_calendars()
        if name:
            for cal in calendars:
                if cal['name'] == name:
                    return cal
            raise RuntimeError(f'Calendar not found: {name}')
        for cal in calendars:
            if 'VEVENT' in cal['components']:
                return cal
        raise RuntimeError('No VEVENT calendar found')

    def list_events(self, calendar_name: str, start: dt.datetime, end: dt.datetime):
        cal = self.get_calendar(calendar_name)
        calendar_url = urllib.parse.urljoin(self.base_url + '/', cal['href'])
        body = f'''<?xml version="1.0" encoding="utf-8"?>
<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:prop><d:getetag/><c:calendar-data/></d:prop>
  <c:filter>
    <c:comp-filter name="VCALENDAR">
      <c:comp-filter name="VEVENT">
        <c:time-range start="{start.strftime('%Y%m%dT%H%M%SZ')}" end="{end.strftime('%Y%m%dT%H%M%SZ')}"/>
      </c:comp-filter>
    </c:comp-filter>
  </c:filter>
</c:calendar-query>'''
        _, _, data = self.request(calendar_url, 'REPORT', body, {'Depth': '1', 'Content-Type': 'application/xml; charset=utf-8'})
        root = ET.fromstring(data)
        events = []
        for resp in root.findall('d:response', NS):
            href = resp.find('d:href', NS)
            caldata = resp.find('.//c:calendar-data', NS)
            if href is None or caldata is None or not caldata.text:
                continue
            parsed = parse_ics(caldata.text)
            parsed['href'] = href.text
            events.append(parsed)
        events.sort(key=lambda e: e.get('sort_key', '99999999'))
        return events

    def create_all_day_event(self, calendar_name: str, title: str, date_str: str, description: str | None = None):
        cal = self.get_calendar(calendar_name)
        calendar_url = urllib.parse.urljoin(self.base_url + '/', cal['href'])
        day = dt.date.fromisoformat(date_str)
        next_day = day + dt.timedelta(days=1)
        uid = str(uuid.uuid4())
        stamp = dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')
        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//OpenClaw Skill//Apple Calendar CalDAV//EN',
            'BEGIN:VEVENT',
            f'UID:{uid}',
            f'DTSTAMP:{stamp}',
            f'SUMMARY:{escape_ics_text(title)}',
            f'DTSTART;VALUE=DATE:{day.strftime("%Y%m%d")}',
            f'DTEND;VALUE=DATE:{next_day.strftime("%Y%m%d")}',
            'TRANSP:TRANSPARENT',
        ]
        if description:
            lines.append(f'DESCRIPTION:{escape_ics_text(description)}')
        lines += ['END:VEVENT', 'END:VCALENDAR', '']
        body = '\r\n'.join(lines).encode()
        event_url = urllib.parse.urljoin(calendar_url.rstrip('/') + '/', uid + '.ics')
        status, headers, _ = self.request(
            event_url,
            method='PUT',
            body=body,
            headers={'Content-Type': 'text/calendar; charset=utf-8; component=VEVENT', 'If-None-Match': '*'},
        )
        return {'status': status, 'uid': uid, 'path': urllib.parse.urlparse(event_url).path, 'etag': headers.get('ETag')}


def escape_ics_text(text: str) -> str:
    return text.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def parse_ics(ics_text: str):
    summary = first_match(ics_text, r'^SUMMARY(?:;[^:]*)?:(.+)$') or '(untitled)'
    dtstart = parse_dt_line(ics_text, 'DTSTART')
    dtend = parse_dt_line(ics_text, 'DTEND')
    uid = first_match(ics_text, r'^UID(?:;[^:]*)?:(.+)$') or ''
    return {
        'summary': summary,
        'dtstart': dtstart,
        'dtend': dtend,
        'uid': uid,
        'sort_key': dtstart['raw'] if dtstart else '99999999',
    }


def first_match(text: str, pattern: str):
    m = re.search(pattern, text, re.M)
    return m.group(1).strip() if m else None


def parse_dt_line(ics_text: str, key: str):
    m = re.search(rf'^{re.escape(key)}(;[^:]*)?:(.+)$', ics_text, re.M)
    if not m:
        return None
    params = m.group(1) or ''
    raw = m.group(2).strip()
    return {
        'raw': raw,
        'all_day': 'VALUE=DATE' in params,
        'params': params,
    }


def require_config(args):
    load_env_file(args.env_file)
    values = {
        'url': os.environ.get(ENV_KEYS['url']),
        'username': os.environ.get(ENV_KEYS['username']),
        'password': os.environ.get(ENV_KEYS['password']),
        'calendar': args.calendar or os.environ.get(ENV_KEYS['calendar']),
        'mode': os.environ.get(ENV_KEYS['mode'], 'readonly'),
    }
    missing = [ENV_KEYS[k] for k in ('url', 'username', 'password') if not values[k]]
    if missing:
        raise RuntimeError('Missing required environment variables: ' + ', '.join(missing))
    return values


def cmd_list_calendars(args):
    cfg = require_config(args)
    client = CalDAVClient(cfg['url'], cfg['username'], cfg['password'])
    for i, cal in enumerate(client.list_calendars(), 1):
        comps = ', '.join(cal['components']) if cal['components'] else 'unknown'
        print(f'{i}. {cal["name"]}')
        print(f'   path: {cal["href"]}')
        print(f'   types: {comps}')
        if cal['color']:
            print(f'   color: {cal["color"]}')


def cmd_list_events(args):
    cfg = require_config(args)
    client = CalDAVClient(cfg['url'], cfg['username'], cfg['password'])
    calendar_name = cfg['calendar']
    if not calendar_name:
        raise RuntimeError('No calendar selected. Pass --calendar or set APPLE_CALDAV_CALENDAR.')
    start = dt.datetime.now(dt.UTC)
    end = start + dt.timedelta(days=args.days)
    events = client.list_events(calendar_name, start, end)
    limit = args.limit if args.limit is not None else len(events)
    for i, event in enumerate(events[:limit], 1):
        start_text = format_dt(event.get('dtstart'))
        print(f'{i}. {event["summary"]} | {start_text}')


def format_dt(parsed):
    if not parsed:
        return 'unknown'
    raw = parsed['raw']
    if parsed['all_day']:
        return f'{raw[0:4]}-{raw[4:6]}-{raw[6:8]} (all day)'
    if len(raw) >= 15:
        return f'{raw[0:4]}-{raw[4:6]}-{raw[6:8]} {raw[9:11]}:{raw[11:13]} UTC'
    return raw


def cmd_create_event(args):
    cfg = require_config(args)
    if cfg['mode'].lower() not in {'write', 'readwrite', 'rw'}:
        raise RuntimeError(f'Calendar mode does not allow writes: {cfg["mode"]}')
    client = CalDAVClient(cfg['url'], cfg['username'], cfg['password'])
    calendar_name = cfg['calendar']
    if not calendar_name:
        raise RuntimeError('No calendar selected. Pass --calendar or set APPLE_CALDAV_CALENDAR.')
    result = client.create_all_day_event(calendar_name, args.title, args.date, args.description)
    print(f'status: {result["status"]}')
    print(f'uid: {result["uid"]}')
    print(f'path: {result["path"]}')


def build_parser():
    parser = argparse.ArgumentParser(description='Apple Calendar / iCloud CalDAV helper')
    parser.add_argument('--env-file', default=None, help='Path to .env file with APPLE_CALDAV_* variables')
    parser.add_argument('--calendar', default=None, help='Calendar name override')
    sub = parser.add_subparsers(dest='command', required=True)

    p1 = sub.add_parser('list-calendars', help='List available calendars')
    p1.set_defaults(func=cmd_list_calendars)

    p2 = sub.add_parser('list-events', help='List future events from a calendar')
    p2.add_argument('--days', type=int, default=30, help='Look-ahead window in days')
    p2.add_argument('--limit', type=int, default=10, help='Maximum events to print')
    p2.set_defaults(func=cmd_list_events)

    p3 = sub.add_parser('create-all-day-event', help='Create an all-day event')
    p3.add_argument('--title', required=True, help='Event title')
    p3.add_argument('--date', required=True, help='Event date in YYYY-MM-DD')
    p3.add_argument('--description', default=None, help='Optional event description')
    p3.set_defaults(func=cmd_create_event)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
