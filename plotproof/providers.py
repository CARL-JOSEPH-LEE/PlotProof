"""Small, explicit adapters for local Ollama and Chat Completions endpoints."""

import ipaddress
import json
import socket
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_RESPONSE = 2_000_000


class ProviderError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward a credential to a redirected origin.
        return None


@dataclass
class Settings:
    provider: str = "rules"
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    language: str = "zh"
    timeout: int = 120

    def validate(self):
        if self.provider not in {"rules", "ollama", "compatible"}:
            raise ValueError("Unsupported provider.")
        if self.language not in {"zh", "en"}:
            raise ValueError("Unsupported report language.")
        if self.provider == "rules":
            return self
        if not isinstance(self.model, str) or not self.model.strip() or len(self.model) > 200:
            raise ValueError("请填写模型名称 / Enter a model name.")
        if not isinstance(self.api_key, str) or any(c in self.api_key for c in "\r\n"):
            raise ValueError("Invalid API key.")
        if not isinstance(self.base_url, str):
            raise ValueError("Invalid base URL.")
        url = urlsplit(self.base_url)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("请填写不含密钥、查询参数的 HTTP(S) 接口地址 / Invalid base URL.")
        try:
            local = url.hostname == "localhost" or ipaddress.ip_address(url.hostname).is_loopback
        except ValueError:
            local = url.hostname == "localhost"
        if url.scheme == "http" and not local:
            raise ValueError("远程接口请使用 HTTPS；HTTP 仅支持本机 / Use HTTPS for remote providers.")
        try:
            url.port
        except ValueError as exc:
            raise ValueError("Invalid endpoint port.") from exc
        self.base_url = self.base_url.rstrip("/")
        if not 1 <= self.timeout <= 300:
            raise ValueError("Timeout must be between 1 and 300 seconds.")
        return self

    def public(self):
        return {
            "provider": self.provider,
            "model": self.model if self.provider != "rules" else "offline-rules-v1",
            "language": self.language,
        }


class Client:
    def __init__(self, settings: Settings):
        self.settings = settings.validate()
        self.requests = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def complete(self, system: str, payload: dict, schema: dict) -> dict:
        s = self.settings
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        body = {"model": s.model, "messages": messages, "stream": False}
        if s.provider == "ollama":
            url = s.base_url + ("/chat" if s.base_url.endswith("/api") else "/api/chat")
            body.update(
                {"format": schema, "options": {"temperature": 0, "num_predict": 6000, "num_ctx": 32768}}
            )
        else:
            url = s.base_url + ("" if s.base_url.endswith("/chat/completions") else "/chat/completions")
            body.update({"temperature": 0, "max_tokens": 6000, "response_format": {"type": "json_object"}})
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "PlotProof/0.1",
        }
        if s.api_key:
            headers["Authorization"] = "Bearer " + s.api_key
        request = Request(
            url, json.dumps(body, ensure_ascii=False).encode("utf-8"), headers=headers, method="POST"
        )
        self.requests += 1
        try:
            with build_opener(NoRedirect).open(request, timeout=s.timeout) as response:
                raw = response.read(MAX_RESPONSE + 1)
                if len(raw) > MAX_RESPONSE:
                    raise ProviderError("模型返回内容过大 / Model response too large.")
                outer = json.loads(raw)
        except HTTPError as exc:
            # Raw provider bodies can echo manuscripts or credentials.
            explanations = {
                401: "密钥无效 / Invalid API key",
                403: "访问被拒绝 / Access denied",
                404: "接口或模型不存在 / Endpoint or model not found",
                429: "请求限流或额度不足 / Rate limit or quota exceeded",
            }
            raise ProviderError(
                f"HTTP {exc.code}: {explanations.get(exc.code, '模型请求失败 / Provider request failed')}."
            ) from None
        except (URLError, TimeoutError, socket.timeout, OSError):
            raise ProviderError(
                "无法连接模型或请求超时，请检查服务和地址 / Provider unavailable or timed out."
            ) from None
        except (ValueError, UnicodeError):
            raise ProviderError("接口未返回有效 JSON / Provider returned invalid JSON.") from None
        try:
            if s.provider == "ollama":
                if outer.get("done") is False or outer.get("done_reason") == "length":
                    raise ProviderError("模型输出被截断 / Model output was truncated.")
                content = outer["message"]["content"]
                self.input_tokens += int(outer.get("prompt_eval_count", 0) or 0)
                self.output_tokens += int(outer.get("eval_count", 0) or 0)
            else:
                choice = outer["choices"][0]
                if choice.get("finish_reason") not in {"stop", None}:
                    raise ProviderError("模型未完整返回结果 / Model did not finish its response.")
                content = choice["message"]["content"]
                usage = outer.get("usage", {}) or {}
                self.input_tokens += int(usage.get("prompt_tokens", 0) or 0)
                self.output_tokens += int(usage.get("completion_tokens", 0) or 0)
            if content.startswith("```json\n") and content.rstrip().endswith("```"):
                content = content.strip()[8:-3]
            value = json.loads(content)
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (KeyError, IndexError, TypeError, ValueError, AttributeError):
            raise ProviderError("模型返回格式不符合约定 / Invalid structured model response.") from None
