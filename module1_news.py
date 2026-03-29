import os
import time
from datetime import datetime
import feedparser
import requests
from groq import Groq
from dotenv import load_dotenv
import db_content_helper as dbcontent
from tavily import TavilyClient

# Import db_sql_helper for multi-tenant keys
from db_sql_helper import get_api_key as sqlite_get_key

# Load environment variables
load_dotenv()

def get_groq_client(user_id):
    """Initializes Groq client using user's API key, or falls back to env var."""
    api_key = None
    if user_id:
        api_key = sqlite_get_key(user_id, "groq", "api_key")
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY")
    return  Groq(api_key=api_key) if api_key else None

def get_news_from_rss():
    """Fetches text news from a few popular RSS feeds."""
    feeds = [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml"
    ]
    
    articles = []
    for feed_url in feeds:
        try:
            feed_resp = requests.get(feed_url, timeout=10)
            if feed_resp.status_code == 200:
                parsed = feedparser.parse(feed_resp.text)
                for entry in parsed.entries[:5]: # Get top 5 from each
                    articles.append({
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "description": entry.get("summary", ""),
                        "source": "RSS"
                    })
        except Exception as e:
            print(f"Error fetching RSS {feed_url}: {e}")
            
    return articles

def get_news_from_api(user_id=None):
    """Fetches AI/Tech news from NewsAPI if a key is provided."""
    api_key = None
    if user_id:
        api_key = sqlite_get_key(user_id, "newsapi", "api_key")
    if not api_key:
        api_key = os.getenv("NEWS_API_KEY")
        
    if not api_key:
        print("Skipping NewsAPI as NEWS_API_KEY is not set.")
        return []
        
    url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&apiKey={api_key}"
    articles = []
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for article in data.get("articles", [])[:10]:
                # Don't grab empty articles
                if article.get("title") and article.get("url"):
                    source_name = article.get("source", {}).get("name", "NewsAPI")
                    articles.append({
                        "title": article["title"],
                        "url": article["url"],
                        "description": article.get("description", ""),
                        "source": source_name,
                        "relevance": ""
                    })
        else:
            print(f"NewsAPI error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error fetching from NewsAPI: {e}")
        
    return articles

def get_trending_topics(custom_query=None, user_id=None):
    """Fetches trending topics or targeted news via Tavily."""
    api_key = None
    if user_id:
        api_key = sqlite_get_key(user_id, "tavily", "api_key")
    if not api_key:
        api_key = os.getenv("TAVILY_API_KEY")
        
    if not api_key:
        return []

    query = custom_query if custom_query else "What are the most viral and trending technology and AI news topics today?"
    
    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=3,
        )
        
        articles = []
        for result in response.get("results", []):
            rel_score = result.get("score", "")
            if isinstance(rel_score, float):
                rel_score = f"{rel_score:.2f}"
            articles.append({
                "title": result.get("title", "Trending Topic"),
                "url": result.get("url", ""),
                "description": result.get("content", ""),
                "source": "Tavily",
                "relevance": rel_score
            })
        return articles
    except Exception as e:
        print(f"Error in Tavily search: {e}")
        return []

def summarize_and_categorize_news(title, description, client):
    """Uses AI to summarize the news, assign a category, and identify 'trending' potential."""
    if not client:
        # Fallback if no Groq key
        summary = description[:200] + "..." if description else "No description available."
        return summary, "Technology", "Normal"
        
    prompt = f"""
    Please read the following news headline and description:
    Title: {title}
    Description: {description}
    
    Task 1: Generate a detailed, engaging, and highly informative news article text based on this story. 
    IMPORTANT: The article text MUST be EXACTLY between 15 and 17 lines long. Each line should be a full, meaningful sentence or part of a coherent paragraph.
    
    Task 2: Assign it to ONE of these categories: AI, Startups, Gadgets, Software, Cybersecurity, Technology.
    Task 3: Rate the "Viral Trendiness" potential from 1-10 and label it as "High" (7+) or "Normal".
    
    Format your response EXACTLY like this:
    Summary: [Your 15-17 line detailed article]
    Category: [The category]
    Trendiness: [High/Normal]
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7,
            timeout=30.0
        )
        output = response.choices[0].message.content.strip()
        
        # Parse output
        summary = "Error"
        category = "Technology"
        trendiness = "Normal"
        
        for line in output.split("\n"):
            if line.startswith("Summary:"): summary = line.replace("Summary:", "").strip()
            if line.startswith("Category:"): category = line.replace("Category:", "").strip()
            if line.startswith("Trendiness:"): trendiness = line.replace("Trendiness:", "").strip()
        
        # Clean formatting
        category = category.replace("*", "").replace("'", "").replace('"', "")
        trendiness = trendiness.replace("*", "").replace("'", "").replace('"', "")
        
        return summary, category, trendiness
        
    except Exception as e:
        print(f"AI summarization error: {e}")
        return "Error calling AI for summary.", "Technology", "Normal"


def run_news_agent(custom_query=None, user_id=None):
    print(f"[{datetime.now()}] Starting News Research Agent for user {user_id or 'System'}...")
    
    client = get_groq_client(user_id)
    
    # 1. Fetch news
    rss_news = get_news_from_rss()
    api_news = get_news_from_api(user_id=user_id)
    trending_topics = get_trending_topics(custom_query=custom_query, user_id=user_id)
    all_news = rss_news + api_news + trending_topics
    
    if not all_news:
        print("No news found from any source.")
        return 0, "No news found."

    # 2. Add News to DB
    saved_count = 0
    date_found = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for article in all_news:
        title = article["title"]
        url = article["url"]
        desc = article["description"]
        
        if not title or title == "Removed":
            continue
            
        # Summarize with AI
        summary, category, trendiness = summarize_and_categorize_news(title, desc, client)
        
        # Save to DB
        try:
            # We'll prepend [TRENDING] to title if high potential
            display_title = f"[TRENDING] {title}" if trendiness == "High" else title
            source_name = article.get("source", "Unknown")
            relevance = article.get("relevance", "")
            
            success = dbcontent.add_news_row(
                display_title, summary, category, url, date_found, 
                status="New", source_name=source_name, relevance_score=relevance,
                user_id=user_id
            )
            if success:
                print(f"Added: [{category}] {display_title[:40]}...")
                saved_count += 1
        except Exception as e:
            print(f"Error saving to DB: {e}")
            
    print(f"[{datetime.now()}] News Agent finished. Saved {saved_count} new articles.")
    return saved_count, "Success"

if __name__ == "__main__":
    run_news_agent()
