import os
import logging
from playwright.async_api import async_playwright
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

import uuid
from brain import AgentBrain
from linkedin import LinkedInAgent
from facebook import FacebookAgent
from instagram import InstagramAgent

import re

async def _is_session_valid(profile_dir: str, check_url: str) -> bool:
    """Returns True if the saved Playwright session is still authenticated by checking UI markers."""
    if not os.path.exists(profile_dir) or not os.listdir(profile_dir):
        return False
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = await browser.new_page()
            await page.goto(check_url, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(3)
            
            # Use platform-specific marker detection instead of just URL
            is_valid = False
            if "linkedin" in check_url:
                is_valid = await page.locator("#global-nav").count() > 0
            elif "facebook" in check_url:
                is_valid = await page.locator("a[aria-label='Facebook']").count() > 0 or await page.locator("div[role='navigation']").count() > 0
            elif "instagram" in check_url:
                is_valid = await page.locator("svg[aria-label='Instagram']").count() > 0 or await page.locator("nav").count() > 0
            else:
                # Fallback for generic - ensure we aren't on a login page
                is_valid = not any(kw in page.url for kw in ["login", "authwall", "accounts/login"])
            
            await browser.close()
            return is_valid
        except Exception:
            try:
                await browser.close()
            except Exception:
                pass
            return False

RUNTIME_DRAFTS = {}

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

brain = AgentBrain()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Hello! I am the Executive AI Assistant for Good Nurse. \U0001f3e5\n"
        "I can help you monitor social media, draft responses, and build connections "
        "with Social Workers and NDIS participants.\n\n"
        "Just chat with me here, or use /draft to have me generate a specific outreach message!"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
        
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    user_input = update.message.text or update.message.caption or ""
    media_path = None
    
    try:
        if update.message.effective_attachment:
            attachment = update.message.effective_attachment
            if isinstance(attachment, list):
                attachment = attachment[-1]
            file = await context.bot.get_file(attachment.file_id)
            ext = os.path.splitext(file.file_path)[1] if getattr(file, "file_path", None) else ""
            media_path = f"temp_{update.effective_chat.id}_{attachment.file_id}{ext}"
            await file.download_to_drive(media_path)
            
        reply = brain.chat(user_input, media_path=media_path)
        
    except Exception as e:
        reply = f"Agent crashed while thinking: {e}"
        
    finally:
        if media_path and os.path.exists(media_path):
            os.remove(media_path)
            
    # Intent Parsing with parameterized regex
    find_leads_keyword = None
    network_keyword = None
    
    # Matches [TOOL: FIND_LEADS: <keyword>]
    fl_match = re.search(r'\[TOOL: FIND_LEADS:?\s*(.*?)\]', reply, re.IGNORECASE)
    if fl_match:
        kw = fl_match.group(1).strip()
        find_leads_keyword = kw if kw else "NDIS Provider"
        reply = re.sub(r'\[TOOL: FIND_LEADS:?\s*(.*?)\]', '', reply, flags=re.IGNORECASE)
        
    # Matches [TOOL: NETWORK: <keyword>]
    nw_match = re.search(r'\[TOOL: NETWORK:?\s*(.*?)\]', reply, re.IGNORECASE)
    if nw_match:
        kw = nw_match.group(1).strip()
        network_keyword = kw if kw else "Support Coordinator"
        reply = re.sub(r'\[TOOL: NETWORK:?\s*(.*?)\]', '', reply, flags=re.IGNORECASE)

    # Send clean reply
    reply = reply.strip()
    if reply:
        max_len = 4000
        for i in range(0, len(reply), max_len):
            await context.bot.send_message(chat_id=update.effective_chat.id, text=reply[i:i+max_len])
            
    if find_leads_keyword:
        await find_leads(update, context, keyword=find_leads_keyword)
    if network_keyword:
        await autonomous_networking(update, context, keyword=network_keyword)

async def draft_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = " ".join(context.args)
    if not user_input:
        await update.message.reply_text("Please provide a topic. E.g., /draft A LinkedIn post about PEG feeding.")
        return
        
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    query = f"Please draft this for me. Make it ready to post: {user_input}"
    try:
        reply = brain.chat(query)
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Agent crashed while drafting: {e}")
        return
        
    keyboard = [
        [
            InlineKeyboardButton("\u2705 Approve", callback_data=f"approve|{user_input[:20]}"),
            InlineKeyboardButton("\u274c Reject", callback_data=f"reject|{user_input[:20]}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=reply, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("|")
    action = data[0]
    draft_id = data[1] if len(data) > 1 else ""
    
    if draft_id in RUNTIME_DRAFTS:
        cached = RUNTIME_DRAFTS[draft_id]
        platform = cached["platform"]
        url = cached["url"]
        draft_text = cached["draft"]
        original = cached["original_post_text"]
    else:
        platform = None
        url = ""
        draft_text = query.message.text
        original = draft_id
        
    if action == "approve":
        brain.memory_store.log_feedback(drafted_text=draft_text, status="approved", original_post=original)
        await query.edit_message_text(text=f"{draft_text}\n\n[\u2705 Approved and Saved to Memory!]")
        
        if platform:
            success = False
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"Launching headless browser to autonomously publish this to {platform.capitalize()}...")
            if platform == "linkedin":
                agent = LinkedInAgent()
                success = await agent.post_comment(url, draft_text)
            elif platform == "facebook":
                agent = FacebookAgent()
                success = await agent.post_comment(url, draft_text)
            elif platform == "instagram":
                agent = InstagramAgent()
                success = await agent.post_comment(url, draft_text)
                
            if success:
                await context.bot.send_message(chat_id=query.message.chat_id, text=f"**Successfully Published to {platform.capitalize()}!**\nView it here: {url}")
            else:
                await context.bot.send_message(chat_id=query.message.chat_id, text=f"**Playwright failed to click the Post button on {platform.capitalize()}!** Check terminal for errors.")
                
    elif action == "reject":
        brain.memory_store.log_feedback(drafted_text=draft_text, status="rejected", original_post=original)
        await query.edit_message_text(text=f"{draft_text}\n\n[\u274c Rejected and Saved to Memory! The agent won't write like this again.]")

async def find_leads(update: Update, context: ContextTypes.DEFAULT_TYPE, keyword="NDIS Search Coordinator"):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Booting up secure scrapers for lead keyword: **{keyword}**...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    li_agent = LinkedInAgent()
    fb_agent = FacebookAgent()
    ig_agent = InstagramAgent()
    
    async def process_platform(posts, platform_name):
        if isinstance(posts, list) and len(posts) > 0 and isinstance(posts[0], dict) and "error" in posts[0]:
            error_type = posts[0].get("error", "")
            if error_type == "not_logged_in":
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{platform_name.capitalize()}: Session expired/invalid. Run auth.py to re-authenticate!")
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{platform_name.capitalize()}: Scraper error - {error_type}")
            return
        
        if not posts:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{platform_name.capitalize()}: Logged in OK but 0 matching results for '{keyword}'. Layout may have shifted or no recent matches.")
            return
            
        for post in posts:
            text = post["text"]
            url = post["url"]
            prompt = f"I found this post on {platform_name}:\n\n'{text}'\n\nDraft a short, professional, empathetic outreach comment seamlessly introducing Good Nurse's services as the Good Nurse Business Page."
            draft = brain.chat(prompt)
            
            draft_id = uuid.uuid4().hex[:8]
            RUNTIME_DRAFTS[draft_id] = {
                "platform": platform_name,
                "url": url,
                "draft": draft,
                "original_post_text": text
            }
            
            keyboard = [[
                InlineKeyboardButton("\u2705 Approve & Auto-Post", callback_data=f"approve|{draft_id}"),
                InlineKeyboardButton("\u274c Reject", callback_data=f"reject|{draft_id}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            msg = f"New {platform_name.capitalize()} Lead for '{keyword}'!\n\n**Post Text:**\n_{text[:250]}..._\n\n**Draft:**\n{draft}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=reply_markup)

    # Scrape sequentially with proper error reporting
    for platform_name, scrape_coro in [
        ("linkedin", li_agent.fetch_recent_posts(keyword=keyword, max_posts=1)),
        ("facebook", fb_agent.fetch_group_posts(max_posts=1)), # FB is currently group-specific
        ("instagram", ig_agent.fetch_hashtag_posts(hashtag=keyword.replace(" ","").lower(), max_posts=1)),
    ]:
        try:
            posts = await scrape_coro
            await process_platform(posts, platform_name)
        except Exception as e:
            print(f"{platform_name} Error: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{platform_name.capitalize()}: Scraper crashed - {str(e)[:150]}")
        
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Finished scanning social platforms!")

async def autonomous_networking(update: Update, context: ContextTypes.DEFAULT_TYPE, keyword="Support Coordinator"):
    """Triggers the background networking drones with target keyword."""
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"**Dispatching Autonomous Drones!** Targeting: **{keyword}**...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    memory = brain.memory_store
    fb = FacebookAgent()
    li = LinkedInAgent()
        
    # 1. Facebook Drone
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Drone 1: Facebook Group Sourcing for '{keyword}'...")
    fb_logs = await fb.discover_and_join_groups(memory_store=memory, brain_agent=brain, keyword=keyword, daily_limit=2)
    
    if fb_logs:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="\n\n".join(fb_logs), parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="ℹ️ Facebook Drone: No new groups joined.")
        
    # 2. LinkedIn Drone
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Drone 2: LinkedIn Targeted Connections for '{keyword}'...")
    li_logs = await li.discover_and_connect(memory_store=memory, brain_agent=brain, keyword=keyword, daily_limit=2)
    
    if li_logs:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="\n\n".join(li_logs), parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="ℹ️ LinkedIn Drone: No new connection requests.")
        
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🎯 **Autonomous Mission Complete!**")


async def check_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Telegram command: /check_auth — tests all 3 platform sessions using UI markers."""
    await context.bot.send_message(chat_id=update.effective_chat.id,
        text="🔍 Checking session health for LinkedIn, Facebook & Instagram...")

    PLATFORM_SESSIONS = {
        "LinkedIn":  {"check_url": "https://www.linkedin.com/feed/",  "profile": "./browser_profiles/linkedin"},
        "Facebook":  {"check_url": "https://www.facebook.com/",       "profile": "./browser_profiles/facebook"},
        "Instagram": {"check_url": "https://www.instagram.com/",      "profile": "./browser_profiles/ig_profile"},
    }

    lines = []
    expired = []
    for name, cfg in PLATFORM_SESSIONS.items():
        valid = await _is_session_valid(cfg["profile"], cfg["check_url"])
        if valid:
            lines.append(f"✅ {name}: Session is ACTIVE")
        else:
            lines.append(f"❌ {name}: Session EXPIRED or Restricted — needs re-login")
            expired.append(name)

    status_msg = "\n".join(lines)

    if expired:
        fix_msg = (
            f"\n\n⚠️ *{len(expired)} platform(s) need re-authentication.*"
            f"\n\nTo fix, run this on your PC:\n"
            f"```\npython auth.py\n```"
            f"\nFollow the prompts to log back in. Then restart the bot."
        )
        await context.bot.send_message(chat_id=update.effective_chat.id,
            text=status_msg + fix_msg, parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
            text=status_msg + "\n\n🎉 All sessions healthy! Bot can find leads autonomously.")


if __name__ == '__main__':
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token or telegram_token == "your_telegram_bot_token":
        print("Error: Please set TELEGRAM_BOT_TOKEN in your .env file.")
        exit(1)
        
    application = ApplicationBuilder().token(telegram_token).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('draft', draft_post))
    application.add_handler(CommandHandler('find_leads', find_leads))
    application.add_handler(CommandHandler('network', autonomous_networking))
    application.add_handler(CommandHandler('check_auth', check_auth))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("Good Nurse Telegram Agent is running...")
    application.run_polling()
