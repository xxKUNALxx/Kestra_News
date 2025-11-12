import feedparser
import json
import os
import requests
import subprocess
import random
from datetime import datetime
from pathlib import Path

def main():
    categories_env = os.getenv("CATEGORIES", "world,technology")
    categories = [c.strip().lower() for c in categories_env.split(",") if c.strip()]

    RSS_MAP = {
        "top": "rssfeedstopstories",
        "india": "-2128936835",
        "world": "296589292",
        "business": "1898055",
        "sports": "4719148",
        "technology": "66949542",
        "entertainment": "1081479906",
        "lifestyle": "2886704",
        "education": "913168846",
        "environment": "2647163",
        "science": "3908999",
    }

    base_url = "https://timesofindia.indiatimes.com/rssfeeds"
    data = {}
    timestamp = datetime.now().strftime("%d%m%Y.%H.%M.%S")
    headers = {"User-Agent": "Mozilla/5.0 (Kestra RSS Fetcher)"}

    print(f" Fetching TOI RSS feeds for: {categories}")

    #  Moved this loop INSIDE main()
    for cat in categories:
        feed_id = RSS_MAP.get(cat)
        if not feed_id:
            print(f" Unknown category '{cat}', skipping...")
            data[cat] = {"articles": [], "error": True, "message": "Invalid category"}
            continue

        url = f"{base_url}/{feed_id}.cms"
        print(f" Fetching: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            feed = feedparser.parse(response.text)

            if not feed.entries:
                print(f" No entries found in feed for '{cat}'")
                data[cat] = {"articles": [], "error": True, "message": "Empty feed"}
                continue

            #  Random 3 articles to save LLM tokens
            all_articles = [
                {
                    "title": entry.title,
                    "link": entry.link,
                    "published": getattr(entry, "published", None)
                }
                for entry in feed.entries
            ]
            selected_articles = random.sample(all_articles, min(2, len(all_articles)))

            print(f" Retrieved {len(all_articles)} total, selected {len(selected_articles)} for '{cat}'")
            data[cat] = {"articles": selected_articles, "error": False}

        except Exception as e:
            print(f" Error fetching {url}: {e}")
            data[cat] = {"articles": [], "error": True, "message": str(e)}

    #  ensure /kestra/output exists even if not mounted
    output_dir = Path("/kestra/output")
    if not output_dir.exists():
        print(" '/kestra/output' not found, creating local fallback directory.")
        output_dir = Path(".")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "toi_rss_output.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {"timestamp": timestamp, "data": data},
            f,
            indent=2,
            ensure_ascii=False
        )

    subprocess.run(["sync"], check=False)

    print("\n Files present in output directory:", os.listdir(output_dir))
    print(" RSS fetch completed successfully!")
    print(f"Output saved at: {output_path}")

#  Ensure the function is only executed when run directly
if __name__ == "__main__":
    main()
