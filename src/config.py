#!/usr/bin/env python3
"""
AI Newsletter Bot - Configuration Management
Centralized configuration with validation.
"""

import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class NewsletterConfig:
    """Centralized configuration for the newsletter bot."""
    
    # Required API credentials
    tavily_api_key: str
    azure_endpoint: str
    azure_api_key: str
    resend_api_key: str
    from_email: str
    to_emails: List[str]
    
    # Optional settings with defaults
    azure_deployment: str = "gpt-5-nano"
    azure_api_version: str = "2024-12-01-preview"
    ai_interests: str = "Large Language Models, AI agents, AI tools, machine learning breakthroughs"
    target_audience: str = "tech professionals and AI enthusiasts"
    newsletter_name: str = "AI Daily Brief"
    
    @classmethod
    def from_env(cls) -> 'NewsletterConfig':
        """Create configuration from environment variables."""
        # Required fields - no defaults
        required_fields = {
            'tavily_api_key': 'TAVILY_API_KEY',
            'azure_endpoint': 'AZURE_OPENAI_ENDPOINT', 
            'azure_api_key': 'AZURE_OPENAI_API_KEY',
            'resend_api_key': 'RESEND_API_KEY',
            'from_email': 'FROM_EMAIL'
        }
        
        # Validate required fields
        missing_fields = []
        config_values = {}
        
        for field_name, env_var in required_fields.items():
            value = os.getenv(env_var)
            if not value:
                missing_fields.append(env_var)
            else:
                config_values[field_name] = value
        
        # Parse recipient emails (required)
        recipients_str = os.getenv('RECIPIENT_EMAILS', '')
        to_emails = [email.strip() for email in recipients_str.split(',') if email.strip()]
        if not to_emails:
            missing_fields.append('RECIPIENT_EMAILS')
        else:
            config_values['to_emails'] = to_emails
        
        if missing_fields:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")
        
        # Optional fields with defaults
        config_values.update({
            'azure_deployment': os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', cls.azure_deployment),
            'azure_api_version': os.getenv('AZURE_OPENAI_API_VERSION', cls.azure_api_version),
            'ai_interests': os.getenv('AI_INTERESTS', cls.ai_interests),
            'target_audience': os.getenv('TARGET_AUDIENCE', cls.target_audience),
            'newsletter_name': os.getenv('NEWSLETTER_NAME', cls.newsletter_name),
        })
        
        return cls(**config_values)
    
    def get_interests_list(self) -> List[str]:
        """Get AI interests as a cleaned list."""
        return [interest.strip() for interest in self.ai_interests.split(',')]