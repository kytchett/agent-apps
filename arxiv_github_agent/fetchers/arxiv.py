"""arXiv fetcher using `arxiv` package."""

from typing import List, Dict
import arxiv
import re
import collections
import string
import requests
import tempfile
import os
from typing import Optional


_STOPWORDS = {
    # small english stopword set to avoid extra deps
    "the",
    "and",
    "of",
    "in",
    "to",
    "a",
    "is",
    "for",
    "we",
    "that",
    "this",
    "with",
    "on",
    "as",
    "are",
    "by",
    "an",
    "be",
    "from",
    "which",
}


def _split_sentences(text: str) -> List[str]:
    # simple sentence splitter, avoids adding heavy NLP deps
    # split on ., ?, ! followed by whitespace and capitalize or digit
    parts = re.split(r'(?<=[\.\?\!])\s+', text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    return parts


def _summarize_text(text: str, max_sentences: int = 2) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return ""
    return " ".join(sentences[:max_sentences])


def _download_pdf(pdf_url: str) -> Optional[str]:
    try:
        r = requests.get(pdf_url, timeout=20)
        r.raise_for_status()
    except Exception:
        return None
    try:
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tf.write(r.content)
        tf.flush()
        tf.close()
        return tf.name
    except Exception:
        return None


def _extract_text_from_pdf(path: str) -> Optional[str]:
    # pdfminer is optional dependency; if not present, return None
    try:
        from pdfminer.high_level import extract_text
    except Exception:
        return None
    try:
        text = extract_text(path)
        return text
    except Exception:
        return None
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


def _extract_introduction_from_text(text: str, max_sentences: int = 3) -> Optional[str]:
    if not text:
        return None
    # look for common section headers
    # normalize line endings
    txt = text
    # try to find "Introduction" header
    patterns = [r"\n\s*Introduction\s*\n", r"\n\s*1\.?\s+Introduction\s*\n", r"\n\s*I\.\s*Introduction\s*\n"]
    for pat in patterns:
        m = re.search(pat, txt, flags=re.IGNORECASE)
        if m:
            start = m.end()
            snippet = txt[start:start + 8000]  # take up to first chunk
            # split into sentences and take top N
            sents = _split_sentences(snippet)
            if sents:
                return " ".join(sents[:max_sentences])
    # fallback: take beginning of document
    sents = _split_sentences(txt)
    if sents:
        return " ".join(sents[:max_sentences])
    return None


def _extract_contributions(text: str, max_sentences: int = 2) -> Optional[str]:
    """Heuristic: find sentences that state contributions/novelty.

    Looks for common phrases like 'we propose', 'our contributions', 'in this paper we', etc.
    """
    if not text:
        return None
    sents = _split_sentences(text)
    cues = [
        r"we (propose|present|introduce|develop|design|show|propose a|propose an)",
        r"our (contribution|contributions)",
        r"in this paper",
        r"the main contributions",
        r"we (demonstrate|evaluate|validate)",
        r"to the best of our knowledge",
    ]
    selected = []
    for sent in sents:
        low = sent.lower()
        for cue in cues:
            if re.search(cue, low):
                selected.append(sent.strip())
                break
        if len(selected) >= max_sentences:
            break
    if selected:
        return " ".join(selected[:max_sentences])
    return None


def _extract_keywords(text: str, top_k: int = 5) -> List[str]:
    # very small TF-based keyword extractor
    cleaned = text.lower()
    # remove punctuation
    cleaned = cleaned.translate(str.maketrans(string.punctuation, ' ' * len(string.punctuation)))
    words = [w for w in cleaned.split() if len(w) > 2 and w not in _STOPWORDS]
    if not words:
        return []
    counter = collections.Counter(words)
    most = [w for w, _ in counter.most_common(top_k)]
    return most


def fetch_arxiv(max_results: int = 100, keywords: str = "", arxiv_id: Optional[str] = None) -> List[Dict]:
    """Fetch latest Computer Science (cs) papers from arXiv.

    If `keywords` provided, include in the query.
    Returns list of dicts with id, title, summary, authors, published, pdf_url.
    """
    results = []
    if arxiv_id:
        # use id_list search when specific id provided
        search = arxiv.Search(id_list=[arxiv_id])
    else:
        query = "cat:cs*"
        if keywords:
            # escape keywords minimally
            query = f"({keywords}) AND {query}"
        search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.SubmittedDate)

    for r in search.results():
        abstract = r.summary or ""

        # try to obtain introduction from PDF (best-effort). If fails, fall back to abstract
        intro = None
        pdf_url = getattr(r, "pdf_url", None)
        if pdf_url:
            pdf_path = _download_pdf(pdf_url)
            if pdf_path:
                fulltext = _extract_text_from_pdf(pdf_path)
                intro = _extract_introduction_from_text(fulltext, max_sentences=3) if fulltext else None

        if intro:
            short = _summarize_text(intro, max_sentences=2)
            keywords_extracted = _extract_keywords(intro, top_k=6)
        else:
            short = _summarize_text(abstract, max_sentences=2)
            keywords_extracted = _extract_keywords(abstract, top_k=6)

        item = {
            "id": r.get_short_id(),
            "title": r.title,
            "abstract": abstract,
            "introduction": intro,
            "summary_short": short,
            "keywords": keywords_extracted,
            "authors": [a.name for a in r.authors],
            "published": r.published.isoformat(),
            "pdf_url": r.pdf_url,
            "primary_category": r.primary_category,
        }
        results.append(item)
    return results
