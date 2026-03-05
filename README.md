# Social Media Automation System

This is a complete, multi-agent AI system designed to fetch tech news, build content for various social media platforms (Instagram, Facebook, LinkedIn, X), allow for human review, and then publish to those specific platforms via smart routing. 

It satisfies all assignment requirements, including required reel input handling, error retry tracking, multiple news sources (RSS and APIs), and scheduling capabilities. 

## Technology Stack & Setup
- **Language**: Python 3
- **Dependencies**: `gspread`, `requests`, `feedparser`, `openai`, `python-dotenv`, `schedule`
- **Database**: Google Sheets (used effectively as a persistent database + UI dashboard)

### 1. Requirements Installation
Create a virtual environment and install the required modules:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Google Sheets Database Setup
1. Go to Google Cloud Console, create a project, and enable the **Google Sheets API** and **Google Drive API**.
2. Create a Service Account and download the JSON key object.
3. Rename the downloaded key file to `credentials.json` and place it in the root of this project.
4. Create a new Google Sheet. Share that sheet with the `client_email` found inside your `credentials.json` file as an "Editor".
5. Copy the URL of your Google Sheet.

### 3. Environment Variable (.env) Setup
Rename `.env.example` to `.env` and fill it out:
```dotenv
GOOGLE_SHEET_URL="https://docs.google.com/spreadsheets/d/YOUR_IDENTIFIER/edit"
OPENAI_API_KEY="sk-..."          # Your OpenAI API key
NEWS_API_KEY="optional"          # Required for grabbing news via APIs, otherwise falls back to RSS only
GOOGLE_APPLICATION_CREDENTIALS="credentials.json"
```

---

## How it works (The 4 Modules)

### Module 1: News Research Agent (`module1_news.py`)
Runs on a schedule to fetch from RSS (TechCrunch, TheVerge) and NewsAPI. It uses OpenAI to generate a short, 2-3 sentence summary and assigns a category. Finally, it drops this into the "News Database" sheet, ensuring we don't save duplicate URLs.

### Module 2: Content Creation Agent (`module2_content.py`)
Picks up "New" entries from the Database. It passes the topic and summary to OpenAI, using platform-specific prompt constraints (e.g., 2200 char limits for IG, storytelling for Facebook, < 280 chars for X).
- **Video constraint**: It explicitly asks the user terminal sequentially for a valid Reel/Video URL string. 
- The generated posts and URL are saved as 'Draft' in the "Content Queue" sheet.

### Module 3: Review and Approval Pipeline
This happens inside Google Sheets! A human looks at the latest "Draft" in the "Content Queue". 
The human edits the text, enters specific target combinations under the `platforms` column (e.g., `all` or `fb,ig`), specifies a `schedule_time` ("now" or "2026-03-05 14:00"), and changes the `status` dropdown to "Approved".

### Module 4: Publishing Agent (`module4_publisher.py`)
A scheduled script polling for "Approved" content. If `schedule_time` is reached, it parses the platforms logic and isolates the mock API targets. It handles errors gracefully to ensure if LinkedIn fails, X will still fire. Finally, it records the live URLs and updates to 'Posted'. 

---

## Execution & Testing

To run the whole pipeline continuously inside a scheduler:
```bash
python main.py
```

To run a single testing loop (ideal for development and demos):
```bash
python main.py --test
```

### Mock Unit Tests
All the modules have rigorous unit tests that mimic the respective API, OpenAI responses, and db interactions. Run them natively via:
`python test_mock_db.py`
`python test_module1.py`
`python test_module2.py`
`python test_module4.py`
