import json
import os
import requests
import psycopg2
from pathlib import Path
from datetime import datetime

def summarize_with_gemini(text, prompt, api_key):
   
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
        raise FileNotFoundError("RSS output file not found (toi_rss_output.json)")

    #  Connect to PostgreSQL
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Ensure table & unique constraint exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_summaries (
            id SERIAL PRIMARY KEY,
            category TEXT,
            title TEXT,
            link TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()

    #  Add UNIQUE constraint if missing (self-healing)
    try:
        cur.execute("ALTER TABLE news_summaries ADD CONSTRAINT unique_link UNIQUE (link);")
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
    except psycopg2.errors.DuplicateObject:
        conn.rollback()
    except Exception:
        conn.rollback()

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    summaries = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summaries.append(f"\n Gemini 2.0 Flash Lite | {timestamp}\n{'='*60}\n")

    new_summaries = 0

    for category, content in data["data"].items():
        articles = content.get("articles", [])
        if not articles:
            continue

        summaries.append(f"\n###  {category.upper()} NEWS ###\n")

        for article in articles:
            title = article.get("title", "")
            link = article.get("link", "")

            #  Skip if already summarized
            cur.execute("SELECT summary FROM news_summaries WHERE link = %s", (link,))
            existing = cur.fetchone()
            if existing:
                continue

            #  Summarize new article
            print(f"✨ Summarizing new article: '{title}'...")
            article_text = f"Title: {title}\nLink: {link}\n"
            summary = summarize_with_gemini(article_text, prompt, api_key)

            cur.execute("""
                INSERT INTO news_summaries (category, title, link, summary)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (link) DO NOTHING;
            """, (category, title, link, summary))
            conn.commit()

            new_summaries += 1
            summaries.append(f"- ( New) {title}\n{summary}\n")

    #  Fetch ALL processed links (old + new) from DB for JSON output
    cur.execute("SELECT category, title, link FROM news_summaries ORDER BY created_at DESC;")
    all_rows = cur.fetchall()
    all_processed = [{"category": r[0], "title": r[1], "link": r[2]} for r in all_rows]

    # Close DB connection
    cur.close()
    conn.close()

    #  Output setup
    output_dir = Path("/kestra/output")
    if not output_dir.exists():
        output_dir = Path(".")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write summary file (new)
    output_summary = output_dir / "summary.txt"
    with open(output_summary, "w", encoding="utf-8") as f:
        f.write("\n".join(summaries))

    # Write all processed (from DB)
    all_links_file = output_dir / "all_processed_links.json"
    with open(all_links_file, "w", encoding="utf-8") as f:
        json.dump(all_processed, f, indent=2, ensure_ascii=False)

    print(f"\n Summary written to {output_summary}")
    print(f" All processed links saved to {all_links_file}")
    print(f" {new_summaries} new articles added, total {len(all_processed)} stored in DB.")


if __name__ == "__main__":
    main()
