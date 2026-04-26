# 🌟 Social Media Pro: AI Content Studio

Social Media Pro is a premium, AI-driven orchestration platform designed to automate the creation and deployment of social media campaigns across multiple platforms. Built with a modern SaaS aesthetic, it combines powerful LLM agents with image generation to transform simple topics into professional-grade social network presence.


![alt text](<Screenshot 2026-04-26 151915.png>)


## ✨ Key Features

*   **Multi-Platform Orchestration:** Simultaneously coordinate campaigns for Twitter/X, Instagram, LinkedIn, and Facebook.
*   **AI Intelligence Profiles:** Customize the "Brand Voice" (Professional, Casual, Witty, etc.) to match your identity.
*   **Visual Logic Matrix:** Automatically generate high-resolution AI images or upload your own assets per platform.
*   **Human-in-the-Loop Review:** Fully review and edit every caption and image choice before final distribution.
*   **Automated Formatting:** Intelligent truncation and hashtag optimization tailored to each platform's unique constraints.
*   **Premium SaaS UI:** A clean, light-mode "Lumina Studio" dashboard designed for modern productivity.

## 🚀 Getting Started

### Prerequisites
*   Python 3.10+
*   API Keys for:
    *   Mistral AI (Large Language Model)
    *   Hugging Face (Image Generation)
    *   Twitter/X, LinkedIn, Facebook (Publishing)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/Social-Media-Orchestra.git
   cd Social-Media-Orchestra
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv venvcreate 
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment:**
   Create a `.env` file in the root directory based on `.env.example` and add your API keys:
   ```env
   MISTRAL_API_KEY=your_key
   HF_API_KEY=your_key
   TWITTER_API_KEY=your_key
   # ... add others
   ```

## 🖥️ Usage

Start the Lumina Studio dashboard:
```bash
streamlit run app.py
```

1.  **Core Strategy:** Enter your campaign topic and select a brand voice.
2.  **Deployment Nodes:** Select which social platforms you want to target.
3.  **Visual Asset Matrix:** Configure image generation or uploads for each platform.
4.  **Orchestrate:** Click the orange button to generate your draft campaign.
5.  **Review:** Edit captions, select images, and click "Post to All Platforms" to go live.

## 🛠️ Technology Stack

*   **UI Framework:** Streamlit
*   **Orchestration Engine:** LangGraph
*   **Primary Intelligence:** Mistral Large
*   **Image Generation:** Hugging Face Router (Inference API)
*   **Client APIs:** Tweepy (Twitter), Facebook Search Ads (FB), LinkedIn API


