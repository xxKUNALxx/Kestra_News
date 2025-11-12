# 📰 Kestra News Summarizer

An automated news aggregation and summarization workflow powered by **Kestra**, **Google Gemini 2.0 Flash Lite**, and **PostgreSQL**. This project fetches Times of India RSS feeds hourly, generates AI-powered summaries, and stores them in a database to avoid duplicate processing.

---

## 🚀 Features

- **Multi-Category RSS Fetching**: Supports 11 TOI categories (World, Technology, Business, Sports, etc.)
- **AI-Powered Summarization**: Uses Google Gemini 2.0 Flash Lite for intelligent article summaries
- **Smart Deduplication**: PostgreSQL tracks processed articles to prevent redundant summarization
- **Organized Output Structure**: Category-wise folders with timestamped files
- **Token Optimization**: Randomly selects 2 articles per category to reduce API costs
- **Customizable Prompts**: Configure your own summarization instructions
- **Automated Scheduling**: Runs every hour via Kestra triggers
- **Complete History Tracking**: `all_processed_links.json` maintains full article history from database
- **Dockerized Setup**: Complete containerized environment with PostgreSQL and Kestra

---

## 📋 Prerequisites

- **Docker** and **Docker Compose** installed
- **Google Gemini API Key** ([Get one here](https://aistudio.google.com/app/apikey))
- Basic understanding of Kestra workflows

---

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/xxKUNALxx/Kestra_News.git
cd Kestra_News
```

### 2. Start the Services

```bash
docker-compose up -d
```

This will start:
- **PostgreSQL** (port 5432) - Database for Kestra and news summaries
- **Kestra** (port 8080) - Workflow orchestration platform

### 3. Access Kestra UI

Open your browser and navigate to:
```
http://localhost:8080
```

### 4. Deploy the Workflow

1. In Kestra UI, go to **Flows** → **Create**
2. Copy the contents of `flows/FLOW.yaml`
3. Paste and save the flow
4. The flow will be available as `company.team.toi_news_summary`

---

## ⚙️ Configuration

### Environment Variables

The workflow accepts the following inputs:

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `categories` | STRING | Comma-separated TOI categories | `world,technology` |
| `gemini_api_key` | STRING | Your Google Gemini API key | **Required** |
| `prompt` | STRING | Custom summarization instruction | `Summarize these news articles in 3 short bullet points...` |

### Available Categories

```
top, india, world, business, sports, technology, 
entertainment, lifestyle, education, environment, science
```

---

## 🎯 Usage

### Manual Execution

1. Navigate to the flow in Kestra UI
2. Click **Execute**
3. Enter your **Gemini API Key**
4. (Optional) Customize categories and prompt
5. Click **Execute**

### Automated Execution

The workflow runs automatically **every hour** via the configured cron trigger:
```yaml
cron: "0 * * * *"
```

To modify the schedule, edit the `triggers` section in `FLOW.yaml`.

---

## 📂 Project Structure

```
Kestra_News/
├── docker-compose.yml          # Docker services configuration
├── flows/
│   └── FLOW.yaml              # Main Kestra workflow definition
├── scripts/
│   ├── fetch_feeds.py         # RSS feed fetcher
│   └── summarize_feeds.py     # Gemini summarization + DB storage
└── README.md                  # This file
```

---

## 🔄 Workflow Steps

1. **Start Log**: Records execution timestamp and parameters
2. **Fetch Feeds**: 
   - Retrieves RSS feeds from TOI for selected categories
   - Randomly selects 2 articles per category to optimize API usage
   - Outputs `toi_rss_output.json`
3. **Summarize Feeds**: 
   - Checks PostgreSQL for already-processed articles (deduplication)
   - Sends only new articles to Gemini API for summarization
   - Stores summaries in database with unique link constraint
   - Creates category-wise folders with timestamped files
   - Generates `all_processed_links.json` from complete DB history
4. **Show Summary**: Logs completion details and output locations

---

## 💾 Database Schema

The workflow automatically creates this table:

```sql
CREATE TABLE news_summaries (
    id SERIAL PRIMARY KEY,
    category TEXT,
    title TEXT,
    link TEXT UNIQUE,
    summary TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 📊 Output Files

Each execution generates organized output in category-wise folders:

```
output/
├── world/
│   ├── summary-13112025.14.30.45.txt    # Timestamped summaries
│   └── links-13112025.14.30.45.json     # Article links
├── technology/
│   ├── summary-13112025.14.30.45.txt
│   └── links-13112025.14.30.45.json
├── toi_rss_output.json                  # Raw RSS feed data
└── all_processed_links.json             # Complete history from DB
```

**File Descriptions:**
- `{category}/summary-{timestamp}.txt` - AI-generated summaries for each category
- `{category}/links-{timestamp}.json` - Article titles and URLs for each category
- `toi_rss_output.json` - Raw RSS feed data from TOI
- `all_processed_links.json` - Complete history of all processed articles from PostgreSQL


---

## 🐛 Troubleshooting

### Issue: "GEMINI_API_KEY environment variable missing"
**Solution**: Ensure you provide the API key when executing the flow.

### Issue: Database connection errors
**Solution**: Verify PostgreSQL is running:
```bash
docker ps | grep postgres
```

### Issue: No articles fetched
**Solution**: Check if the category names are valid (see Available Categories section).

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is open-source and available under the MIT License.

---

## 🙏 Acknowledgments

- **Kestra** - Workflow orchestration platform
- **Google Gemini** - AI summarization
- **Times of India** - News source

---

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Built with ❤️ using Kestra and Gemini AI**
