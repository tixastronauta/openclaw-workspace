#!/usr/bin/env python3
import argparse
import email
import imaplib
import os
import smtplib
import ssl
import sys
from datetime import datetime
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import formatdate, getaddresses, make_msgid, parseaddr
from pathlib import Path

ENV_PATH = Path('/data/.openclaw/workspace/secrets/.env')


def load_env(path: Path):
    env = {}
    if not path.exists():
        raise FileNotFoundError(f'Missing env file: {path}')
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def cfg(env, key, default=None, required=False):
    value = env.get(key, default)
    if required and (value is None or value == ''):
        raise KeyError(f'Missing required setting: {key}')
    return value


def as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def decode_mime(value):
    if not value:
        return ''
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def imap_connect(env):
    host = cfg(env, 'IMAP_HOST', required=True)
    port = int(cfg(env, 'IMAP_PORT', 993))
    user = cfg(env, 'IMAP_USER', required=True)
    password = cfg(env, 'IMAP_PASS', required=True)
    secure = as_bool(env.get('IMAP_SECURE'), True)
    if secure:
        client = imaplib.IMAP4_SSL(host, port)
    else:
        client = imaplib.IMAP4(host, port)
    client.login(user, password)
    return client


def smtp_connect(env):
    host = cfg(env, 'SMTP_HOST', required=True)
    port = int(cfg(env, 'SMTP_PORT', 587))
    user = env.get('SMTP_USER') or cfg(env, 'IMAP_USER', required=True)
    password = env.get('SMTP_PASS') or cfg(env, 'IMAP_PASS', required=True)
    secure = as_bool(env.get('SMTP_SECURE'), False)
    if secure:
        client = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        client = smtplib.SMTP(host, port, timeout=20)
        client.ehlo()
        client.starttls(context=ssl.create_default_context())
        client.ehlo()
    client.login(user, password)
    return client


def mailbox_name(env, override=None):
    return override or env.get('IMAP_MAILBOX') or 'INBOX'


def list_mailboxes(env):
    m = imap_connect(env)
    try:
        status, boxes = m.list()
        if status != 'OK':
            raise RuntimeError('Could not list mailboxes')
        for raw in boxes:
            print(raw.decode(errors='replace'))
    finally:
        m.logout()


def select_box(m, mailbox):
    status, data = m.select(mailbox, readonly=True)
    if status != 'OK':
        raise RuntimeError(f'Could not open mailbox: {mailbox}')
    return int(data[0]) if data and data[0] else 0


def fetch_headers(m, uids, mailbox):
    results = []
    for uid in uids:
        status, msgdata = m.uid('fetch', uid, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID REPLY-TO REFERENCES IN-REPLY-TO)])')
        if status != 'OK' or not msgdata or not msgdata[0]:
            continue
        raw = msgdata[0][1]
        msg = email.message_from_bytes(raw)
        results.append({
            'uid': uid.decode() if isinstance(uid, bytes) else str(uid),
            'subject': decode_mime(msg.get('Subject', '(no subject)')),
            'from': decode_mime(msg.get('From', '')),
            'date': msg.get('Date', ''),
            'message_id': msg.get('Message-ID', ''),
            'reply_to': msg.get('Reply-To', ''),
            'references': msg.get('References', ''),
            'in_reply_to': msg.get('In-Reply-To', ''),
        })
    return results


def recent(env, limit, mailbox):
    m = imap_connect(env)
    try:
        box = mailbox_name(env, mailbox)
        total = select_box(m, box)
        if total == 0:
            print('No messages')
            return
        status, data = m.uid('search', None, 'ALL')
        if status != 'OK':
            raise RuntimeError('Search failed')
        uids = data[0].split()[-limit:]
        headers = fetch_headers(m, reversed(uids), box)
        for item in headers:
            print(f"UID: {item['uid']}")
            print(f"Subject: {item['subject']}")
            print(f"From: {item['from']}")
            print(f"Date: {item['date']}")
            print('')
    finally:
        m.logout()


