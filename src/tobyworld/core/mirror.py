from .config import Config
from .guard import Guard
from .ledger import Ledger
from ..traits.resonance import Resonance
from ..traits.lucidity import Lucidity
from ..retrieval.retriever import Retriever
from ..retrieval.recovery import fallback
from ..knowledge.canonical import Canonical

class MirrorCore:
    def __init__(self, cfg: Config | None = None):
        self.cfg = cfg or Config()
        self.guard = Guard()
        self.ledger = Ledger()
        self.resonance = Resonance(self.cfg.decay_half_life_days)
        self.lucidity = Lucidity()
        self.canon = Canonical()
        self.retriever = Retriever()

    def ask(self, user: str, question: str) -> dict:
        q, flags = self.guard.sanitize_in(question)
        docs = self.retriever.retrieve(q, top_k=self.cfg.rag_top_k)
        ctx = "\n\n".join([d.get("chunk","") for d in docs]) if docs else ""
        answer = ctx or fallback(q)
        answer = self.guard.sanitize_out(answer)
        clarity = 1.0 if len(answer) > 40 else 0.5
        engagement = 1.0 if docs else 0.6
        lvl, meta = self.lucidity.adjust(engagement, clarity)
        self.ledger.log("ask", {"user":user, "flags":flags, "docs":len(docs), "lucidity":lvl})
        return {"answer":answer, "meta":{"lucidity":lvl,"docs_used":len(docs)}}
