import os
import json
import asyncio
from typing import List, Dict, Any
from agents import Agent, Runner
from openai import AsyncOpenAI
from db_sql_helper import get_connection
from db_content_helper import add_news_row, create_post
from module1_news import get_tavily_news, get_news_api_headlines
from image_agent import ImageAgent
from datetime import datetime, timedelta

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Client for Groq
async_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)

# --- Agent Definitions ---

# 1. Orchestrator
orchestrator = Agent(
    name="Orchestrator",
    instructions="""You are the lead content strategist. Your job is to:
    1. Analyze the brand's system instructions and provided news topics.
    2. Decide on a 40/30/20/10 content mix: Academy, Tech News, Business, General.
    3. Generate a structured task list JSON for the sub-agents.
    4. Ensure no same category on two consecutive days.
    5. Route specific tasks to ResearchAgent, ContentAgent, and ImageAgent.""",
    model="llama-3.3-70b-versatile"
)

# 2. ResearchAgent
research_agent = Agent(
    name="ResearchAgent",
    instructions="""You are a world-class researcher. Your job is to:
    1. Browse topics using the provided tools.
    2. Summarize findings into 15-17 line digests with a 'trendiness score'.
    3. Deduplicate news by URL.""",
    model="llama-3.3-70b-versatile"
)

# 3. ContentAgent
content_agent = Agent(
    name="ContentAgent",
    instructions="""You are an expert social media copywriter. Your job is to:
    1. Read the brand's system instructions.
    2. Write platform-native captions for: Instagram (2200), LinkedIn (3000), Facebook (63k), TikTok (2200), and X (280).
    3. Include CTA and contact details as per brand guidelines.""",
    model="llama-3.3-70b-versatile"
)

# 4. ImageAgent (Proxy wrapper to existing ImageAgent class)
# In the SDK, agents are usually LLM-based, but we can wrap our artistic generator as a tool
image_manager = ImageAgent()

async def generate_images_task(topic: str, category: str, brand_profile: dict):
    """Bridge to the artistic generator."""
    return await image_manager.process_post_image(topic, category, brand_profile)

# 5. ScheduleAgent
schedule_agent = Agent(
    name="ScheduleAgent",
    instructions="""You are a scheduling expert. Your job is to:
    1. Assign optimal time slots for a batch of posts.
    2. Enforce: no same category two days in a row, no more than 2 posts in a 3-hour window.
    3. Output the final schedule to the database.""",
    model="llama-3.3-70b-versatile"
)

# --- Orchestration Runner ---

class AgenticWorkflowManager:
    def __init__(self, brand_id: str):
        self.brand_id = brand_id
        self.brand_profile = self._load_brand_profile()

    def _load_brand_profile(self):
        conn = get_connection()
        row = conn.execute("SELECT * FROM brand_profiles WHERE id = ?", (self.brand_id,)).fetchone()
        conn.close()
        return dict(row) if row else {}

    async def run_weekly_cycle(self):
        """Phase 3 Full Parallel Workflow."""
        print(f"Starting Weekly Cycle for {self.brand_profile.get('name')}...")
        
        # 1. Orchestrated Discovery (Deterministic for now, can be LLM-driven)
        # We simulate the 40/30/20/10 plan
        topics = ["AI and Education", "Social Media Automation Trends", "FastAPI and React Production"]
        
        # 2. Parallel Generation (Content + Image)
        tasks = []
        for i, topic in enumerate(topics):
            cat = ["academy", "tech_news", "business", "general"][i % 4]
            tasks.append(self.process_single_post(topic, cat))
        
        results = await asyncio.gather(*tasks)
        print(f"Generated {len(results)} posts in parallel.")
        return results

    async def process_single_post(self, topic: str, category: str):
        """Parallel Content + Image Gen."""
        # 1. Start Content Gen
        content_task = Runner.run(content_agent, input=f"Write captions for: {topic}. Category: {category}. Brand Persona: {self.brand_profile.get('system_instruction')}")
        
        # 2. Start Image Gen
        image_task = generate_images_task(topic, category, self.brand_profile)
        
        # Wait for both
        caps_res, img_res = await asyncio.gather(content_task, image_task)
        
        # 3. Save to DB (Status: generated)
        post_data = {
            "topic": topic,
            "category": category,
            "ig_caption": caps_res.final_output if hasattr(caps_res, 'final_output') else str(caps_res),
            "image_urls": img_res["crops"],
            "status": "generated"
        }
        post_id = create_post(self.brand_id, post_data)
        return post_id

if __name__ == "__main__":
    # Test
    # manager = AgenticWorkflowManager("test-brand-id")
    # asyncio.run(manager.run_weekly_cycle())
    pass
