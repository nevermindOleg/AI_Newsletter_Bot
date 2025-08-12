# AI Newsletter Bot

This project is an automated AI-powered newsletter generator. It performs the following steps:

1.  **Collects:** Fetches the latest news and articles about Artificial Intelligence from the web using the Tavily Search API.
2.  **Processes:** Uses Azure OpenAI Service (GPT models) to score, rank, and summarize the collected articles, generating engaging headlines and insights.
3.  **Delivers:** Formats the processed content into a clean HTML email and sends it to a recipient list using the Resend API.

The entire process is designed to be run automatically on a schedule (e.g., daily), providing a curated AI news digest with minimal human intervention.

## Features

- **Modular Architecture:** Code is separated into logical components for collection, processing, and delivery.
- **Azure OpenAI Integration:** Leverages the power and reliability of Azure for AI processing.
- **High-Quality Content:** Advanced prompt engineering generates rewritten headlines, summaries, and key takeaways.
- **Efficient Scheduling:** Designed to be run via `cron` to minimize resource usage.
- **Test Mode:** Includes a `--test` flag to run the full pipeline without sending an email, printing a preview to the console instead.

## Project Structure

```
/
├── .gitignore              # Files to ignore for Git
├── .env                    # Your private API keys (create this file)
├── .env.example            # A template for the .env file
├── README.md               # This file
├── requirements.txt        # Python dependencies
└── src/
    ├── __init__.py
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

Create a `.env` file in the root of the project by copying the example template.

```bash
cp .env.example .env
```

Now, open the `.env` file with a text editor and fill in your actual API keys and configuration details.

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

## Automated Scheduling with Cron

For fully automated daily newsletters, use a cron job. This is the most resource-efficient method.

1.  Open your crontab editor:
    ```bash
    crontab -e
    ```

2.  Add a line to schedule the script. This example runs the script every day at 8:00 AM. Make sure to use the **absolute paths** to your Python interpreter and script.

    ```cron
    # Minute Hour Day Month DayOfWeek Command
    0 8 * * * /path/to/your/venv/bin/python /path/to/your/AI_Newsletter_Bot/src/main.py --once >> /path/to/your/AI_Newsletter_Bot/cron.log 2>&1
    ```

    - `>> /path/to/your/AI_Newsletter_Bot/cron.log 2>&1` is highly recommended as it logs all output and errors from the script, which is essential for debugging.
