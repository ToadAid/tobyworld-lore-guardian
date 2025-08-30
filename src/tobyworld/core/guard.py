import re

SECRET = re.compile(r"(api[_-]?key|token|password)\s*[:=]\s*[\w\-]{8,}", re.I)

class Guard:
    def sanitize_in(self, text: str) -> tuple[str, dict]:
        flags = {}
        if SECRET.search(text):
            text = SECRET.sub(r"[REDACTED]", text)
            flags["secret_stripped"]=True
        return text.strip(), flags

    def sanitize_out(self, text: str) -> str:
        return text.strip()
