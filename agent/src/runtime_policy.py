"""Fail-closed network authorization and bounded request accounting.

Offline planning and tests require no credentials. Real requests require an
explicit AGENT_ALLOW_PAID_CALLS=1; configuring a key alone is never authorization.
"""
import os
import re
import threading
import time
from urllib.parse import urlsplit


class PolicyError(RuntimeError):
    pass


class HardDeadline:
    """Stop this CLI process even if a provider continuously drips response bytes.

    Cooperative HTTP deadlines remain the first line of defense. This watchdog
    is the last resort; partial files/last run manifest are kept, never reported
    as successful. It does not kill other processes or shared services.
    """
    def __init__(self, seconds=28 * 60, on_expire=None):
        self.seconds = seconds
        self.on_expire = on_expire or os._exit
        self.timer = None

    def _expire(self):
        try:
            os.write(2, b'agent hard deadline exceeded; partial run, exit=124\n')
        finally:
            self.on_expire(124)

    def __enter__(self):
        self.timer = threading.Timer(self.seconds, self._expire)
        self.timer.daemon = True
        self.timer.start()
        return self

    def __exit__(self, *args):
        self.timer.cancel()


class RuntimePolicy:
    def __init__(self, deadline=None, max_requests=64, max_media_requests=24):
        self.deadline = deadline
        self.max_requests = max_requests
        self.max_media_requests = max_media_requests
        self.requests = 0
        self.media_requests = 0
        self._lock = threading.Lock()

    def remaining(self):
        return max(0.0, self.deadline - time.monotonic()) if self.deadline else float('inf')

    def check_time(self):
        if self.remaining() <= 0:
            raise PolicyError('run deadline exceeded; no further request is allowed')

    def authorize(self, url, method='GET', media=False):
        if os.environ.get('AGENT_ALLOW_PAID_CALLS') != '1':
            raise PolicyError('network disabled: use --plan-only; real calls require AGENT_ALLOW_PAID_CALLS=1')
        parts = urlsplit(url)
        if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
            raise PolicyError('only credential-free HTTPS URLs are allowed')
        self.check_time()
        with self._lock:
            # Polls and downloads are bounded by time, not the generation counter.
            if method == 'POST':
                if self.requests >= self.max_requests:
                    raise PolicyError('model request ceiling reached')
                if media and self.media_requests >= self.max_media_requests:
                    raise PolicyError('media submission ceiling reached')
                self.requests += 1
                self.media_requests += int(media)

    def snapshot(self):
        return {'network_authorized': os.environ.get('AGENT_ALLOW_PAID_CALLS') == '1',
                'model_requests': self.requests, 'media_requests': self.media_requests,
                'max_model_requests': self.max_requests,
                'max_media_requests': self.max_media_requests}


_policy = RuntimePolicy()


def configure_runtime(deadline=None, max_requests=64, max_media_requests=24):
    global _policy
    _policy = RuntimePolicy(deadline, max_requests, max_media_requests)
    return _policy


def policy():
    return _policy


def redact(value):
    text = str(value)
    text = re.sub(r'(?i)(bearer\s+|sk-)[A-Za-z0-9._-]+', '[REDACTED]', text)
    text = re.sub(r'(?i)(api[_-]?key|authorization|access[_-]?token)([\s\"\x27:=]+)[^\s,\"\x27}]+',
                  r'\1\2[REDACTED]', text)
    text = re.sub(r'(https?://[^\s?]+)\?[^\s]+', r'\1?[REDACTED_QUERY]', text)
    return text
