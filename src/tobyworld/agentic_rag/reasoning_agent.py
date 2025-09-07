from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
from .base import QueryContext, DocBlob, Circuit, LLM

@dataclass
class Thought:
    question: str
    hypothesis: Optional[str] = None
    evidence_ids: List[str] = None

class ReasoningAgent:
    def __init__(self, llm: LLM, circuit: Optional[Circuit]=None):
        self.llm=llm; self.circuit=circuit or Circuit(max_steps=3)
    def analyze(self, query:str, ctx:QueryContext, top_docs:List[DocBlob])->Tuple[List[Thought],str]:
        doc_summ="\\n".join(f"[{i+1}] {d.text[:280]}" for i,d in enumerate(top_docs))
        prompt=f'''You are a concise research planner. User asked: "{query}"
Snippets:\\n{doc_summ}\\n
1) List ≤2 missing sub-questions.
2) Predict refined query (≤20 words).
Return JSON: {{"subs":["..."],"refined":"..."}}'''
        raw=self.llm.complete(prompt,max_tokens=220,temperature=0.0)
        import json,re
        try:
            js=json.loads(re.search(r"\\{.*\\}",raw,re.S).group(0))
            subs=js.get("subs",[])[:2]; refined=js.get("refined",query) or query
        except Exception: subs=[]; refined=query
        return [Thought(q) for q in subs], refined
