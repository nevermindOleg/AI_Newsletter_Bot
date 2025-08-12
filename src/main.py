#!/usr/bin/env python3
"""
AI Newsletter Bot - Main Entry Point
"""

import asyncio
import sys
import os

# Add the src directory to the Python path
# This allows us to import from 'bot' even when running from the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot import AINewsletterBot
from src.config import NewsletterConfig

async def main():
    """
    Main execution function.
    Parses command-line arguments to decide whether to run a real newsletter,
    a test run, or show help.
    """
    try:
        config = NewsletterConfig.from_env()
        bot = AINewsletterBot(config)

        if '--once' in sys.argv:
            await bot.run_newsletter()
        elif '--test' in sys.argv:
            await bot.test_run()
        else:
            print("Usage: python src/main.py [--once | --test]")
            print("  --once: Run the full newsletter pipeline and send the email.")
            print("  --test: Run the pipeline but print a preview instead of sending an email.")
            sys.exit(1)
    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # This allows the script to be run from the command line.
    # For example: `python src/main.py --test`
    try:
        asyncio.run(main())
    except ValueError as e:
        # Catch configuration errors from the bot's __init__ methods
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
