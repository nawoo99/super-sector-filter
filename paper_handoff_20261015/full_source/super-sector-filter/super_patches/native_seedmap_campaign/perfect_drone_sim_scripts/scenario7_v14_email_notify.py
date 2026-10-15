#!/usr/bin/env python3
"""Send a one-time c40 terminal email using a locally stored Gmail app password.

No credential is accepted on the command line, written to campaign results, or
committed to a repository. `setup` prompts on a real terminal and sends a test.
"""
import fcntl
from getpass import getpass
import json
import os
from pathlib import Path
import smtplib
import socket
import ssl
import stat
import sys
import tempfile
import time
from datetime import datetime
from email.message import EmailMessage

import run_scenario7_v14_completion as campaign


ADDRESS = 'nawoo5407@gmail.com'
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 465
ROOT = campaign.COMPLETION
CAMPAIGN_STATUS = ROOT / 'status.json'
EMAIL_STATUS = ROOT / 'email_terminal_status.json'
TEST_STATUS = ROOT / 'email_test_status.json'
SECRET_DIRECTORY = Path('/root/.config/super-sector-filter')
SECRET_PATH = SECRET_DIRECTORY / 'scenario7_gmail_app_password'
LOCK_PATH = Path('/tmp/super_sector_filter_scenario7_v14_email.lock')
TERMINAL = ('COMPLETE', 'STOPPED_FOR_DIAGNOSIS')


def timestamp():
    return datetime.now().astimezone().isoformat()


def record(path, **fields):
    campaign.base.atomic_json(path, dict(updated_local=timestamp(), **fields))


def credential_fingerprint():
    try:
        info = SECRET_PATH.stat(follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() \
            or stat.S_IMODE(info.st_mode) != 0o600:
        raise RuntimeError('credential must be an owned regular file with mode 0600')
    directory = SECRET_DIRECTORY.stat(follow_symlinks=False)
    if not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.getuid() \
            or stat.S_IMODE(directory.st_mode) != 0o700:
        raise RuntimeError('credential directory must be owned and mode 0700')
    return (info.st_ino, info.st_mtime_ns, info.st_size)


def normalize_password(value):
    result = ''.join(value.split())
    if len(result) != 16 or not result.isascii() or not result.isalnum():
        raise ValueError('expected a 16-character Google app password')
    return result


def read_password():
    if credential_fingerprint() is None:
        return None
    return normalize_password(SECRET_PATH.read_text(encoding='ascii'))


def save_password(value):
    password = normalize_password(value)
    SECRET_DIRECTORY.mkdir(parents=True, exist_ok=True, mode=0o700)
    if SECRET_DIRECTORY.is_symlink() or SECRET_DIRECTORY.stat().st_uid != os.getuid():
        raise RuntimeError('credential directory is not owned by this user')
    os.chmod(SECRET_DIRECTORY, 0o700)
    descriptor, temporary = tempfile.mkstemp(prefix='.scenario7-gmail-', dir=SECRET_DIRECTORY)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, 'w', encoding='ascii') as stream:
            stream.write(password + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, SECRET_PATH)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def send(subject, body, password):
    mail = EmailMessage()
    mail['From'] = ADDRESS
    mail['To'] = ADDRESS
    mail['Subject'] = subject
    mail.set_content(body)
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT,
                          context=ssl.create_default_context(), timeout=20) as server:
        server.login(ADDRESS, password)
        refused = server.send_message(mail)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


def terminal_message(status):
    state = status['state']
    completed = len(status.get('completed', []))
    if state == 'COMPLETE':
        subject = '[SUPER] c40 no-cutoff campaign complete'
        outcome = '210 planned flights have finished; the original 72 were preserved.'
    else:
        subject = '[SUPER] c40 no-cutoff campaign stopped'
        outcome = 'The continuation stopped for diagnosis. Do not treat it as complete.'
    body = ('SUPER 7-map no-mission-cutoff campaign\n\n'
            + outcome + '\n'
            + f'Continuation triplets completed: {completed}/46\n'
            + f'State: {state}\n'
            + f'Status: {CAMPAIGN_STATUS}\n'
            + f'Results: {ROOT}\n')
    if state == 'COMPLETE':
        body += f'Combined report (if generated): {ROOT / "summary_no_cutoff.md"}\n'
    return subject, body


