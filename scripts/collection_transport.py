"""Bounded collection with immutable response evidence; no parsing or publication."""
from datetime import datetime, timezone
from hashlib import sha256
import time

from official_http import SourceFetchError, download_once, public_url


class EvidenceTransport:
    def __init__(self, directory, *, download=download_once, sleeper=time.sleep):
        self.directory = directory
        self.download = download
        self.sleep = sleeper
        self.attempts = []

    def __call__(self, url, allowed_hosts, *, observe_response):
        for attempt in (1, 2):
            self.sleep(1)
            item = {'url': public_url(url), 'attempt': attempt,
                    'collectedAt': datetime.now(timezone.utc).isoformat(), 'responses': []}
            self.attempts.append(item)

            def observe(target, status, location):
                item['responses'].append({'url': public_url(target), 'status': status})
                observe_response(target, status, location)

            try:
                raw, encoding = self.download(url, allowed_hosts, observe_response=observe)
            except SourceFetchError as error:
                item.update(status='failed', reason=str(error))
                delay = error.retry_after if error.retry_after is not None else 2
                if not error.retryable or attempt == 2 or delay > 30:
                    raise
                self.sleep(delay)
                continue
            except (ValueError, OSError) as error:
                item.update(status='failed', reason=type(error).__name__)
                raise
            digest = sha256(raw).hexdigest()
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.directory / (digest + '.html')
            if path.exists():
                if path.read_bytes() != raw:
                    raise ValueError('Evidência existente não corresponde ao hash.')
            else:
                with path.open('xb') as stream:
                    stream.write(raw)
            item.update(status='received', sha256=digest, bytes=len(raw), encoding=encoding,
                        file='originals/' + path.name)
            return raw, encoding