def extract_text(msg):
    if msg.is_multipart():
        text_parts = []
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get('Content-Disposition', ''))
            if ctype == 'text/plain' and 'attachment' not in disp.lower():
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                if payload is not None:
                    text_parts.append(payload.decode(charset, errors='replace'))
        return '\n'.join(text_parts).strip()
    payload = msg.get_payload(decode=True)
    if payload is None:
        return ''
    charset = msg.get_content_charset() or 'utf-8'
    return payload.decode(charset, errors='replace').strip()


def read_message(env, uid, mailbox):
    m = imap_connect(env)
    try:
        box = mailbox_name(env, mailbox)
        select_box(m, box)
        status, msgdata = m.uid('fetch', str(uid), '(BODY.PEEK[])')
        if status != 'OK' or not msgdata or not msgdata[0]:
            raise RuntimeError(f'Could not fetch UID {uid}')
        raw = msgdata[0][1]
        msg = email.message_from_bytes(raw)
        print(f"UID: {uid}")
        print(f"Subject: {decode_mime(msg.get('Subject', '(no subject)'))}")
        print(f"From: {decode_mime(msg.get('From', ''))}")
        print(f"To: {decode_mime(msg.get('To', ''))}")
        print(f"Date: {msg.get('Date', '')}")
        if msg.get('Reply-To'):
            print(f"Reply-To: {decode_mime(msg.get('Reply-To'))}")
        if msg.get('Message-ID'):
            print(f"Message-ID: {msg.get('Message-ID')}")
        print('\n---\n')
        print(extract_text(msg))
    finally:
        m.logout()


def build_search_criteria(args):
    criteria = []
    if args.unseen:
        criteria.append('UNSEEN')
    if args.since:
        dt = datetime.strptime(args.since, '%Y-%m-%d')
        criteria.extend(['SINCE', dt.strftime('%d-%b-%Y')])
    if not criteria:
        criteria.append('ALL')
    return criteria


def search(env, args):
    m = imap_connect(env)
    try:
        box = mailbox_name(env, args.mailbox)
        select_box(m, box)
        criteria = build_search_criteria(args)
        status, data = m.uid('search', None, *criteria)
        if status != 'OK':
            raise RuntimeError('Search failed')
        uids = data[0].split()
        if not uids:
            print('No matching messages')
            return
        headers = fetch_headers(m, reversed(uids[-args.limit:]), box)
        filtered = []
        for item in headers:
            if args.from_text and args.from_text.lower() not in item['from'].lower():
                continue
            if args.subject and args.subject.lower() not in item['subject'].lower():
                continue
            filtered.append(item)
        if not filtered:
            print('No matching messages after header filters')
            return
        for item in filtered:
            print(f"UID: {item['uid']}")
            print(f"Subject: {item['subject']}")
            print(f"From: {item['from']}")
            print(f"Date: {item['date']}")
            print('')
    finally:
        m.logout()


def send_mail(env, to, subject, body, cc=None, bcc=None, in_reply_to=None, references=None):
    sender = env.get('SMTP_FROM') or env.get('SMTP_USER') or cfg(env, 'IMAP_USER', required=True)
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = to
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid()
    if cc:
        msg['Cc'] = cc
    if in_reply_to:
        msg['In-Reply-To'] = in_reply_to
    if references:
        msg['References'] = references
    msg.set_content(body)

    recipient_fields = [x for x in [to, cc, bcc] if x]
    recipients = []
    for field in recipient_fields:
        for part in str(field).split(','):
            addr = part.strip()
            if addr:
                recipients.append(addr)
    if not recipients:
        raise RuntimeError('No valid recipients parsed from To/Cc/Bcc')
    try:
        with smtp_connect(env) as s:
            refused = s.sendmail(sender, recipients, msg.as_string())
        if refused:
            raise RuntimeError(f'Recipients refused: {refused!r}')
    except smtplib.SMTPRecipientsRefused as e:
        raise RuntimeError(f'SMTP recipients refused: sender={sender!r} recipients={recipients!r} details={e.recipients!r}')
    except smtplib.SMTPResponseException as e:
        raise RuntimeError(f'SMTP response error: code={e.smtp_code!r} message={e.smtp_error!r} sender={sender!r} recipients={recipients!r}')
    print('SEND_OK')
    print(f'To: {to}')
    if cc:
        print(f'Cc: {cc}')
    if bcc:
        print(f'Bcc: {bcc}')
    print(f'Subject: {subject}')


