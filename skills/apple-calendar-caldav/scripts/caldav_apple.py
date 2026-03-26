#!/usr/bin/env python3
import argparse
import base64
import datetime as dt
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

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
    'timezone': 'APPLE_CALDAV_TIMEZONE',
}


TEXT_KEYS = {'SUMMARY', 'DESCRIPTION', 'LOCATION'}
DEFAULT_LOOKBACK_DAYS = 3650
DEFAULT_LOOKAHEAD_DAYS = 3650


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
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class CalDAVClient:
    def __init__(self, base_url: str, username: str, password: str, default_timezone: str = 'UTC'):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.default_timezone = default_timezone or 'UTC'
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

    def _calendar_url(self, calendar_name: str) -> str:
        cal = self.get_calendar(calendar_name)
        return urllib.parse.urljoin(self.base_url + '/', cal['href'])

    def list_events(self, calendar_name: str, start: dt.datetime, end: dt.datetime, expand: bool = True):
        calendar_url = self._calendar_url(calendar_name)
        extra = ''
        if expand:
            extra = f'<c:expand start="{to_utc_basic(start)}" end="{to_utc_basic(end)}"/>'
        body = f'''<?xml version="1.0" encoding="utf-8"?>
<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:prop><d:getetag/><c:calendar-data>{extra}</c:calendar-data></d:prop>
  <c:filter>
    <c:comp-filter name="VCALENDAR">
      <c:comp-filter name="VEVENT">
        <c:time-range start="{to_utc_basic(start)}" end="{to_utc_basic(end)}"/>
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
            etag = resp.find('.//d:getetag', NS)
            if href is None or caldata is None or not caldata.text:
                continue
            parsed_events = parse_ics_bundle(caldata.text, href.text, etag.text if etag is not None else None, calendar_name, self.default_timezone)
            events.extend(parsed_events)
        events.sort(key=lambda e: e.get('sort_key', '99999999'))
        return events

    def find_events(self, calendar_name: str, query: str, start: dt.datetime, end: dt.datetime, expand: bool = True):
        query_lc = query.lower()
        matches = []
        for event in self.list_events(calendar_name, start, end, expand=expand):
            haystack = ' '.join(filter(None, [
                event.get('summary'),
                event.get('description'),
                event.get('location'),
                event.get('uid'),
                event.get('rrule'),
            ])).lower()
            if query_lc in haystack:
                matches.append(event)
        return matches

    def get_event(self, calendar_name: str, uid: str | None = None, href: str | None = None, recurrence_id: str | None = None):
        events = self.list_events(
            calendar_name,
            dt.datetime.now(dt.UTC) - dt.timedelta(days=DEFAULT_LOOKBACK_DAYS),
            dt.datetime.now(dt.UTC) + dt.timedelta(days=DEFAULT_LOOKAHEAD_DAYS),
            expand=False,
        )
        if uid:
            filtered = [e for e in events if e.get('uid') == uid]
            if recurrence_id is not None:
                filtered = [e for e in filtered if e.get('recurrence_id_raw') == recurrence_id]
            for event in filtered:
                return event
            raise RuntimeError(f'Event not found for uid: {uid}')
        if href:
            norm = normalize_href(href)
            filtered = [e for e in events if normalize_href(e.get('href', '')) == norm]
            if recurrence_id is not None:
                filtered = [e for e in filtered if e.get('recurrence_id_raw') == recurrence_id]
            for event in filtered:
                return event
            raise RuntimeError(f'Event not found for href: {href}')
        raise RuntimeError('Provide uid or href to identify the event')

    def put_event(self, event_href: str, ics_text: str, etag: str | None = None):
        event_url = urllib.parse.urljoin(self.base_url + '/', event_href.lstrip('/'))
        headers = {'Content-Type': 'text/calendar; charset=utf-8; component=VEVENT'}
        if etag:
            headers['If-Match'] = etag
        status, response_headers, _ = self.request(event_url, method='PUT', body=ics_text.encode('utf-8'), headers=headers)
        return {'status': status, 'etag': response_headers.get('ETag'), 'path': urllib.parse.urlparse(event_url).path}

    def create_event(self, calendar_name: str, title: str, start_value: str, end_value: str, description: str | None = None, location: str | None = None, timezone_name: str | None = None, rrule: str | None = None):
        calendar_url = self._calendar_url(calendar_name)
        uid = str(uuid.uuid4())
        stamp = to_utc_basic(dt.datetime.now(dt.UTC))
        tz_name = timezone_name or self.default_timezone
        start_info = parse_input_datetime(start_value, tz_name)
        end_info = parse_input_datetime(end_value, tz_name)
        validate_dt_pair(start_info, end_info)
        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//OpenClaw Skill//Apple Calendar CalDAV//EN',
            'BEGIN:VEVENT',
            f'UID:{uid}',
            f'DTSTAMP:{stamp}',
            f'SUMMARY:{escape_ics_text(title)}',
        ]
        lines.extend(serialize_dt('DTSTART', start_info))
        lines.extend(serialize_dt('DTEND', end_info))
        if description:
            lines.append(f'DESCRIPTION:{escape_ics_text(description)}')
        if location:
            lines.append(f'LOCATION:{escape_ics_text(location)}')
        if rrule:
            lines.append(f'RRULE:{rrule}')
        lines += ['END:VEVENT', 'END:VCALENDAR', '']
        body = '\r\n'.join(lines)
        event_url = urllib.parse.urljoin(calendar_url.rstrip('/') + '/', uid + '.ics')
        status, headers, _ = self.request(
            event_url,
            method='PUT',
            body=body.encode('utf-8'),
            headers={'Content-Type': 'text/calendar; charset=utf-8; component=VEVENT', 'If-None-Match': '*'},
        )
        return {'status': status, 'uid': uid, 'href': urllib.parse.urlparse(event_url).path, 'etag': headers.get('ETag'), 'rrule': rrule, 'timezone': tz_name}

    def update_event(self, calendar_name: str, uid: str | None = None, href: str | None = None, recurrence_id: str | None = None, title: str | None = None, start_value: str | None = None, end_value: str | None = None, description: str | None = None, location: str | None = None, timezone_name: str | None = None, rrule: str | None = None, clear_rrule: bool = False):
        event = self.get_event(calendar_name, uid=uid, href=href, recurrence_id=recurrence_id)
        props = event['props'].copy()
        if title is not None:
            props['SUMMARY'] = title
        if description is not None:
            if description == '':
                props.pop('DESCRIPTION', None)
            else:
                props['DESCRIPTION'] = description
        if location is not None:
            if location == '':
                props.pop('LOCATION', None)
            else:
                props['LOCATION'] = location
        tz_name = timezone_name or self.default_timezone
        if start_value is not None:
            start_info = parse_input_datetime(start_value, tz_name)
            apply_dt_to_props(props, 'DTSTART', start_info)
        else:
            start_info = props_to_dtinfo(props, 'DTSTART', tz_name)
        if end_value is not None:
            end_info = parse_input_datetime(end_value, tz_name)
            apply_dt_to_props(props, 'DTEND', end_info)
        else:
            end_info = props_to_dtinfo(props, 'DTEND', tz_name)
        validate_dt_pair(start_info, end_info)
        if clear_rrule:
            props.pop('RRULE', None)
        elif rrule is not None:
            props['RRULE'] = rrule
        props['DTSTAMP'] = to_utc_basic(dt.datetime.now(dt.UTC))
        ics_text = build_ics_from_props(props)
        result = self.put_event(event['href'], ics_text, etag=event.get('etag'))
        result['uid'] = props.get('UID')
        result['href'] = event['href']
        result['recurrence_id'] = props.get('RECURRENCE-ID')
        result['rrule'] = props.get('RRULE')
        return result

    def delete_event(self, calendar_name: str, uid: str | None = None, href: str | None = None, recurrence_id: str | None = None):
        event = self.get_event(calendar_name, uid=uid, href=href, recurrence_id=recurrence_id)
        event_url = urllib.parse.urljoin(self.base_url + '/', event['href'].lstrip('/'))
        headers = {}
        if event.get('etag'):
            headers['If-Match'] = event['etag']
        status, _, _ = self.request(event_url, method='DELETE', headers=headers)
        return {'status': status, 'uid': event.get('uid'), 'href': event.get('href'), 'recurrence_id': event.get('recurrence_id_raw')}


def normalize_href(value: str) -> str:
    return '/' + value.lstrip('/')


def to_utc_basic(value: dt.datetime) -> str:
    return value.astimezone(dt.UTC).strftime('%Y%m%dT%H%M%SZ')


def zone_or_utc(name: str | None):
    if not name:
        return dt.UTC
    try:
        return ZoneInfo(name)
    except Exception:
        raise RuntimeError(f'Invalid timezone: {name}')


def parse_input_datetime(value: str, timezone_name: str | None = None):
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return {'all_day': True, 'date': dt.date.fromisoformat(value), 'timezone': None, 'floating': False}
    normalized = value.replace('Z', '+00:00')
    parsed = dt.datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        tz = zone_or_utc(timezone_name or 'UTC')
        parsed = parsed.replace(tzinfo=tz)
        return {'all_day': False, 'datetime': parsed, 'timezone': timezone_name or 'UTC', 'floating': False}
    return {'all_day': False, 'datetime': parsed, 'timezone': None, 'floating': False}


def serialize_dt(name: str, info: dict):
    if info['all_day']:
        return [f'{name};VALUE=DATE:{info["date"].strftime("%Y%m%d")}']
    if info.get('timezone'):
        local = info['datetime'].astimezone(zone_or_utc(info['timezone']))
        return [f'{name};TZID={info["timezone"]}:{local.strftime("%Y%m%dT%H%M%S")}']
    if info['datetime'].tzinfo is None:
        return [f'{name}:{info["datetime"].strftime("%Y%m%dT%H%M%S")}']
    return [f'{name}:{to_utc_basic(info["datetime"])}']


def validate_dt_pair(start_info: dict, end_info: dict):
    if bool(start_info.get('all_day')) != bool(end_info.get('all_day')):
        raise RuntimeError('DTSTART and DTEND must both be all-day or both timed')
    if start_info['all_day']:
        if end_info['date'] <= start_info['date']:
            raise RuntimeError('For all-day events, end date must be after start date')
        return
    s = start_info['datetime']
    e = end_info['datetime']
    if e <= s:
        raise RuntimeError('End must be after start')


def escape_ics_text(text: str) -> str:
    return text.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def unescape_ics_text(text: str) -> str:
    return text.replace('\\n', '\n').replace('\\,', ',').replace('\\;', ';').replace('\\\\', '\\')


def unfold_ics_lines(ics_text: str):
    raw = ics_text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    lines = []
    for line in raw:
        if not line:
            continue
        if line.startswith((' ', '\t')) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def parse_ics_bundle(ics_text: str, href: str, etag: str | None, calendar_name: str, default_timezone: str):
    lines = unfold_ics_lines(ics_text)
    events = []
    current = None
    for line in lines:
        if line == 'BEGIN:VEVENT':
            current = []
            continue
        if line == 'END:VEVENT':
            if current is not None:
                parsed = parse_vevent_props(current, href, etag, calendar_name, default_timezone)
                events.append(parsed)
            current = None
            continue
        if current is not None:
            current.append(line)
    return events


def parse_vevent_props(event_lines: list[str], href: str, etag: str | None, calendar_name: str, default_timezone: str):
    props = {}
    for line in event_lines:
        if ':' not in line:
            continue
        left, value = line.split(':', 1)
        key = left.split(';', 1)[0]
        params = left[len(key):]
        props[key] = unescape_ics_text(value)
        if params:
            props[f'{key}__PARAMS'] = params
    dtstart = props_to_dtinfo(props, 'DTSTART', default_timezone)
    dtend = props_to_dtinfo(props, 'DTEND', default_timezone)
    recurrence_id = props_to_dtinfo(props, 'RECURRENCE-ID', default_timezone)
    return {
        'uid': props.get('UID'),
        'summary': props.get('SUMMARY', '(untitled)'),
        'description': props.get('DESCRIPTION'),
        'location': props.get('LOCATION'),
        'rrule': props.get('RRULE'),
        'recurrence_id': dtinfo_to_json(recurrence_id),
        'recurrence_id_raw': props.get('RECURRENCE-ID'),
        'dtstart': dtinfo_to_json(dtstart),
        'dtend': dtinfo_to_json(dtend),
        'all_day': bool(dtstart and dtstart.get('all_day')),
        'props': props,
        'href': href,
        'etag': etag,
        'calendar': calendar_name,
        'sort_key': dtinfo_sort_key(dtstart),
    }


def props_to_dtinfo(props: dict, key: str, default_timezone: str | None = None):
    raw = props.get(key)
    if not raw:
        return None
    params = props.get(f'{key}__PARAMS', '')
    if 'VALUE=DATE' in params:
        return {'all_day': True, 'date': dt.date.fromisoformat(f'{raw[0:4]}-{raw[4:6]}-{raw[6:8]}'), 'timezone': None, 'floating': False}
    tz_match = re.search(r'TZID=([^;:]+)', params)
    tz_name = tz_match.group(1) if tz_match else None
    if raw.endswith('Z'):
        parsed = dt.datetime.strptime(raw, '%Y%m%dT%H%M%SZ').replace(tzinfo=dt.UTC)
        return {'all_day': False, 'datetime': parsed, 'timezone': 'UTC', 'floating': False}
    parsed = dt.datetime.strptime(raw, '%Y%m%dT%H%M%S')
    if tz_name:
        parsed = parsed.replace(tzinfo=zone_or_utc(tz_name))
        return {'all_day': False, 'datetime': parsed, 'timezone': tz_name, 'floating': False}
    parsed = parsed.replace(tzinfo=zone_or_utc(default_timezone or 'UTC'))
    return {'all_day': False, 'datetime': parsed, 'timezone': default_timezone or 'UTC', 'floating': True}


def apply_dt_to_props(props: dict, key: str, info: dict):
    if info['all_day']:
        props[key] = info['date'].strftime('%Y%m%d')
        props[f'{key}__PARAMS'] = ';VALUE=DATE'
        return
    if info.get('timezone'):
        local = info['datetime'].astimezone(zone_or_utc(info['timezone']))
        props[key] = local.strftime('%Y%m%dT%H%M%S')
        props[f'{key}__PARAMS'] = f';TZID={info["timezone"]}'
        return
    props[key] = to_utc_basic(info['datetime'])
    props.pop(f'{key}__PARAMS', None)


def build_ics_from_props(props: dict):
    ordered = ['UID', 'RECURRENCE-ID', 'DTSTAMP', 'SUMMARY', 'DTSTART', 'DTEND', 'RRULE', 'DESCRIPTION', 'LOCATION']
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//OpenClaw Skill//Apple Calendar CalDAV//EN', 'BEGIN:VEVENT']
    for key in ordered:
        if key in props:
            value = escape_ics_text(str(props[key])) if key in TEXT_KEYS else str(props[key])
            params = props.get(f'{key}__PARAMS', '')
            lines.append(f'{key}{params}:{value}')
    for key, value in props.items():
        if key in ordered or key.endswith('__PARAMS'):
            continue
        if key in TEXT_KEYS:
            value = escape_ics_text(str(value))
        lines.append(f'{key}:{value}')
    lines += ['END:VEVENT', 'END:VCALENDAR', '']
    return '\r\n'.join(lines)


def dtinfo_to_json(info: dict | None):
    if not info:
        return None
    if info['all_day']:
        return {'type': 'date', 'value': info['date'].isoformat()}
    utc_value = info['datetime'].astimezone(dt.UTC).isoformat().replace('+00:00', 'Z')
    return {
        'type': 'datetime',
        'value': utc_value,
        'timezone': info.get('timezone'),
        'local_value': info['datetime'].isoformat(),
        'floating': info.get('floating', False),
    }


def dtinfo_sort_key(info: dict | None):
    if not info:
        return '99999999'
    if info['all_day']:
        return info['date'].isoformat()
    return info['datetime'].astimezone(dt.UTC).isoformat()


def require_config(args):
    load_env_file(args.env_file)
    values = {
        'url': os.environ.get(ENV_KEYS['url']),
        'username': os.environ.get(ENV_KEYS['username']),
        'password': os.environ.get(ENV_KEYS['password']),
        'calendar': args.calendar or os.environ.get(ENV_KEYS['calendar']),
        'mode': os.environ.get(ENV_KEYS['mode'], 'readonly'),
        'timezone': args.timezone or os.environ.get(ENV_KEYS['timezone'], 'UTC'),
    }
    missing = [ENV_KEYS[k] for k in ('url', 'username', 'password') if not values[k]]
    if missing:
        raise RuntimeError('Missing required environment variables: ' + ', '.join(missing))
    zone_or_utc(values['timezone'])
    return values


def ensure_write_mode(mode: str):
    if mode.lower() not in {'write', 'readwrite', 'rw'}:
        raise RuntimeError(f'Calendar mode does not allow writes: {mode}')


def emit(data, as_json: bool):
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if isinstance(data, list):
        for idx, item in enumerate(data, 1):
            print(f'{idx}. {item}')
    elif isinstance(data, dict):
        for k, v in data.items():
            print(f'{k}: {v}')
    else:
        print(data)


def event_to_output(event: dict):
    return {
        'uid': event.get('uid'),
        'href': event.get('href'),
        'etag': event.get('etag'),
        'calendar': event.get('calendar'),
        'summary': event.get('summary'),
        'description': event.get('description'),
        'location': event.get('location'),
        'all_day': event.get('all_day'),
        'rrule': event.get('rrule'),
        'recurrence_id': event.get('recurrence_id'),
        'dtstart': event.get('dtstart'),
        'dtend': event.get('dtend'),
    }


def cmd_list_calendars(args):
    cfg = require_config(args)
    client = CalDAVClient(cfg['url'], cfg['username'], cfg['password'], default_timezone=cfg['timezone'])
    calendars = client.list_calendars()
    if args.json:
        emit(calendars, True)
        return
    for i, cal in enumerate(calendars, 1):
        comps = ', '.join(cal['components']) if cal['components'] else 'unknown'
        print(f'{i}. {cal["name"]}')
        print(f'   path: {cal["href"]}')
        print(f'   types: {comps}')
        if cal['color']:
            print(f'   color: {cal["color"]}')


def cmd_list_events(args):
    cfg = require_config(args)
    client = CalDAVClient(cfg['url'], cfg['username'], cfg['password'], default_timezone=cfg['timezone'])
    calendar_name = cfg['calendar']
    if not calendar_name:
        raise RuntimeError('No calendar selected. Pass --calendar or set APPLE_CALDAV_CALENDAR.')
    start = dt.datetime.now(dt.UTC)
    end = start + dt.timedelta(days=args.days)
    events = client.list_events(calendar_name, start, end, expand=not args.no_expand)
    output = [event_to_output(e) for e in events[:args.limit]]
    if args.json:
        emit(output, True)
        return
    for i, event in enumerate(output, 1):
        start_value = event['dtstart']['value'] if event['dtstart'] else 'unknown'
        print(f"{i}. {event['summary']} | {start_value}")


def cmd_find_events(args):
    cfg = require_config(args)
    client = CalDAVClient(cfg['url'], cfg['username'], cfg['password'], default_timezone=cfg['timezone'])
    calendar_name = cfg['calendar']
    if not calendar_name:
        raise RuntimeError('No calendar selected. Pass --calendar or set APPLE_CALDAV_CALENDAR.')
    start = dt.datetime.now(dt.UTC) - dt.timedelta(days=args.lookback_days)
    end = dt.datetime.now(dt.UTC) + dt.timedelta(days=args.days)
    events = client.find_events(calendar_name, args.query, start, end, expand=not args.no_expand)
    output = [event_to_output(e) for e in events[:args.limit]]
    if args.json:
        emit(output, True)
        return
    for i, event in enumerate(output, 1):
        start_value = event['dtstart']['value'] if event['dtstart'] else 'unknown'
        print(f"{i}. {event['summary']} | {start_value}")


def cmd_create_event(args):
    cfg = require_config(args)
    ensure_write_mode(cfg['mode'])
    client = CalDAVClient(cfg['url'], cfg['username'], cfg['password'], default_timezone=cfg['timezone'])
    calendar_name = cfg['calendar']
    if not calendar_name:
        raise RuntimeError('No calendar selected. Pass --calendar or set APPLE_CALDAV_CALENDAR.')
    result = client.create_event(calendar_name, args.title, args.start, args.end, description=args.description, location=args.location, timezone_name=cfg['timezone'], rrule=args.rrule)
    emit(result, args.json)


def cmd_update_event(args):
    cfg = require_config(args)
    ensure_write_mode(cfg['mode'])
    client = CalDAVClient(cfg['url'], cfg['username'], cfg['password'], default_timezone=cfg['timezone'])
    calendar_name = cfg['calendar']
    if not calendar_name:
        raise RuntimeError('No calendar selected. Pass --calendar or set APPLE_CALDAV_CALENDAR.')
    result = client.update_event(
        calendar_name,
        uid=args.uid,
        href=args.href,
        recurrence_id=args.recurrence_id,
        title=args.title,
        start_value=args.start,
        end_value=args.end,
        description=args.description,
        location=args.location,
        timezone_name=cfg['timezone'],
        rrule=args.rrule,
        clear_rrule=args.clear_rrule,
    )
    emit(result, args.json)


def cmd_delete_event(args):
    cfg = require_config(args)
    ensure_write_mode(cfg['mode'])
    client = CalDAVClient(cfg['url'], cfg['username'], cfg['password'], default_timezone=cfg['timezone'])
    calendar_name = cfg['calendar']
    if not calendar_name:
        raise RuntimeError('No calendar selected. Pass --calendar or set APPLE_CALDAV_CALENDAR.')
    result = client.delete_event(calendar_name, uid=args.uid, href=args.href, recurrence_id=args.recurrence_id)
    emit(result, args.json)


def build_parser():
    parser = argparse.ArgumentParser(description='Apple Calendar / iCloud CalDAV helper')
    parser.add_argument('--env-file', default=None, help='Path to .env file with APPLE_CALDAV_* variables')
    parser.add_argument('--calendar', default=None, help='Calendar name override')
    parser.add_argument('--timezone', default=None, help='IANA timezone for naive datetimes, e.g. Europe/Lisbon')
    parser.add_argument('--json', action='store_true', help='Emit JSON output')
    sub = parser.add_subparsers(dest='command', required=True)

    p1 = sub.add_parser('list-calendars', help='List available calendars')
    p1.set_defaults(func=cmd_list_calendars)

    p2 = sub.add_parser('list-events', help='List future events from a calendar')
    p2.add_argument('--days', type=int, default=30, help='Look-ahead window in days')
    p2.add_argument('--limit', type=int, default=10, help='Maximum events to print')
    p2.add_argument('--no-expand', action='store_true', help='Do not expand recurring events into instances')
    p2.set_defaults(func=cmd_list_events)

    pfind = sub.add_parser('find-events', help='Search events by text')
    pfind.add_argument('--query', required=True, help='Case-insensitive text query')
    pfind.add_argument('--days', type=int, default=365, help='Look-ahead window in days')
    pfind.add_argument('--lookback-days', type=int, default=30, help='Look-back window in days')
    pfind.add_argument('--limit', type=int, default=20, help='Maximum events to print')
    pfind.add_argument('--no-expand', action='store_true', help='Do not expand recurring events into instances')
    pfind.set_defaults(func=cmd_find_events)

    p3 = sub.add_parser('create-event', help='Create an event (timed or all-day)')
    p3.add_argument('--title', required=True, help='Event title')
    p3.add_argument('--start', required=True, help='Start in YYYY-MM-DD or ISO datetime')
    p3.add_argument('--end', required=True, help='End in YYYY-MM-DD or ISO datetime')
    p3.add_argument('--description', default=None, help='Optional event description')
    p3.add_argument('--location', default=None, help='Optional event location')
    p3.add_argument('--rrule', default=None, help='Optional RRULE, e.g. FREQ=WEEKLY;COUNT=5')
    p3.set_defaults(func=cmd_create_event)

    p4 = sub.add_parser('update-event', help='Update an existing event by uid or href')
    p4.add_argument('--uid', default=None, help='Event UID')
    p4.add_argument('--href', default=None, help='Event href/path')
    p4.add_argument('--recurrence-id', default=None, help='Specific recurring instance RECURRENCE-ID to target')
    p4.add_argument('--title', default=None, help='New title')
    p4.add_argument('--start', default=None, help='New start in YYYY-MM-DD or ISO datetime')
    p4.add_argument('--end', default=None, help='New end in YYYY-MM-DD or ISO datetime')
    p4.add_argument('--description', default=None, help='New description; use empty string to clear')
    p4.add_argument('--location', default=None, help='New location; use empty string to clear')
    p4.add_argument('--rrule', default=None, help='New RRULE')
    p4.add_argument('--clear-rrule', action='store_true', help='Remove RRULE')
    p4.set_defaults(func=cmd_update_event)

    p5 = sub.add_parser('delete-event', help='Delete an existing event by uid or href')
    p5.add_argument('--uid', default=None, help='Event UID')
    p5.add_argument('--href', default=None, help='Event href/path')
    p5.add_argument('--recurrence-id', default=None, help='Specific recurring instance RECURRENCE-ID to target')
    p5.set_defaults(func=cmd_delete_event)
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
