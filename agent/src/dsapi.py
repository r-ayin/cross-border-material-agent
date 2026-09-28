# -*- coding: utf-8 -*-
"""DashScope API client: OpenAI-compatible chat + async task APIs.

Pure standard library (urllib). Handles retry with exponential backoff,
rate-limit handling, endpoint probing and artifact download.
"""
import json
import logging
import os
import random
import re
import ssl
import time
import urllib.error
import urllib.request

from .runtime_policy import PolicyError, policy, redact

log = logging.getLogger("agent")

CONNECT_TIMEOUT = 15
READ_TIMEOUT = 300  # long for chat completions / media endpoints
POLL_INTERVAL_MIN = 3.0
POLL_INTERVAL_MAX = 12.0

_SSL_CTX = None


def _ssl_ctx():
    global _SSL_CTX
    if _SSL_CTX is None:
        _SSL_CTX = ssl.create_default_context()
    return _SSL_CTX


class ApiError(Exception):
    def __init__(self, message, status=None, retryable=False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class AuthError(ApiError):
    pass


class TaskAcceptedError(ApiError):
    """The provider already accepted the task; never replay its POST."""
    def __init__(self, task_id, status=None):
        super().__init__('accepted task could not be retrieved; keep its id and do not resubmit', status=status)
        self.task_id = task_id


class RateLimitError(ApiError):
    def __init__(self, message, retry_after=None):
        super().__init__(message, status=429, retryable=True)
        self.retry_after = retry_after


def get_env():
    key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    dash_base = os.environ.get("DASHSCOPE_BASE_URL", "").strip().rstrip("/")
    openai_base = os.environ.get("OPENAI_BASE_URL", "").strip().rstrip("/")
    return key, dash_base, openai_base


def _http_request(url, data=None, headers=None, method=None, timeout=None, raw_body=None):
    """Perform an HTTP request. Returns (status_code, body_bytes, resp_headers)."""
    if timeout is None:
        timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)
    # urllib only accepts a single socket timeout; collapse (connect, read) tuples
    if isinstance(timeout, (tuple, list)):
        timeout = max(float(t) for t in timeout)
    actual_method = method or ('POST' if data is not None or raw_body is not None else 'GET')
    media = any(token in url for token in ('image', 'video', 'multimodal-generation'))
    policy().authorize(url, actual_method, media=media)
    timeout = max(0.001, min(timeout, policy().remaining()))
    hdrs = dict(headers or {})
    body = None
    if raw_body is not None:
        body = raw_body
    elif data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method or ("POST" if body else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx()) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        try:
            payload = e.read()
        except Exception:
            payload = b""
        return e.code, payload, dict(e.headers or {})
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        raise ApiError(f"network error: {e}", retryable=True) from e


def _raise_for_status(status, payload, context=""):
    text = redact(payload.decode("utf-8", "replace")) if payload else ""
    if status == 401 or status == 403:
        raise AuthError(f"auth failed ({status}): {text[:300]}", status=status)
    if status == 429:
        raise RateLimitError(f"rate limited: {text[:300]}")
    if status >= 500:
        raise ApiError(f"server error {status}: {text[:300]}", status=status, retryable=True)
    if status >= 400:
        raise ApiError(f"client error {status} {context}: {text[:400]}", status=status, retryable=False)


