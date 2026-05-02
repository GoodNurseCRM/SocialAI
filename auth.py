import asyncio
import sys
import io
from playwright.async_api import async_playwright

# Force UTF-8 output on Windows to prevent emoji UnicodeEncodeError in cp1252 terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

async def login_to_platform(platform_name, url, profile_dir):
    print(f"\n--- Logging into {platform_name} ---")
    print("A secure browser will pop open. Please log into your account.")
    print("Once fully logged in and on your home feed, CLOSE the browser window (the X in the top right).")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False, # Opens visibly so you can type passwords
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = await browser.new_page()
        await page.goto(url)
        
        # Wait until the user closes the browser window themselves
        try:
            print("[...] Waiting for you to close the browser window...")
            # If the user clicks the X on the browser, the context fires a close/disconnect event
            await browser.wait_for_event("disconnected", timeout=0)
        except Exception:
            pass
            
    print(f"[OK] Securely saved your background session cookies for {platform_name}!")

async def main():
    print("Welcome to the Good Nurse Scraper Authentication Setup!")
    print("We need to securely save your login sessions so the bot can browse invisibly later.")
    
    print("\n[!] VERY IMPORTANT for Business Pages:")
    print("If you want the bot to comment as the 'Good Nurse' Business Page instead of your personal profile,")
    print("you MUST switch your active profile over to the Page (top-right corner) on Facebook and LinkedIn")
    print("BEFORE you close the browser window!")
    
    # 1. LinkedIn auth
    await login_to_platform("LinkedIn", "https://www.linkedin.com/login", "./browser_profiles/linkedin")
    
    # 2. Facebook auth
    await login_to_platform("Facebook", "https://www.facebook.com/login", "./browser_profiles/facebook")
    
    # 3. Instagram auth
    await login_to_platform("Instagram", "https://www.instagram.com/accounts/login", "./browser_profiles/ig_profile")
    
    print("\n[DONE] Authentication Complete! Your bot can now autonomously use the /find_leads command on Telegram.")

if __name__ == "__main__":
    asyncio.run(main())
