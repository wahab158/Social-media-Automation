# Social Media Automation: Frontend & API Documentation

This document provides a comprehensive overview of how the current frontend interacts with the backend, its core features, and technical specifications. It also includes strategic recommendations for the next version of the platform.

---

## 🏗️ System Architecture
The application follows a modern **Decoupled Architecture**:
- **Frontend**: React (Vite) + Lucide Icons + Axios (for API communication).
- **Backend**: FastAPI (Python) + Groq (LLM) + Cloudinary (Media) + Google Sheets (Data persistence).
- **Communication**: RESTful API for standard operations + SSE (Server-Sent Events) for real-time AI Chat streaming.

---

## 🚀 Frontend Features

### 1. AI Command Center (Chat Wizard)
The central nervous system of the dashboard.
- **SSE Streaming**: Real-time "thinking" status updates from the AI.
- **Smart Pining**: Drag-and-drop images/videos from the Media Library or local storage to "Pin" them as context for the AI.
- **Context-Aware Research**: The AI (Antigravity) can perform web research on specific topics, generate viral captions, and even trigger the automated pipeline based on natural language commands.
- **In-Chat Drafts**: When the AI generates a post, it renders a mini-approval card directly in the chat for instant publishing.

### 2. News Feed & Researcher
Automated content discovery engine.
- **Bulk Discovery**: Fetches the latest trending news based on user-defined topics (AI, Tech, etc.).
- **Editable Summaries**: Review and tweak news summaries before they are sent to the AI for caption generation.
- **Bulk Generation**: Select multiple news articles and generate unique social media drafts for each in one click.
- **Custom Post Creator**: A "Gemini-style" input box at the top allows users to paste raw text/news and instantly "Craft" a professional post draft.

### 3. Smart Approval System (Approval Card)
Professional-grade content refiner.
- **Multi-Platform Support**: Simultaneously manages Instagram, Facebook, LinkedIn, and X (Twitter).
- **Platform-Specific Captions**: Generates and allows editing of unique captions for each platform to ensure maximum engagement.
- **Vision AI Recommendations**: Automatically analyzes uploaded images and suggests the best crop ratio (Square, Portrait, Landscape) for each platform.
- **Cloudinary AI Transforms**: Uses intelligent `g_auto:subject` cropping to ensure the main subject matches the platform's required aspect ratio without manual editing.
- **Character Limit Enforcement**: Visual warnings and "Publish" blocking if a caption exceeds platform limits (e.g., 280 chars for X).

### 4. Media Library
Centralized asset management.
- **Cloudinary Integration**: Fully synced with Cloudinary storage.
- **Smart Upload**: When an image is uploaded, it is automatically analyzed by the Vision AI to prepare suggested crops before the user even sees it.
- **Quick-Pin**: One-click to pin any existing asset for use in the AI Chat.

---

## 🔗 API Endpoints (Backend Connection)

### 🔐 Authentication
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | User registration and JWT issuance. |
| `POST` | `/api/auth/login` | Secure login with bcrypt validation. |
| `GET` | `/api/auth/me` | Validates JWT and returns current user profile. |

### 📝 Content & Workflow
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/content/pending` | Retrieves Drafts from the Google Sheets "Database". |
| `GET` | `/api/content/history` | Fetches Posted/Failed history logs. |
| `POST` | `/api/content/edit` | Updates captions, platforms, or media URLs for a draft. |
| `POST` | `/api/workflow/approve-and-publish` | Atomically marks draft as Approved and triggers the Publisher engine. |
| `DELETE` | `/api/content/{index}` | Soft-deletes a row in the system. |

### 📰 News & Research
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/news` | Lists all discovered news articles. |
| `POST` | `/api/news/fetch` | Triggers the News Agent to find new content for a topic. |
| `POST` | `/api/news/generate` | Calls the Content Agent to turn news into social drafts. |
| `POST` | `/api/news/custom` | Generates a draft directly from user-provided text. |

### 🖼️ Media & AI
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/media/upload-and-analyze` | The "Smart Upload" pipeline (Upload + Vision Analysis + Transforms). |
| `POST` | `/api/media/retransform` | Manual override to generate a new crop via Cloudinary. |
| `POST` | `/api/ai/chat` | The SSE Streaming endpoint for the AI Assistant. |

---

## 💡 System Upgrade & Feature Recommendations

Since you are rebuilding the frontend with **Lovable**, here are the top recommendations to take the system from "Functional" to "Elite":

### 🎨 1. UI/UX Transformation
- **Glassmorphic Design**: Use backdrop blurs and subtle gradients to create a premium, futuristic SaaS feel.
- **Dark/Light Mode**: Implement a sleek toggle (prefer dark mode by default for AI apps).
- **Interactive Tutorials**: Add a "Guided Onboarding" for the Chat Wizard to show users how to pin images and trigger tasks.
- **Vibrant Empty States**: Replace boring text with AI-generated illustrations (Lottie animations or custom SVGs).

### 🚀 2. "Content Calendar" View
- **The Gap**: Currently, drafts are just a list.
- **The Upgrade**: A drag-and-drop calendar where users can see their scheduled posts visually. This makes it feel like a professional tool (like Buffer or Hootsuite).

### 📈 3. Real-time Analytics Dashboard
- **The Gap**: The system publishes content but doesn't track performance.
- **The Upgrade**: Integrate Ayrshare Analytics to pull Likes, Impressions, and Comments back into the "Post History" view. Show growth charts on the Overview page.

### 🤖 4. "Brand Kit" Integration
- **The Upgrade**: Let users save "Brand Voice" (e.g., Professional, Sassy, Minimalist) and "Brand Assets" (Logos, hex colors).
- **AI Sync**: The AI can then automatically inject brand-specific emojis, hashtags, and even overlay logos on images using Cloudinary's overlay features.

### 🏗️ 5. Infrastructure Scaling
- **Database Migration**: Move from SQLite to **PostgreSQL (Supabase)** for better multi-tenancy and real-time database listeners.
- **Task Queue**: Move the Publisher and News Fetcher to a task queue (like **Celery** or **Upstash Redis**) to prevent API timeouts during heavy processing.
- **WebSockets**: Upgrade the AI Chat from SSE to WebSockets for even faster, bi-directional interaction.


**Social Media Co-Pilot**
