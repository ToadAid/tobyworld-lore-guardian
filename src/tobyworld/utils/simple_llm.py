from __future__ import annotations
import os,json,httpx
from tobyworld.agentic_rag.base import LLM

class HTTPLLM(LLM):
    def __init__(self, endpoint=None, model=None, apikey=None):
        self.endpoint=endpoint or os.getenv("LMSTUDIO_ENDPOINT","http://127.0.0.1:1234/v1/chat/completions")
        self.model=model or os.getenv("LMSTUDIO_MODEL","Meta-Llama-3-8B-Instruct-Q4_K_M")
        self.apikey=apikey or os.getenv("LMSTUDIO_API_KEY","")
    def complete(self,prompt,max_tokens=512,temperature=0.2)->str:
        payload={"model":self.model,"messages":[{"role":"user","content":prompt}],
                 "temperature":temperature,"max_tokens":max_tokens}
        headers={"Content-Type":"application/json"}
        if self.apikey: headers["Authorization"]=f"Bearer {self.apikey}"
        try:
            with httpx.Client(timeout=25.0) as client:
                r=client.post(self.endpoint,headers=headers,data=json.dumps(payload)); r.raise_for_status()
                return r.json().get("choices",[{}])[0].get("message",{}).get("content","").strip()
        except Exception as e: return f"[LLM error: {e}]"