def with_retry(fn, max_retries=4, base_delay=4.0, max_delay=60.0, label="api"):
    """Exponential backoff retry for retryable errors."""
    attempt = 0
    while True:
        policy().check_time()
        try:
            return fn()
        except (AuthError, PolicyError):
            raise
        except RateLimitError as e:
            attempt += 1
            if attempt > max_retries:
                raise
            delay = e.retry_after if e.retry_after else min(base_delay * (2 ** (attempt - 1)), max_delay)
            delay = min(delay + random.uniform(0, 2), max_delay + 10)
            log.warning("[%s] rate limited, retry %d/%d in %.1fs", label, attempt, max_retries, delay)
            if delay >= policy().remaining():
                raise PolicyError('retry would exceed the run deadline')
            time.sleep(delay)
        except ApiError as e:
            if not e.retryable:
                raise
            attempt += 1
            if attempt > max_retries:
                raise
            delay = min(base_delay * (2 ** (attempt - 1)) + random.uniform(0, 2), max_delay)
            log.warning("[%s] retryable error (%s), retry %d/%d in %.1fs", label, str(e)[:120], attempt, max_retries, delay)
            if delay >= policy().remaining():
                raise PolicyError('retry would exceed the run deadline')
            time.sleep(delay)


class ChatClient:
    """OpenAI-compatible chat completions client (streaming-first).

    Long generations (thinking models) can exceed a socket read timeout when
    non-streaming, so we prefer SSE streaming and fall back to a single
    non-streaming request if streaming is rejected.
    """

    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url  # ends with /v1

    def _chat_stream(self, url, payload, timeout=None):
        policy().authorize(url, 'POST')
        payload = dict(payload)
        payload["stream"] = True
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
        )
        collected = []
        received_chars = 0
        completed = False
        read_timeout = max(timeout) if isinstance(timeout, (tuple, list)) else (timeout or READ_TIMEOUT)
        with urllib.request.urlopen(req, timeout=min(read_timeout, policy().remaining()), context=_ssl_ctx()) as resp:
            if resp.status >= 400:
                raise ApiError(f"stream chat error {resp.status}", status=resp.status)
            for raw in resp:
                policy().check_time()
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    completed = True
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if choices:
                    delta = choices[0].get("delta") or {}
                    c = delta.get("content")
                    if c:
                        received_chars += len(c)
                        if received_chars > 2_000_000:
                            raise ApiError('stream response exceeds safety limit')
                        collected.append(c)
                    reason = choices[0].get('finish_reason')
                    if reason == 'stop':
                        completed = True
                    elif reason in ('length', 'content_filter'):
                        raise ApiError(f'incomplete generation: finish_reason={reason}')
        if not completed:
            raise ApiError('SSE stream ended without completion; refusing truncated output')
        return "".join(collected)

    def chat(self, model, messages, temperature=0.7, max_tokens=8000, timeout=None):
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        def _call():
            # streaming first: keeps long thinking generations alive
            try:
                text = self._chat_stream(url, payload, timeout=timeout)
                if text:
                    return text
                raise ApiError('stream returned empty; no automatic duplicate submission')
            except urllib.error.HTTPError as e:
                # streaming may be unsupported or rate-limited; inspect and maybe retry
                if e.code == 429:
                    ra = None
                    try:
                        ra = float(e.headers.get("Retry-After") or 0) or None
                    except (TypeError, ValueError):
                        ra = None
                    raise RateLimitError("rate limited (stream)", retry_after=ra)
                if e.code in (401, 403):
                    raise AuthError(f"auth failed ({e.code})", status=e.code)
                if e.code not in (400, 405, 422):
                    raise ApiError(f'stream rejected ({e.code}); no duplicate submission', status=e.code) from e
                log.warning("stream chat rejected (%s), falling back to non-stream", e.code)
            except (ApiError, PolicyError):
                raise
            except Exception as e:
                raise ApiError('stream interrupted; request outcome unknown, refusing automatic replay') from e

            status, body, _ = _http_request(
                url,
                data=dict(payload, stream=False),
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=timeout or (CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            _raise_for_status(status, body, "chat")
            obj = json.loads(body.decode("utf-8"))
            try:
                return obj["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError) as e:
                raise ApiError(f"unexpected chat response: {json.dumps(obj)[:300]}") from e

        return with_retry(_call, max_retries=6, base_delay=6.0, max_delay=90.0, label=f"chat:{model}")


class OpenAIImageClient:
    """OpenAI-compatible /images/generations fallback for image models."""

    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url  # ends with /v1

    def generate(self, model, prompt, size="1024*1024", n=1):
        url = f"{self.base_url}/images/generations"
        payload = {"model": model, "prompt": prompt, "size": size, "n": n}

        def _call():
            status, body, _ = _http_request(
                url, data=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            _raise_for_status(status, body, "images/generations")
            obj = json.loads(body.decode("utf-8"))
            urls = []
            for d in obj.get("data") or []:
                if d.get("url"):
                    urls.append(d["url"])
            if not urls:
                raise ApiError(f"no image url in response: {json.dumps(obj)[:200]}")
            return urls

        return with_retry(_call, label=f"openai-img:{model}")


class TaskClient:
    """DashScope async task client for image/video synthesis."""

    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url  # ends with /api/v1

    def generate(self, path, model, input_obj, parameters=None, deadline=None, label=""):
        """Smart generation request: synchronous call first, async task fallback.

        Returns the output dict (with artifact URLs) either way. Some platforms
        only support synchronous calls, others require the async task API; this
        method transparently handles both.
        """
        url = f"{self.base_url}{path}"
        payload = {"model": model, "input": input_obj}
        if parameters:
            payload["parameters"] = parameters
        tag = label or f"gen:{model}"

        def _sync():
            status, body, _ = _http_request(
                url,
                data=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=min(180, max(0.001, deadline - time.monotonic())) if deadline else 180,
            )
            if status in (200, 202):
                obj = json.loads(body.decode("utf-8"))
                output = obj.get("output") or {}
                if output.get("task_id") and not extract_urls_from_output(output):
                    return {"__async_task_id__": output["task_id"]}
                return output
            # auth errors are final
            if status in (401, 403):
                raise AuthError(f'auth failed ({status})', status=status)
            if status >= 500:
                raise ApiError(f"server error {status}", status=status, retryable=True)
            raise ApiError(f"sync failed {status}: {(body or b'').decode('utf-8', 'replace')[:200]}",
                           status=status, retryable=False)

        if deadline is not None and time.monotonic() >= deadline:
            raise ApiError('media deadline expired before submission')
        try:
            # Retrying an uncertain POST can create and charge a second task.
            out = _sync()
        except ApiError as e:
            if isinstance(e, AuthError) or e.status not in (400, 405, 422):
                raise
            if 'async' not in str(e).lower():
                raise
            log.info('[%s] server explicitly requires async submission', tag)
        else:
            if '__async_task_id__' in out:
                if deadline is None:
                    raise ApiError('async task returned without deadline')
                # Preserve accepted-task identity across every caller/fallback layer.
                task_id = out['__async_task_id__']
                try:
                    return self.poll(task_id, deadline)
                except Exception as e:
                    raise TaskAcceptedError(task_id, getattr(e, 'status', None)) from e
            return out

        def _async():
            status, body, _ = _http_request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "X-DashScope-Async": "enable",
                },
                timeout=(CONNECT_TIMEOUT, 60),
            )
            _raise_for_status(status, body, f"submit:{path}")
            obj = json.loads(body.decode("utf-8"))
            task_id = (obj.get("output") or {}).get("task_id")
            if not task_id:
                raise ApiError(f"no task_id in response: {json.dumps(obj)[:300]}")
            return task_id

        task_id = _async()
        if deadline is None:
            deadline = time.monotonic() + 15 * 60
        try:
            return self.poll(task_id, deadline)
        except Exception as e:
            raise TaskAcceptedError(task_id, getattr(e, 'status', None)) from e

    def submit(self, path, model, input_obj, parameters=None, timeout=None):
        """Legacy async-only submit kept for compatibility."""
        url = f"{self.base_url}{path}"
        payload = {"model": model, "input": input_obj}
        if parameters:
            payload["parameters"] = parameters

        def _call():
            status, body, _ = _http_request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "X-DashScope-Async": "enable",
                },
                timeout=timeout or (CONNECT_TIMEOUT, 60),
            )
            _raise_for_status(status, body, f"submit:{path}")
            obj = json.loads(body.decode("utf-8"))
            task_id = (obj.get("output") or {}).get("task_id")
            if not task_id:
                raise ApiError(f"no task_id in response: {json.dumps(obj)[:300]}")
            return task_id

        return with_retry(_call, label=f"submit:{model}")

    def poll(self, task_id, deadline):
        """Poll task until SUCCEEDED/FAILED or deadline. Returns output dict."""
        url = f"{self.base_url}/tasks/{task_id}"
        interval = POLL_INTERVAL_MIN
        while time.monotonic() < deadline:
            status, body, _ = _http_request(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                method="GET",
                timeout=min(30, max(0.001, deadline - time.monotonic())),
            )
            _raise_for_status(status, body, "poll")
            obj = json.loads(body.decode("utf-8"))
            output = obj.get("output") or {}
            task_status = output.get("task_status", "")
            if task_status == "SUCCEEDED":
                return output
            if task_status in ("FAILED", "UNKNOWN"):
                msg = output.get("message") or output.get("code") or json.dumps(output)[:200]
                raise ApiError(f"task failed: {msg}")
            log.debug("task %s status=%s", task_id, task_status)
            time.sleep(min(interval, max(1.0, deadline - time.monotonic())))
            interval = min(interval * 1.4, POLL_INTERVAL_MAX)
        raise ApiError(f"task {task_id} poll timeout", retryable=False)


