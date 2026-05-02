import os
import time
import logging
from google import genai
from memory import AgentMemory
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Primary and fallback models — if the primary is overloaded, we gracefully degrade
PRIMARY_MODEL = "gemini-3.1-pro-preview"
FALLBACK_MODEL = "gemini-2.0-flash"

GOOD_NURSE_CONTEXT = """You are the 'Good Nurse Outreach Agent', an autonomous assistant built for Good Nurse.
Good Nurse is a registered NDIS provider based in Westmead, Sydney. They specialize in personalized aged care, disability support, and complex health services.
Services offered:
- In-home care and nursing care
- Disability support
- High-intensity daily personal activities
- Complex care including bowel management, catheter care, enteral nutrition (PEG feeding), and managing severe dysphagia.
- Hospital-to-home transitions and post-discharge recovery.

Contact info: Website: goodnurse.com.au | Phone: 1300 457 557 | Email: support@goodnurse.com.au

Your goal: Help draft social media posts, comments, and LinkedIn connection requests to network with Social Workers, NDIS participants, and Support Coordinators to generate leads. 
Always maintain a professional, empathetic, and human tone.
You are currently chatting with your manager via Telegram. You should assist them, show them drafts, and refine your approach based on their feedback.

[CRITICAL INSTRUCTION]
You have access to autonomous web-scraping scripts running in your background architecture. If your manager asks you to:
1. "Find leads" or scan social media for specific people/posts, you MUST append EXACTLY this secret tag anywhere in your response: [TOOL: FIND_LEADS: <search_keyword>]
   - Example: [TOOL: FIND_LEADS: Social Worker]
2. "Network", "Join Facebook groups", or automatically connect with Support Coordinators, you MUST append EXACTLY this secret tag anywhere in your response: [TOOL: NETWORK: <search_keyword>]
   - Example: [TOOL: NETWORK: Support Coordinator]

Simply acknowledge the user and include the appropriate tag with the most relevant keyword from their request. Do not output scraped data yourself!
"""

class AgentBrain:
    def __init__(self):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key or gemini_api_key == "your_gemini_api_key_here":
            print("Warning: GEMINI_API_KEY is not set correctly in .env")
            return
            
        self.client = genai.Client(api_key=gemini_api_key)
        
        # Short-term active chat memory using direct SDK calls
        self.chat_history = []
        
        # Long-term specific preference memory
        self.memory_store = AgentMemory()

    def _call_with_retry(self, model, contents, config, max_retries=3):
        """Call generate_content with exponential backoff retry on 503/overload errors."""
        last_error = None
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config
                )
                return response
            except Exception as e:
                last_error = e
                error_str = str(e)
                # Retry on 503 / UNAVAILABLE / capacity / overload errors
                if any(kw in error_str for kw in ["503", "UNAVAILABLE", "high demand", "capacity", "overloaded"]):
                    wait_time = 2 ** (attempt + 1)  # 2s, 4s, 8s
                    logger.warning(f"Gemini API overloaded (attempt {attempt+1}/{max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Non-retryable error, raise immediately
                    raise
        # All retries exhausted — raise the last error
        raise last_error
        
    def chat(self, user_input: str = "", media_path: str = None) -> str:
        if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "your_gemini_api_key_here":
            return "API Key Missing: Please update your GEMINI_API_KEY in the .env file."
        
        if not user_input:
            user_input = "Please analyze this attached media and answer accordingly."
            
        past_learnings = self.memory_store.get_past_learnings(context_query=user_input)
        
        full_prompt = f"Previous Approved/Rejected Guidelines you MUST follow (if any):\n{past_learnings}\n\nUser request: {user_input}"
        
        from google.genai import types
        user_parts = [types.Part.from_text(text=full_prompt)]
        
        if media_path:
            # Upload the file natively to Google Gemini API
            uploaded_file = self.client.files.upload(file=media_path)
            
            # For multimedia like videos, wait for Google to finish generating its frames
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(2)
                uploaded_file = self.client.files.get(name=uploaded_file.name)
                
            user_parts.append(types.Part.from_uri(file_uri=uploaded_file.uri, mime_type=uploaded_file.mime_type))
            
        self.chat_history.append(types.Content(role="user", parts=user_parts))
        
        # Keep history from growing too large (e.g., max 20 messages)
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]
            # Ensure the first message is from the user
            if self.chat_history and self.chat_history[0].role == "model":
                self.chat_history.pop(0)
        
        config = {"system_instruction": GOOD_NURSE_CONTEXT}
        
        # Try the primary model first with retries, then fall back
        try:
            response = self._call_with_retry(PRIMARY_MODEL, self.chat_history, config)
        except Exception as primary_err:
            err_str = str(primary_err)
            if any(kw in err_str for kw in ["503", "UNAVAILABLE", "high demand", "capacity", "overloaded"]):
                logger.warning(f"Primary model {PRIMARY_MODEL} unavailable after retries. Falling back to {FALLBACK_MODEL}...")
                try:
                    response = self._call_with_retry(FALLBACK_MODEL, self.chat_history, config)
                except Exception as fallback_err:
                    # Both models failed — return a friendly error instead of crashing
                    self.chat_history.pop()  # Remove the user message so history stays clean
                    return (
                        "The AI service is currently experiencing very high demand across all models. "
                        "Please try again in a minute or two — this is a temporary issue on Google's side."
                    )
            else:
                # Non-capacity error — still don't crash the bot
                self.chat_history.pop()
                return f"An error occurred while thinking: {primary_err}"
        
        self.chat_history.append(types.Content(role="model", parts=[types.Part.from_text(text=response.text)]))
        
        return response.text
