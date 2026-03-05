import os
import time
from datetime import datetime
import feedparser
import requests
from groq import Groq
from dotenv import load_dotenv
from db_helper import DBHelper
from tavily import TavilyClient

# Load environment variables
load_dotenv()

# Initialize Groq
groq_api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=groq_api_key) if groq_api_key else None

def get_news_from_rss():
    """Fetches text news from a few popular RSS feeds."""
    feeds = [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml"
    ]
    
    articles = []
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
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

def get_news_from_api():
    """Fetches AI/Tech news from NewsAPI if a key is provided."""
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        print("Skipping NewsAPI as NEWS_API_KEY is not set.")
        return []
        
    url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&apiKey={api_key}"
    articles = []
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for article in data.get("articles", [])[:10]:
                # Don't grab empty articles
                if article.get("title") and article.get("url"):
                    articles.append({
                        "title": article["title"],
                        "url": article["url"],
                        "description": article.get("description", ""),
                        "source": "NewsAPI"
                    })
        else:
            print(f"NewsAPI error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error fetching from NewsAPI: {e}")
        
    return articles

def get_trending_topics():
    """Fetches currently trending technology topics using Tavily Search API."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("Skipping Tavily search as TAVILY_API_KEY is not set.")
        return []

    try:
        client = TavilyClient(api_key=api_key)
        # We prompt Tavily to find the latest highly viral or trending tech news today
        response = client.search(
            query="What are the most viral and trending technology and AI news topics today?",
            search_depth="advanced",
            include_answer=False,
            include_images=False,
            include_raw_content=False,
            max_results=5,
        )
        
        articles = []
        for result in response.get("results", []):
            articles.append({
                "title": result.get("title", "Trending Topic"),
                "url": result.get("url", ""),
                "description": result.get("content", ""),
                "source": "TavilySearch"
            })
        return articles
    except Exception as e:
        print(f"Error fetching trending topics via Tavily: {e}")
        return []

def summarize_and_categorize_news(title, description):
    """Uses AI to summarize the news, assign a category, and identify 'trending' potential."""
    if not client:
        # Fallback if no OpenAI key
        summary = description[:200] + "..." if description else "No description available."
        return summary, "Technology", "Normal"
        
    prompt = f"""
    Please read the following news headline and description:
    Title: {title}
    Description: {description}
    
    Task 1: Summarize the story in 2-3 clear, engaging sentences.
    Task 2: Assign it to ONE of these categories: AI, Startups, Gadgets, Software, Cybersecurity, Technology.
    Task 3: Rate the "Viral Trendiness" potential from 1-10 and label it as "High" (7+) or "Normal".
    
    Format your response EXACTLY like this:
    Summary: [Your summary]
    Category: [The category]
    Trendiness: [High/Normal]
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7
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


def run_news_agent():
    print(f"[{datetime.now()}] Starting News Research Agent...")
    
    # 1. Fetch news
    rss_news = get_news_from_rss()
    api_news = get_news_from_api()
    trending_topics = get_trending_topics()
    all_news = rss_news + api_news + trending_topics
    
    if not all_news:
        print("No news found from any source.")
        return

    # 2. Connect to DB
    try:
        db = DBHelper()
        db.connect()
    except Exception as e:
        print(f"Database connection error: {e}")
        return

    # 3. Process each article
    saved_count = 0
    date_found = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for article in all_news:
        title = article["title"]
        url = article["url"]
        desc = article["description"]
        
        if not title or title == "Removed":
            continue
            
        existing_urls = []
        try:
            existing_urls = db.news_sheet.col_values(4)
        except Exception:
            pass 
            
        if url in existing_urls:
            continue
            
        # Summarize with AI
        summary, category, trendiness = summarize_and_categorize_news(title, desc)
        
        # Save to sheet
        try:
            # We'll prepend [TRENDING] to title if high potential
            display_title = f"[TRENDING] {title}" if trendiness == "High" else title
            success = db.add_news_row(display_title, summary, category, url, date_found, status="New")
            if success:
                print(f"Added: [{category}] {display_title[:40]}...")
                saved_count += 1
        except Exception as e:
            print(f"Error saving to DB: {e}")
            
    print(f"[{datetime.now()}] News Agent finished. Saved {saved_count} new articles.")

if __name__ == "__main__":
    run_news_agent()