def extract_urls_from_output(output):
    """Extract artifact URLs from a task output (results/choices layouts)."""
    urls = []
    for r in output.get("results") or []:
        if isinstance(r, dict) and r.get("url"):
            urls.append(r["url"])
    for c in output.get("choices") or []:
        msg = (c or {}).get("message") or {}
        content = msg.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if part.get("url"):
                        urls.append(part["url"])
                    elif part.get("image"):
                        urls.append(part["image"])
                    elif part.get("video"):
                        urls.append(part["video"])
    if output.get("video_url"):
        urls.append(output["video_url"])
    return urls


def download_file(url, dest_path, max_retries=3, label="download"):
    """Bounded, atomic download; credentials are never sent to artifact hosts."""
    limit = (200 if str(dest_path).endswith('.mp4') else 10) * 1024 * 1024
    def _call():
        policy().authorize(url)
        req = urllib.request.Request(url, headers={"User-Agent": "agent/1.1"})
        tmp = dest_path + '.part'
        try:
            with urllib.request.urlopen(req, timeout=min(READ_TIMEOUT, policy().remaining()), context=_ssl_ctx()) as resp:
                received = 0
                with open(tmp, 'wb') as f:
                    while True:
                        policy().check_time()
                        chunk = resp.read(256 * 1024)
                        if not chunk:
                            break
                        received += len(chunk)
                        if received > limit:
                            raise ApiError('artifact exceeds download size limit')
                        f.write(chunk)
                if not received:
                    raise ApiError('empty artifact download')
                os.replace(tmp, dest_path)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ApiError('artifact download interrupted', retryable=True) from e
        finally:
            if os.path.isfile(tmp):
                os.remove(tmp)
        return os.path.getsize(dest_path)

    return with_retry(_call, max_retries=max_retries, base_delay=3.0, label=label)


def extract_json_block(text):
    """Extract the first JSON object/array from LLM text output."""
    if not text:
        return None
    text = text.strip()
    # strip markdown fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        while start != -1:
            depth = 0
            in_str = False
            esc = False
            for i in range(start, len(text)):
                ch = text[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == opener:
                    depth += 1
                elif ch == closer:
                    depth -= 1
                    if depth == 0:
                        candidate = text[start:i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break
            start = text.find(opener, start + 1)
    return None