def fetch_original_for_reply(env, uid, mailbox):
    m = imap_connect(env)
    try:
        box = mailbox_name(env, mailbox)
        select_box(m, box)
        status, msgdata = m.uid('fetch', str(uid), '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM TO CC MESSAGE-ID REPLY-TO REFERENCES)])')
        if status != 'OK' or not msgdata or not msgdata[0]:
            raise RuntimeError(f'Could not fetch original message UID {uid}')
        msg = email.message_from_bytes(msgdata[0][1])
        return {
            'subject': decode_mime(msg.get('Subject', '(no subject)')),
            'from': decode_mime(msg.get('From', '')),
            'to': decode_mime(msg.get('To', '')),
            'cc': decode_mime(msg.get('Cc', '')),
            'reply_to': decode_mime(msg.get('Reply-To', '')),
            'message_id': msg.get('Message-ID', ''),
            'references': msg.get('References', ''),
        }
    finally:
        m.logout()


def reply_mail(env, uid, body, mailbox, reply_all=False):
    orig = fetch_original_for_reply(env, uid, mailbox)
    target = orig['reply_to'] or orig['from']
    target_addrs = [addr for _, addr in getaddresses([target]) if addr]
    if not target_addrs:
        raise RuntimeError('Could not determine reply recipient')
    to = ', '.join(target_addrs)
    cc = None
    if reply_all:
        cc_addrs = [addr for _, addr in getaddresses([orig.get('to', ''), orig.get('cc', '')]) if addr]
        me = (env.get('SMTP_FROM') or env.get('SMTP_USER') or '').lower()
        cc_addrs = [addr for addr in cc_addrs if addr.lower() != me and addr.lower() not in {a.lower() for a in target_addrs}]
        if cc_addrs:
            cc = ', '.join(sorted(dict.fromkeys(cc_addrs)))
    subject = orig['subject']
    if not subject.lower().startswith('re:'):
        subject = f'Re: {subject}'
    refs = ' '.join(x for x in [orig.get('references', ''), orig.get('message_id', '')] if x).strip() or None
    send_mail(env, to=to, subject=subject, body=body, cc=cc, in_reply_to=orig.get('message_id') or None, references=refs)


def smtp_test(env):
    with smtp_connect(env):
        pass
    print('SMTP_OK')


def build_parser():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)

    sub.add_parser('list-mailboxes')

    r = sub.add_parser('recent')
    r.add_argument('--limit', type=int, default=10)
    r.add_argument('--mailbox')

    rd = sub.add_parser('read')
    rd.add_argument('--uid', required=True)
    rd.add_argument('--mailbox')

    s = sub.add_parser('search')
    s.add_argument('--from', dest='from_text')
    s.add_argument('--subject')
    s.add_argument('--since')
    s.add_argument('--unseen', action='store_true')
    s.add_argument('--limit', type=int, default=20)
    s.add_argument('--mailbox')

    snd = sub.add_parser('send')
    snd.add_argument('--to', required=True)
    snd.add_argument('--subject', required=True)
    snd.add_argument('--body', required=True)
    snd.add_argument('--cc')
    snd.add_argument('--bcc')

    rep = sub.add_parser('reply')
    rep.add_argument('--uid', required=True)
    rep.add_argument('--body', required=True)
    rep.add_argument('--mailbox')
    rep.add_argument('--reply-all', action='store_true')

    sub.add_parser('smtp-test')
    return p


def main():
    env = load_env(ENV_PATH)
    args = build_parser().parse_args()
    try:
        if args.cmd == 'list-mailboxes':
            list_mailboxes(env)
        elif args.cmd == 'recent':
            recent(env, args.limit, args.mailbox)
        elif args.cmd == 'read':
            read_message(env, args.uid, args.mailbox)
        elif args.cmd == 'search':
            search(env, args)
        elif args.cmd == 'send':
            send_mail(env, args.to, args.subject, args.body, cc=args.cc, bcc=args.bcc)
        elif args.cmd == 'reply':
            reply_mail(env, args.uid, args.body, args.mailbox, reply_all=args.reply_all)
        elif args.cmd == 'smtp-test':
            smtp_test(env)
        else:
            raise RuntimeError('Unknown command')
    except Exception as e:
        print(f'ERROR: {e!r}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
