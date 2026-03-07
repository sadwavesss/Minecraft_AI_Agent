# Groq LLM Integration Setup Guide

This guide explains how to set up Groq's free LLM API to power the AI assistant's tips in your Minecraft game.

## Why Groq?

Groq provides a fast, free-tier LLM API that's perfect for real-time game assistance:
- **Free tier**: Up to 30 requests per minute
- **Fast inference**: Very quick responses
- **Context-aware**: Analyzes last 5 game events to give specific tips
- **Russian support**: Generates tips in Russian

## Step 1: Get a Groq API Key

1. Go to https://console.groq.com/keys
2. Sign up for a free Groq account (requires Google/GitHub login)
3. Once logged in, you'll see your API key
4. Copy the API key (keep it secret!)

## Step 2: Create .env File

In the root directory of the project (same folder as `main.py`), create a file named `.env`:

```
GROQ_API_KEY=your_actual_api_key_here
```

Replace `your_actual_api_key_here` with the key you copied from Groq Console.

**Important:**
- The `.env` file is automatically ignored by git (in `.gitignore`)
- Never commit this file to version control
- Never share your API key

## Step 3: Verify It Works

Start the server and check the logs:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Test the endpoint:

```bash
curl http://127.0.0.1:8000/api/advice/
```

Look for `"source": "groq"` in the response. If you see `"source": "fallback"`, the API key wasn't loaded.

## How It Works

### With Groq (API key configured)

1. When a player requests advice, the system collects the last 5 game events
2. These are formatted as context about:
   - Current health
   - Nearby threats
   - Hunger level
   - Time of day
   - Recent events (low health, hostile mobs, night time, etc.)
3. Groq LLM analyzes this context in Russian
4. Returns a short, actionable tip specific to the player's situation
5. Tip is sent back with `"source": "groq"`

### Without Groq (no API key)

If no API key is set or Groq is unavailable:

1. System automatically falls back to rule-based advice
2. Same priority-based logic as before (check for low health, enemies, hunger, etc.)
3. Returns advice with `"source": "fallback"`

This ensures the game always has helpful tips, even if Groq is down.

## API Response Format

```json
{
  "advice": "Низкое здоровье: отступи, закройся блоками и срочно поешь/используй зелья.",
  "confidence": 0.8,
  "level": "WARNING",
  "threats": [],
  "source": "groq"
}
```

- **advice**: The actual tip text (in Russian)
- **confidence**: How confident the system is (0.6-0.85)
- **level**: Severity level (INFO, WARNING, or CRITICAL)
- **threats**: List of detected threats
- **source**: Either `"groq"` (AI-generated) or `"fallback"` (rule-based)

## Troubleshooting

### "source" is always "fallback"

1. Check if `.env` file exists in the project root
2. Verify `GROQ_API_KEY=` line is there
3. Make sure the API key is correct
4. Restart the server after creating/editing `.env`

### API key shows as `None`

The `python-dotenv` package might not be loading the `.env` file. Try:

```python
from dotenv import load_dotenv
load_dotenv()  # Explicitly load .env
```

This is already done in `api/advice.py`, but if you're testing elsewhere, add it.

### Groq API rate limit

Groq free tier is 30 requests per minute. The mod requests advice periodically (default 5 seconds), so ~12 requests per minute. This should be well within limits.

### Groq API errors

Check the server logs for error messages. Common issues:
- Invalid API key format
- Account suspended
- Network connectivity issues

## Advanced: Customize the Prompt

Edit `api/groq_client.py` in the `generate_tip()` method to customize the prompt that's sent to Groq. Current prompt asks for:
- Short (1-2 sentences) advice
- Specific to what's happening
- Actionable (tells player what to do)
- In Russian language

## Free Tier Limits

- 30 requests per minute
- No credit card required
- Good for small-scale testing and personal use
- Paid tiers available for higher volume

## Cost Estimate

For a single player using the mod with advice requested every 5 seconds:
- ~12 requests per minute
- ~720 requests per hour
- **Free tier covers this completely**

For multiple players or higher frequency, Groq pricing is very reasonable (~$0.05 per million tokens).

---

Questions? Check:
- https://console.groq.com/docs
- https://groq.com/
- Project README.md
