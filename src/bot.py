#!/usr/bin/env python3
"""
AI Newsletter Bot - Core Logic
Contains classes for collecting, processing, and delivering AI news.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import List, Dict
from pathlib import Path

import httpx
from openai import AsyncAzureOpenAI
import resend
from dotenv import load_dotenv

from .config import NewsletterConfig

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class TavilyCollector:
    """Collects AI news using the Tavily Search API."""

    def __init__(self, trusted_news_domains: List[str] = None):
        self.api_key = os.getenv('TAVILY_API_KEY')
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set.")
        self.base_url = "https://api.tavily.com"
        self.interests = os.getenv('AI_INTERESTS', 'LLMs, AI agents, AI tools').split(',')
        self.trusted_news_domains = trusted_news_domains

    async def search_news(self) -> List[Dict]:
        """Fetches the latest AI news from Tavily based on interests."""
        queries = self._generate_queries()
        all_results = []

        async with httpx.AsyncClient(timeout=30) as client:
            tasks = [self._fetch_for_query(client, query) for query in queries]
            results_list = await asyncio.gather(*tasks)
            for results in results_list:
                all_results.extend(results)

        # Filter by trusted domains if configured
        all_results = self._filter_by_domain(all_results)

        return self._deduplicate(all_results)

    async def _fetch_for_query(self, client: httpx.AsyncClient, query: str) -> List[Dict]:
        """Helper to fetch news for a single query."""
        try:
            response = await client.post(
                f"{self.base_url}/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "include_raw_content": True,
                    "max_results": 100,
                    "days": 1  # Last 24 hours
                }
            )
            response.raise_for_status()  # Raise an exception for bad status codes
            data = response.json()
            logger.info(f"Found {len(data.get('results', []))} articles for query: '{query}'")
            return data.get('results', [])
        except httpx.HTTPStatusError as e:
            logger.error(f"Tavily API error for query '{query}': {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Error fetching news for query '{query}': {e}")
        return []

    def _generate_queries(self) -> List[str]:
        """Generates a list of search queries based on user interests."""
        return [f"latest news on {interest.strip()}" for interest in self.interests]

    def _deduplicate(self, articles: List[Dict]) -> List[Dict]:
        """Removes duplicate articles based on URL."""
        seen_urls = set()
        unique_articles = []
        for article in articles:
            url = article.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
        logger.info(f"Deduplicated: {len(articles)} -> {len(unique_articles)} articles")
        return unique_articles

    def _filter_by_domain(self, articles: List[Dict]) -> List[Dict]:
        """Filters articles to include only those from trusted news domains."""
        if not self.trusted_news_domains:
            logger.info("No trusted news domains specified. Skipping domain filtering.")
            return articles

        filtered_articles = []
        for article in articles:
            url = article.get('url')
            if url:
                # Extract domain from URL and check against trusted domains
                import urllib.parse
                parsed_url = urllib.parse.urlparse(url)
                domain = parsed_url.netloc
                # Remove 'www.' prefix if present for consistent matching
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                if domain in self.trusted_news_domains:
                    filtered_articles.append(article)
                else:
                    logger.debug(f"Skipping article from untrusted domain: {domain} - {url}")
        logger.info(f"Filtered by domain: {len(articles)} -> {len(filtered_articles)} articles")
        return filtered_articles


class GPTProcessor:
    """Processes and ranks articles using Azure OpenAI Service."""

    def __init__(self):
        try:
            self.client = AsyncAzureOpenAI(
                api_version="2024-12-01-preview",  # Hardcoded API version
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            )
            # Hardcoded deployment and model name
            self.deployment_name = "gpt-5-mini"
        except Exception as e:
            raise ValueError(f"Azure OpenAI client initialization failed: {e}")

        # Use hardcoded defaults if environment variables are not set
        self.interests = os.getenv('AI_INTERESTS', 'Large Language Models, AI agents, AI tools, machine learning breakthroughs')
        self.audience = os.getenv('TARGET_AUDIENCE', 'tech professionals and AI enthusiasts')

    async def process_articles(self, articles: List[Dict], limit: int = 5) -> Dict:
        """Scores, ranks, and generates newsletter content from the top articles."""
        if not articles:
            return {}

        scored_articles = await self._score_articles(articles)
        top_articles = scored_articles[:limit]
        
        if not top_articles:
            logger.warning("No articles scored high enough to be included in the newsletter.")
            return {}

        newsletter_content = await self._generate_newsletter(top_articles)
        return newsletter_content

    async def _score_articles(self, articles: List[Dict]) -> List[Dict]:
        """Scores articles based on relevance, newsworthiness, and importance."""
        articles_text = [
            f"ID: {i}
Title: {article.get('title', 'N/A')}
Content: {article.get('raw_content', '')[:4000]}"
            for i, article in enumerate(articles)
        ]

        scoring_prompt = f"""
        You are an AI newsletter curator for an audience of {self.audience}.
        Your task is to score the following articles based on their relevance to these interests: {self.interests}.
        Consider newsworthiness (breakthroughs > updates), practical value, and source credibility.
        
        Articles to score:
        {chr(10).join(articles_text)}
        
        Return a JSON object containing a single key "scores" with a list of objects.
        Each object must have "id" (integer), "score" (float 0-10), and "reason" (string, 1 sentence).
        Be selective. Only truly noteworthy news should score above 7.
        Example: {{\"scores\": [{{\"id\": 0, \"score\": 8.5, \"reason\": \"Major LLM breakthrough from a credible source.\"}}]}}
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": scoring_prompt}],
                response_format={"type": "json_object"},
            )
            scores_data = json.loads(response.choices[0].message.content)
            scores = scores_data.get("scores", [])

            for score_info in scores:
                if isinstance(score_info, dict) and 'id' in score_info:
                    idx = score_info['id']
                    if 0 <= idx < len(articles):
                        articles[idx]['score'] = score_info.get('score', 0)
                        articles[idx]['reason'] = score_info.get('reason', '')
            
            articles.sort(key=lambda x: x.get('score', 0), reverse=True)
            return articles
        except Exception as e:
            logger.error(f"Error scoring articles with Azure OpenAI: {e}")
            return articles # Return unscored but still usable

    async def _generate_newsletter(self, articles: List[Dict]) -> Dict:
        """Generates the final newsletter content as a structured JSON object."""
        articles_formatted = [
            f"Title: {article.get('title')}\nURL: {article.get('url')}\nWhy selected: {article.get('reason', 'Important AI news')}"
            for article in articles
        ]

        newsletter_prompt = f"""
        You are a world-class newsletter editor for an audience of {self.audience}.
        Create an engaging AI newsletter for {datetime.now().strftime('%B %d, %Y')}.
        Use these top {len(articles)} articles:
        {chr(10).join(articles_formatted)}

        Your task is to generate the newsletter in a specific JSON format.
        The JSON object must have these exact keys: "opening_hook", "top_stories", "tool_of_the_day", "closing_thought".
        
        - "opening_hook": A compelling 1-2 sentence intro about today's AI landscape.
        - "top_stories": A JSON array. For each article, create an object with "headline" (rewritten, engaging), "summary" (2-3 sentences focusing on what and why it matters), and "link" (the original URL).
        - "tool_of_the_day": A string recommending one practical AI tool or resource (can be from the articles or general knowledge).
        - "closing_thought": A forward-looking insight or question to ponder.

        Keep the tone professional yet conversational. Focus on practical implications.
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": newsletter_prompt}],
                response_format={"type": "json_object"},
            )
            newsletter_data = json.loads(response.choices[0].message.content)
            # Attach original articles for reference in the emailer
            newsletter_data['original_articles'] = articles
            return newsletter_data
        except Exception as e:
            logger.error(f"Error generating newsletter content with Azure OpenAI: {e}")
            return {}


class ResendEmailer:
    """Sends the newsletter via the Resend API."""

    def __init__(self):
        resend.api_key = os.getenv('RESEND_API_KEY')
        if not resend.api_key:
            raise ValueError("RESEND_API_KEY environment variable not set.")
        
        self.from_email = os.getenv('FROM_EMAIL')
        # Get recipient emails, split by comma, and strip whitespace
        recipients_str = os.getenv('RECIPIENT_EMAILS') or os.getenv('RECIPIENT_EMAIL', '')
        self.to_emails = [email.strip() for email in recipients_str.split(',') if email.strip()]
        
        self.newsletter_name = os.getenv('NEWSLETTER_NAME', 'AI Daily Brief')

    async def send_newsletter(self, newsletter_data: Dict) -> bool:
        """Constructs and sends the newsletter email."""
        if not self.from_email or not self.to_emails:
            logger.error("FROM_EMAIL or RECIPIENT_EMAILS environment variables not set or empty.")
            return False
        if not newsletter_data or 'top_stories' not in newsletter_data:
            logger.warning("No newsletter data to send.")
            return False

        subject = f"{self.newsletter_name} - {datetime.now().strftime('%B %d, %Y')}"
        html_content = self._generate_html(newsletter_data)
        text_content = self._generate_text_version(newsletter_data)

        try:
            response = resend.Emails.send({
                "from": self.from_email,
                "to": self.to_emails, # Pass the list of recipients
                "subject": subject,
                "html": html_content,
                "text": text_content,
            })
            logger.info(f"Newsletter sent successfully! Message ID: {response.get('id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to send newsletter via Resend: {e}")
            return False

    def _generate_html(self, data: Dict) -> str:
        """Generates HTML email content from template."""
        stories_html = ""
        for story in data.get('top_stories', []):
            stories_html += f"""
            <div class="article">
                <h3>{story.get('headline', 'Untitled')}</h3>
                <p class="summary">{story.get('summary', 'No summary available.')}</p>
                <a href="{story.get('link', '#')}" class="read-more">Read the full story →</a>
            </div>
            """

        # Load and render template
        template_path = PROJECT_ROOT / "templates" / "newsletter.html"
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            return template.format(
                newsletter_name=self.newsletter_name,
                current_date=datetime.now().strftime('%A, %B %d, %Y'),
                opening_hook=data.get('opening_hook', 'Here is your daily AI briefing.'),
                stories_html=stories_html,
                tool_of_the_day=data.get('tool_of_the_day', 'Explore new AI tools to boost your productivity.'),
                closing_thought=data.get('closing_thought', 'The field of AI continues to evolve at a breathtaking pace. Stay curious!')
            )
        except FileNotFoundError:
            logger.error(f"Template not found: {template_path}")
            return "Template not found. Please check your installation."
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return "Error rendering newsletter template."

    def _generate_text_version(self, data: Dict) -> str:
        """Generates a plain text version of the email."""
        text = f"{self.newsletter_name}\n{datetime.now().strftime('%A, %B %d, %Y')}\n\n"
        text += f"{data.get('opening_hook', 'Here is your daily AI briefing.')}\n\n"
        text += "--- TOP STORIES ---\n\n"
        for story in data.get('top_stories', []):
            text += f"Headline: {story.get('headline', 'Untitled')}\n"
            text += f"Summary: {story.get('summary', 'N/A')}\n"
            text += f"Link: {story.get('link', '#')}\n\n"
        text += f"--- TOOL OF THE DAY ---\n{data.get('tool_of_the_day', 'N/A')}\n\n"
        text += f"--- CLOSING THOUGHT ---\n{data.get('closing_thought', 'N/A')}\n"
        return text


class AINewsletterBot:
    """Main orchestrator for the newsletter bot."""

    def __init__(self, config: NewsletterConfig = None):
        self.config = config or NewsletterConfig.from_env()
        self.collector = TavilyCollector(trusted_news_domains=self.config.trusted_news_domains)
        self.processor = GPTProcessor()
        self.emailer = ResendEmailer()

    async def run_newsletter(self):
        """Runs the full pipeline to generate and send the newsletter."""
        logger.info("🚀 Starting newsletter generation pipeline...")
        try:
            articles = await self.collector.search_news()
            if not articles:
                logger.warning("No articles found. Stopping pipeline.")
                return False

            newsletter_data = await self.processor.process_articles(articles, limit=5)
            if not newsletter_data:
                logger.warning("Processing failed to produce newsletter content. Stopping pipeline.")
                return False

            success = await self.emailer.send_newsletter(newsletter_data)
            if success:
                logger.info("✅ Newsletter pipeline completed successfully!")
            else:
                logger.error("❌ Newsletter pipeline failed during email sending.")
            return success
        except Exception as e:
            logger.critical(f"An unexpected error occurred in the main pipeline: {e}", exc_info=True)
            return False

    async def test_run(self):
        """Runs the pipeline without sending an email, printing a preview instead."""
        logger.info("🧪 Running in TEST mode...")
        articles = await self.collector.search_news()
        if not articles:
            logger.warning("No articles found. Test run cannot proceed.")
            return

        newsletter_data = await self.processor.process_articles(articles, limit=5)
        if not newsletter_data:
            logger.warning("Processing failed to produce newsletter content.")
            return
            
        print("\n" + "="*50)
        print("✉️  NEWSLETTER PREVIEW ✉️")
        print("="*50 + "\n")
        print(f"SUBJECT: {self.emailer.newsletter_name} - {datetime.now().strftime('%B %d, %Y')}\n")
        print(f"OPENING: {newsletter_data.get('opening_hook')}\n")
        for i, story in enumerate(newsletter_data.get('top_stories', []), 1):
            print(f"--- STORY {i} ---")
            print(f"HEADLINE: {story.get('headline')}")
            print(f"SUMMARY: {story.get('summary')}")
            print(f"LINK: {story.get('link')}\n")
        print("--- TOOL OF THE DAY ---")
        print(f"{newsletter_data.get('tool_of_the_day')}\n")
        print("--- CLOSING THOUGHT ---")
        print(f"{newsletter_data.get('closing_thought')}\n")
        print("="*50)
        print("Test run complete. No email was sent.")
        print("="*50 + "\n")