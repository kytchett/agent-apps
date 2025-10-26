#!/usr/bin/env python3
"""Agent entrypoint: fetch arXiv CS papers and GitHub top repos."""
import argparse
import time
from datetime import datetime
from dotenv import load_dotenv
import os

from fetchers.arxiv import fetch_arxiv
from fetchers.github import fetch_github
from utils.output import save_json
from ai_agent import Agent

load_dotenv()


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true", help="Run one fetch cycle and exit")
    p.add_argument("--interval", type=int, default=0, help="Polling interval in seconds (0 means no loop)")

    p.add_argument("--arxiv-max", type=int, default=100, help="Max number of arXiv results")
    p.add_argument("--arxiv-keywords", type=str, default="", help="Keywords for arXiv search")
    p.add_argument("--arxiv-id", type=str, default="", help="Specific arXiv id to summarize (e.g. 2301.01234)")
    p.add_argument("--use-llm", action="store_true", help="Use OpenAI LLM for improved summaries (requires OPENAI_API_KEY)")

    p.add_argument("--github-max", type=int, default=100, help="Max number of GitHub repos to fetch")
    p.add_argument("--github-keywords", type=str, default="", help="Keywords for GitHub search")
    p.add_argument("--github-language", type=str, default="", help="Filter GitHub by language")

    return p.parse_args()


def run_cycle(args):
    now = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    print(f"[{now}] Running AI agent (fetch + summarize) ...")
    agent = Agent(use_llm=args.use_llm)

    if args.arxiv_id:
        print(f"Fetching single arXiv id: {args.arxiv_id}")
        items = fetch_arxiv(max_results=1, keywords=args.arxiv_keywords, arxiv_id=args.arxiv_id)
        summarized = [agent.summarize_arxiv_item(i) for i in items]
        arxiv_path = save_json(summarized, f"{now}_arxiv_single_{args.arxiv_id}.json")
        print(f"Saved single arXiv summary to {arxiv_path}")
        return

    out = agent.fetch_and_summarize(
        arxiv_max=args.arxiv_max,
        arxiv_keywords=args.arxiv_keywords,
        github_max=args.github_max,
        github_keywords=args.github_keywords,
        github_language=args.github_language,
    )

    arxiv_path = save_json(out.get("arxiv", []), f"{now}_arxiv.json")
    github_path = save_json(out.get("github", []), f"{now}_github.json")
    meta_path = save_json(out.get("meta", {}), f"{now}_meta.json")

    print(f"Saved arXiv to {arxiv_path} ({out.get('meta', {}).get('arxiv_count', 0)} items)")
    print(f"Saved GitHub to {github_path} ({out.get('meta', {}).get('github_count', 0)} items)")
    print(f"Saved meta to {meta_path}")


def main():
    args = parse_args()

    if args.once or args.interval == 0:
        run_cycle(args)
        return

    print(f"Starting polling every {args.interval}s. Press Ctrl+C to stop.")
    try:
        while True:
            run_cycle(args)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Stopped by user")


if __name__ == "__main__":
    main()