def setup():
    if not sys.stdin.isatty():
        raise RuntimeError('run setup directly in an interactive terminal')
    print('Google App Passwords: https://myaccount.google.com/apppasswords')
    print('Use a dedicated app password, NOT your normal Google password.')
    print('It will be stored only at ' + str(SECRET_PATH) + ' (0600).')
    password = getpass('16-character app password (hidden): ')
    save_password(password)
    print('Credential saved; sending one test message to ' + ADDRESS + ' ...')
    try:
        send('[SUPER] c40 notification test',
             'This is a test of the local SUPER campaign completion alert.\n',
             read_password())
    except (OSError, smtplib.SMTPException, ValueError) as error:
        record(TEST_STATUS, delivery='FAILED', error_type=type(error).__name__,
               recipient=ADDRESS)
        print('Test failed: ' + type(error).__name__ + '. No credential was printed.')
        return 1
    record(TEST_STATUS, delivery='SENT', recipient=ADDRESS)
    print('Test email sent to ' + ADDRESS)
    return 0


def monitor():
    with LOCK_PATH.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if EMAIL_STATUS.is_file():
            previous = json.loads(EMAIL_STATUS.read_text())
            if previous.get('delivery') == 'SENT':
                print('Terminal email already sent; no duplicate.')
                return 0
        last_state = None
        rejected_credential = None
        while True:
            try:
                status = json.loads(CAMPAIGN_STATUS.read_text())
            except (OSError, json.JSONDecodeError):
                time.sleep(30)
                continue
            if status.get('state') not in TERMINAL:
                if last_state != 'WAITING_FOR_TERMINAL':
                    record(EMAIL_STATUS, delivery='WAITING_FOR_TERMINAL', recipient=ADDRESS)
                    last_state = 'WAITING_FOR_TERMINAL'
                time.sleep(30)
                continue
            try:
                fingerprint = credential_fingerprint()
            except RuntimeError:
                if last_state != 'UNSAFE_CREDENTIAL_FILE':
                    record(EMAIL_STATUS, delivery='UNSAFE_CREDENTIAL_FILE',
                           recipient=ADDRESS, campaign_state=status['state'])
                    last_state = 'UNSAFE_CREDENTIAL_FILE'
                time.sleep(30)
                continue
            if fingerprint is None:
                if last_state != 'WAITING_FOR_AUTH':
                    record(EMAIL_STATUS, delivery='WAITING_FOR_AUTH',
                           recipient=ADDRESS, campaign_state=status['state'])
                    last_state = 'WAITING_FOR_AUTH'
                time.sleep(30)
                continue
            if fingerprint == rejected_credential:
                time.sleep(30)
                continue
            try:
                password = read_password()
                subject, body = terminal_message(status)
                send(subject, body, password)
            except (smtplib.SMTPAuthenticationError, ValueError) as error:
                rejected_credential = fingerprint
                record(EMAIL_STATUS, delivery='AUTH_FAILED', error_type=type(error).__name__,
                       recipient=ADDRESS, campaign_state=status['state'])
                last_state = 'AUTH_FAILED'
                time.sleep(30)
                continue
            except (OSError, smtplib.SMTPException, socket.timeout) as error:
                record(EMAIL_STATUS, delivery='RETRYING', error_type=type(error).__name__,
                       recipient=ADDRESS, campaign_state=status['state'])
                last_state = 'RETRYING'
                time.sleep(120)
                continue
            record(EMAIL_STATUS, delivery='SENT', recipient=ADDRESS,
                   campaign_state=status['state'], completed_triplets=len(
                       status.get('completed', [])))
            print('Terminal email sent to ' + ADDRESS, flush=True)
            return 0


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('setup', 'monitor', 'check'):
        raise SystemExit('usage: scenario7_v14_email_notify.py {setup|monitor|check}')
    command = sys.argv[1]
    if command == 'setup':
        return setup()
    if command == 'check':
        print(json.dumps(dict(recipient=ADDRESS,
                              credential_present=credential_fingerprint() is not None,
                              test_status=(json.loads(TEST_STATUS.read_text())
                                           if TEST_STATUS.is_file() else None),
                              terminal_email_status=(json.loads(EMAIL_STATUS.read_text())
                                                     if EMAIL_STATUS.is_file() else None)),
                         indent=2))
        return 0
    return monitor()


if __name__ == '__main__':
    raise SystemExit(main())
