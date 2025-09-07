from tobyworld.agentic_rag.pipeline import AgenticRAGPipeline
from tobyworld.agentic_rag.multi_arc_retrieval import MultiArcRetriever, ArcConfig, LocalRetriever
from tobyworld.agentic_rag.reasoning_agent import ReasoningAgent
from tobyworld.agentic_rag.synthesis_agent import SynthesisAgent
from tobyworld.agentic_rag.base import QueryContext, DocBlob
from tobyworld.utils.simple_llm import HTTPLLM
from tobyworld.utils.scroll_loader import load_scroll_index
import os, pprint, time

def main():
    print("→ Loading scroll index…", flush=True)
    index = load_scroll_index()
    print(f"   loaded {len(index)} docs.")

    retriever = MultiArcRetriever(
        arcs={"lexical": ArcConfig(name="lexical", weight=1.0, k=12, enabled=True)},
        backends={"lexical": LocalRetriever(index)},
    )
    llm = HTTPLLM(
        endpoint=os.getenv("LMSTUDIO_ENDPOINT", "http://127.0.0.1:1234/v1/chat/completions"),
        model=os.getenv("LMSTUDIO_MODEL", "Meta-Llama-3-8B-Instruct-Q4_K_M"),
    )
    pipeline = AgenticRAGPipeline(
        retriever=retriever,
        reasoning=ReasoningAgent(llm),
        synthesis=SynthesisAgent(llm),
    )

    q = "Who is Toby in Tobyworld?"
    ctx = QueryContext(user_id="smoke", route_symbol="🪞", depth="normal")
    t0 = time.perf_counter()
    out = pipeline.run(q, ctx, k=8)
    dt = time.perf_counter() - t0

    print("\n— Agentic RAG SMOKE —")
    print(f"query      : {q}")
    print(f"latency    : {dt:.3f}s")
    print("used_refs  :", out.get("used_refs"))
    print("tone_score :", out.get("tone_score"))
    print("docs       :")
    for d in out.get("docs", []):
        print("  -", d["meta"].get("title"), " (score:", d["score"], ")")
    print("\nanswer:\n", out.get("answer"))

if __name__ == "__main__":
    main()
