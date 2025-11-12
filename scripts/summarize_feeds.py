import json
import os
import requests
import psycopg2
from pathlib import Path
from datetime import datetime

def summarize_with_gemini(text, prompt, api_key):
    """Send text and custom prompt to Gemini 2.0 Flash Lite."""
    model = "gemini-2.0-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Content-Type": "application/json"}
    body = {"contents": [{"parts": [{"text": f"{prompt}\n\n{text}"}]}]}

    try:
        response = requests.post(f"{url}?key={api_key}", headers=headers, json=body, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f" Gemini summarization failed: {e}"

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    prompt = os.getenv("CUSTOM_PROMPT", "Summarize briefly and clearly.")
    db_url = os.getenv("DATABASE_URL", "postgresql://kestra:k3str4@host.docker.internal:5432/kestra")

    if not api_key:
        raise ValueError(" GEMINI_API_KEY environment variable missing")

    input_path = Path("toi_rss_output.json")
    if not input_path.exists():
        raise FileNotFoundError(" RSS output file not found (toi_rss_output.json)")

    # Connect to PostgreSQL
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_summaries (
            id SERIAL PRIMARY KEY,
            category TEXT,
            title TEXT,
            link TEXT UNIQUE,
            summary TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    timestamp = datetime.now().strftime("%d%m%Y.%H.%M.%S")
    output_root = Path("/kestra/output")
    if not output_root.exists():
        output_root = Path(".")
    output_root.mkdir(parents=True, exist_ok=True)

    total_new = 0

    for category, content in data["data"].items():
        articles = content.get("articles", [])
        if not articles:
            continue

        print(f"\n Processing category: {category}")
        category_dir = output_root / category
        category_dir.mkdir(parents=True, exist_ok=True)

        summary_file = category_dir / f"summary-{timestamp}.txt"
        links_file = category_dir / f"links-{timestamp}.json"

        summaries = []
        processed_links = []

        for article in articles:
            title = article.get("title", "")
            link = article.get("link", "")

            cur.execute("SELECT summary FROM news_summaries WHERE link = %s", (link,))
            existing = cur.fetchone()
            if existing:
                continue

            print(f" Summarizing: {title}")
            text = f"Title: {title}\nLink: {link}\n"
            summary = summarize_with_gemini(text, prompt, api_key)

            cur.execute("""
                INSERT INTO news_summaries (category, title, link, summary)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (link) DO NOTHING;
            """, (category, title, link, summary))
            conn.commit()

            summaries.append(f" {title}\n{summary}\n{'-'*60}\n")
            processed_links.append({"title": title, "link": link})
            total_new += 1

        #  Write category files
        if summaries:
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write("\n".join(summaries))
            with open(links_file, "w", encoding="utf-8") as f:
                json.dump(processed_links, f, indent=2, ensure_ascii=False)

            print(f" Saved {category} summaries and links.")

    #  Now fetch ALL articles ever processed from PostgreSQL
    cur.execute("SELECT category, title, link FROM news_summaries ORDER BY created_at DESC;")
    all_rows = cur.fetchall()
    all_processed = [{"category": r[0], "title": r[1], "link": r[2]} for r in all_rows]

    # Save global “all_processed_links.json”
    all_links_file = output_root / "all_processed_links.json"
    with open(all_links_file, "w", encoding="utf-8") as f:
        json.dump(all_processed, f, indent=2, ensure_ascii=False)

    print(f"\n All processed links saved to {all_links_file}")
    print(f" {total_new} new articles added, total {len(all_processed)} in DB.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
