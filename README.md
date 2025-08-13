# AI Newsletter Bot

This project is an automated AI-powered newsletter generator. It performs the following steps:

1.  **Collects:** Fetches the latest news and articles about Artificial Intelligence from the web using the Tavily Search API.
2.  **Processes:** Uses Azure OpenAI Service (GPT models) to score, rank, and summarize the collected articles, generating engaging headlines and insights.
3.  **Delivers:** Formats the processed content into a clean HTML email and sends it to a recipient list using the Resend API.

The entire process is designed to be run automatically on a schedule (e.g., daily), providing a curated AI news digest with minimal human intervention.

## Features

- **Centralized Configuration:** Clean config management with validation and defaults
- **Modular Architecture:** Code is separated into logical components for collection, processing, and delivery
- **Azure OpenAI Integration:** Leverages the power and reliability of Azure for AI processing
- **Multiple Recipients:** Support for sending to multiple email addresses
- **Template-based HTML:** Clean separation of HTML templates from code
- **High-Quality Content:** Advanced prompt engineering generates rewritten headlines, summaries, and key takeaways
- **Efficient Scheduling:** Designed to be run via `cron` to minimize resource usage
- **Test Mode:** Includes a `--test` flag to run the full pipeline without sending an email, printing a preview to the console instead

## Recent Enhancements

The following enhancements and features have been implemented:

-   **Enhanced News Collection Strategy:** The `TavilyCollector` was refactored to employ a dual search approach, ensuring more comprehensive news gathering:
    *   **Self-reported News:** Targeted searches are now performed using Tavily's `include_domains` parameter, directly fetching articles from specified `trusted_news_domains` (e.g., official company blogs). This ensures efficient and precise collection of direct announcements.
    *   **Third-party Coverage:** A separate, broader search is conducted using `topic="news"` to gather general AI news from a wider array of sources. This captures industry trends and analyses that might not originate from the trusted domain list.
-   **Improved Data Handling:** Article processing now includes robust handling for `raw_content`, ensuring content is always correctly processed as a string.
-   **Improved Configuration Loading:** The system now ensures that default values for `trusted_news_domains` are correctly loaded when the environment variable is not set, enhancing configuration stability.
-   **Adjusted Search Scope:** The third-party news search `time_range` was adjusted to focus on the last 1 day, providing more current results.

## Project Structure

```
/
├── .gitignore              # Files to ignore for Git
├── .env                    # Your private API keys (create this file)
├── .env.example            # A template for the .env file
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── templates/
│   └── newsletter.html     # Email HTML template
└── src/
    ├── __init__.py
    ├── config.py           # Centralized configuration management
    ├── bot.py              # Core logic classes
    └── main.py             # Main execution script
```

## Setup and Installation

### 1. Prerequisites

- Python 3.8+
- API keys for:
    - [Tavily AI](https://tavily.com/)
    - [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
    - [Resend](https://resend.com/)

### 2. Clone the Repository

```bash
git clone <repository-url>
cd AI_Newsletter_Bot
```

### 3. Install Dependencies

Create a virtual environment (recommended) and install the required libraries.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure Environment Variables

For local development, you can create a `.env` file in the root of the project by copying the template.

```bash
cp .env.example .env
```

Now, open the `.env` file and fill in your configuration. The `RECIPIENT_EMAILS` variable can be a single email or a comma-separated list of emails.

**Configuration Details:**

**Required Variables (must be set):**
- `TAVILY_API_KEY` - Your Tavily search API key
- `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_KEY` - Your Azure OpenAI API key
- `RESEND_API_KEY` - Your Resend email API key
- `FROM_EMAIL` - Sender email (must be verified with Resend)
- `RECIPIENT_EMAILS` - Comma-separated list of recipient emails

**Optional Variables (have defaults):**
- `AZURE_OPENAI_DEPLOYMENT_NAME` (default: `gpt-5-nano`)
- `AZURE_OPENAI_API_VERSION` (default: `2024-12-01-preview`)
- `AI_INTERESTS` (default: `Large Language Models, AI agents, AI tools, machine learning breakthroughs`)
- `TARGET_AUDIENCE` (default: `tech professionals and AI enthusiasts`)
- `NEWSLETTER_NAME` (default: `AI Daily Brief`)

The script will fail if any required variables are missing, but optional ones will use sensible defaults for quick testing.

## How to Run

Make sure your virtual environment is activated (`source venv/bin/activate`).

### Manual Run (for a single newsletter)

To run the full process once and send an email, use the `--once` flag:

```bash
python3 src/main.py --once
```

### Test Run (Dry Run)

To run the collection and processing steps without sending an email, use the `--test` flag. This will print a preview of the newsletter to your terminal.

```bash
python3 src/main.py --test
```

## Automation

This project is designed to be automated. The recommended method is using GitHub Actions, but a traditional cron job can also be used if you prefer to self-host.

### Method 1: GitHub Actions (Recommended)

This repository contains a workflow file at `.github/workflows/newsletter.yml` that will automatically run your script on a schedule.

**How it Works:**

1.  **Schedule:** The action is scheduled to run daily at 08:00 UTC. You can change this by editing the `cron` schedule in the `newsletter.yml` file.
2.  **Manual Trigger:** You can also run the workflow manually by going to the "Actions" tab in your GitHub repository, selecting "Send Daily AI Newsletter", and clicking "Run workflow".
3.  **Secrets:** The workflow **requires** you to store your API keys and configuration in your repository's secrets. Go to `Settings` > `Secrets and variables` > `Actions` and add all the variables from the `.env.example` file. The script will not work until you do this.

### Method 2: Cron Job (Self-hosted Alternative)

If you are running this on your own server, you can use a cron job for scheduling.

1.  Open your crontab editor:
    ```bash
    crontab -e
    ```

2.  Add a line to schedule the script. This example runs it every day at 8:00 AM. Make sure to use the **absolute paths** to your Python interpreter and script.

    ```cron
    # Minute Hour Day Month DayOfWeek Command
    0 8 * * * /path/to/your/venv/bin/python /path/to/your/AI_Newsletter_Bot/src/main.py --once >> /path/to/your/AI_Newsletter_Bot/cron.log 2>&1
    ```

    - Logging the output (`>> ... 2>&1`) is crucial for debugging.
