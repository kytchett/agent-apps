"""AI Agent coordinator: orchestrates fetchers and summarizes results.

Contract:
- Inputs: fetch parameters (max counts, keywords, language), use_llm flag
- Outputs: dict with 'arxiv' and 'github' lists; each item may include 'agent_summary'
- Error modes: if LLM unavailable or API key missing, falls back to local summary fields

"""
from typing import List, Dict, Any, Optional
import os
import time
import requests

from fetchers.arxiv import fetch_arxiv
from fetchers.github import fetch_github

try:
    import openai
    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False


class Agent:
    def __init__(self, use_llm: bool = False):
        # support a local chatbox API via LOCAL_CHATBOX_URL; if present prefer it.
        self.local_chatbox_url = os.getenv("LOCAL_CHATBOX_URL")
        self.local_chatbox_token = os.getenv("LOCAL_CHATBOX_TOKEN")
        self.use_local = bool(self.local_chatbox_url)

        self.use_openai = _HAS_OPENAI and bool(os.getenv("OPENAI_API_KEY"))

        # final flag: whether LLM capabilities were requested
        self.use_llm = use_llm and (self.use_local or self.use_openai)

        if use_llm and not self.use_llm:
            print("LLM requested but no local chatbox or OpenAI API key found; falling back to local summaries")

        if self.use_openai:
            openai.api_key = os.getenv("OPENAI_API_KEY")

    def _call_openai(self, prompt: str, max_tokens: int = 256) -> Optional[str]:
        if not self.use_llm:
            return None
        try:
            resp = openai.ChatCompletion.create(
                model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.2,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print("OpenAI call failed:", e)
            return None


    def _call_local_chatbox(self, prompt: str, max_tokens: int = 256) -> Optional[str]:
        if not self.use_local:
            return None
        url = self.local_chatbox_url
        headers = {"Content-Type": "application/json"}
        if self.local_chatbox_token:
            headers["Authorization"] = f"Bearer {self.local_chatbox_token}"
        # include a model field for local chatbox services that require it
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "model": os.getenv("LOCAL_CHATBOX_MODEL", os.getenv("OPENAI_MODEL", "qwen2.5:3b")),
        }
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            # try to parse JSON and extract a sensible text field
            try:
                data = r.json()
            except Exception:
                data = None

            if isinstance(data, dict):
                # common possible keys
                for key in ("response", "text", "result", "output", "reply"):
                    if key in data and isinstance(data[key], str):
                        return data[key].strip()
                if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
                    ch = data["choices"][0]
                    if isinstance(ch, dict):
                        for k in ("text", "message", "content"):
                            if k in ch and isinstance(ch[k], str):
                                return ch[k].strip()
            # fallback to raw text
            txt = r.text
            if isinstance(txt, str) and txt.strip():
                return txt.strip()
            return None
        except Exception as e:
            print("Local chatbox call failed:", e)
            return None


    def _call_llm(self, prompt: str, max_tokens: int = 256) -> Optional[str]:
        # prefer local chatbox if available, otherwise use OpenAI
        if self.use_local:
            out = self._call_local_chatbox(prompt, max_tokens=max_tokens)
            if out:
                return out
        if self.use_openai:
            return self._call_openai(prompt, max_tokens=max_tokens)
        return None

    def _build_prompt_for_arxiv(self, title: str, intro: Optional[str], abstract: str) -> str:
        text = intro or abstract or ""
        prompt = (
            "You are an assistant that summarizes academic papers.\n"
            "Given the paper title and its Introduction (or abstract if Introduction missing), produce a concise 2-3 sentence summary focused on: 1) the main contributions / innovations, and 2) a brief description of the methods/work.\n\n"
            f"Title: {title}\n\nIntroduction/Abstract:\n{text}\n\n"
            "Return only the summary text."
        )
        return prompt

    def summarize_arxiv_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        # item contains 'title', 'introduction' (maybe None), 'abstract', 'summary_short'
        summary = None
        if self.use_llm:
            prompt = self._build_prompt_for_arxiv(item.get("title", ""), item.get("introduction"), item.get("abstract", ""))
            summary = self._call_openai(prompt)

        if not summary:
            # fall back to existing short summary or introduction/contrib heuristics
            summary = item.get("summary_short") or (item.get("introduction") and (item.get("introduction")[:400])) or (item.get("abstract")[:400])

        out = dict(item)
        out["agent_summary"] = summary
        return out

    def summarize_github_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        summary = None
        if self.use_llm:
            prompt = (
                "Summarize this GitHub repository in 1-2 sentences focusing on its purpose and strengths.\n\n"
                f"Name: {item.get('full_name')}\nDescription: {item.get('description') or ''}\n"
            )
            summary = self._call_openai(prompt, max_tokens=120)

        if not summary:
            summary = (item.get("description") or "No description available")[:300]

        out = dict(item)
        out["agent_summary"] = summary
        return out

    def fetch_and_summarize(self, arxiv_max: int = 100, arxiv_keywords: str = "", github_max: int = 100, github_keywords: str = "", github_language: str = "") -> Dict[str, Any]:
        start = time.time()
        arxiv_items = fetch_arxiv(max_results=arxiv_max, keywords=arxiv_keywords)
        github_items = fetch_github(max_results=github_max, keywords=github_keywords, language=github_language)

        arxiv_out = [self.summarize_arxiv_item(i) for i in arxiv_items]
        github_out = [self.summarize_github_item(i) for i in github_items]

        return {
            "arxiv": arxiv_out,
            "github": github_out,
            "meta": {
                "arxiv_count": len(arxiv_out),
                "github_count": len(github_out),
                "elapsed": time.time() - start,
            },
        }
