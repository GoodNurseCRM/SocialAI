import os
import asyncio
from playwright.async_api import async_playwright

class FacebookAgent:
    def __init__(self, user_data_dir="./browser_profiles/facebook"):
        self.user_data_dir = user_data_dir
        os.makedirs(self.user_data_dir, exist_ok=True)
        
    async def fetch_group_posts(self, group_url="https://www.facebook.com/groups/ndisproviders", max_posts=3):
        """
        Launches browser, gets recent posts in an NDIS Facebook group.
        Requires manual login on first run (headless=False).
        """
        scraped_posts = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            page = await browser.new_page()
            
            print(f"Navigating to Facebook Group: {group_url}")
            try:
                await page.goto(group_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(5) # Let dynamic elements load
                
                # REPRODUCIBLE LOGIN CHECK: Check for home feed or brand marker
                is_logged_in = await page.locator("a[aria-label='Facebook']").count() > 0 or await page.locator("div[role='navigation']").count() > 0
                if not is_logged_in:
                    if "login" in page.url or await page.locator("input[name='email']").count() > 0:
                        print("Error: Not logged into Facebook. Redirected to login page.")
                        await page.screenshot(path="facebook_login_wall.png")
                        await browser.close()
                        return [{"error": "not_logged_in"}]
                
                # Wait for post elements - try multiple FB layout styles
                found_selector = None
                for selector in ["div[role='article']", "div[data-testid='fbfeed_story']", "[role='feed'] > div"]:
                    try:
                        await page.wait_for_selector(selector, timeout=10000)
                        found_selector = selector
                        break
                    except:
                        continue
                
                if not found_selector:
                    print(f"No posts found in Facebook group: {group_url}")
                    await page.screenshot(path="debug_facebook_no_results.png")
                    await browser.close()
                    return []
                
                post_elements = await page.query_selector_all(found_selector)
                count = 0
                for element in post_elements:
                    if count >= max_posts:
                        break
                        
                    try:
                        # Extract the post text - check multiple common Comet/Legacy classes
                        text_el = None
                        for ts in ["div[data-ad-preview='message']", "div[data-ad-comet-preview='message']", "div[dir='auto']"]:
                            text_el = await element.query_selector(ts)
                            if text_el: 
                                # Check if it actually contains text (not just a nested container)
                                t = await text_el.inner_text()
                                if len(t.strip()) > 5: break
                                else: text_el = None
                        
                        if not text_el:
                            continue
                            
                        text = await text_el.inner_text()
                        
                        # Attempt to extract the post's unique URL
                        url = await element.evaluate('''
                            el => {
                                const links = Array.from(el.querySelectorAll('a[role="link"]'));
                                const postLink = links.find(a => a.href.includes('/groups/') && (a.href.includes('/permalink/') || a.href.includes('/posts/')));
                                return postLink ? postLink.href : null;
                            }
                        ''')
                        
                        if url:
                            scraped_posts.append({
                                "text": text.strip(),
                                "url": url.split('?')[0], # Clean URL
                                "platform": "facebook"
                            })
                            count += 1
                    except Exception:
                        continue
                    
            except Exception as e:
                print(f"Facebook scraping error: {e}")
                await page.screenshot(path="debug_facebook_error.png")
            finally:
                await browser.close()
                
        return scraped_posts

    async def post_comment(self, post_url, comment_text):
        """Autonomously publish a comment onto a specific Facebook post URL"""
        print(f"Autonomously posting to {post_url} on Facebook...")
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = await browser.new_page()
            try:
                await page.goto(post_url, wait_until="networkidle")
                
                # Wait for FB comment placeholder to load
                await page.wait_for_selector('div[aria-label="Write a comment"]', timeout=15000)
                
                # Fill the text
                await page.fill('div[aria-label="Write a comment"]', comment_text)
                await asyncio.sleep(1)
                
                # Wait for internal network sync, then press Return to post
                await page.keyboard.press('Enter')
                await asyncio.sleep(5) # Wait for UI confirmation
                
                return True
                
            except Exception as e:
                print(f"Failed to post on Facebook: {e}")
                return False
            finally:
                await browser.close()

    async def discover_and_join_groups(self, memory_store, brain_agent, keyword="NDIS", daily_limit=2):
        """Autonomously search, join, and navigate the induction questions for new NDIS groups."""
        print(f"Autonomous Drone: Searching Facebook for unjoined '{keyword}' Groups...")
        joined_count = 0
        logs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = await browser.new_page()
            try:
                search_url = f"https://www.facebook.com/search/groups/?q={keyword.replace(' ', '%20')}"
                await page.goto(search_url, wait_until="networkidle")
                
                await page.wait_for_selector('a[href*="/groups/"]', timeout=15000)
                await asyncio.sleep(2)
                
                # Extract all unique group links
                links = await page.eval_on_selector_all(
                    'a[role="presentation"], a[role="link"]', 
                    "elements => elements.map(el => el.href).filter(href => href.includes('/groups/') && !href.includes('/search/') && !href.includes('?__'))"
                )
                unique_groups = list(set([l.split('?')[0] for l in links if 'groups' in l]))
                
                for group_url in unique_groups:
                    if joined_count >= daily_limit:
                        break
                        
                    # Spam Filter check
                    if memory_store.has_networked("facebook", group_url):
                        continue
                        
                    print(f"Investigating un-networked Group: {group_url}")
                    memory_store.record_networked("facebook", group_url) # Instantly mark to avoid duplicate hits on crash
                    
                    await page.goto(group_url, wait_until="networkidle")
                    await asyncio.sleep(3)
                    
                    # Look for the Join button (try multiple common FB selectors)
                    join_btn = None
                    for selector in ["div[aria-label='Join group']", "div[aria-label='Join Group']"]:
                        if await page.locator(selector).count() > 0:
                            join_btn = page.locator(selector).first
                            break
                    
                    if not join_btn:
                        continue # Already joined or pending!
                        
                    await join_btn.click()
                    await asyncio.sleep(4)
                    
                    # Handle "Choose how to interact" popup (Personal vs Page)
                    if await page.locator("text='Choose how to interact'").count() > 0:
                        print("🤖 Selecting Good Nurse Page Persona...")
                        # Select the 2nd radio option (usually the Page)
                        radios = page.locator("div[role='radio']")
                        if await radios.count() > 1:
                            await radios.nth(1).click()
                        await asyncio.sleep(1)
                        await page.locator("div[aria-label='Join group']").click()
                        await asyncio.sleep(5)
                    
                    # Handle "Answer Questions" Group Admin Induction Modal
                    if await page.locator("textarea").count() > 0:
                        print("🤖 Group has onboarding questions! Generating AI Responses...")
                        textareas = await page.locator("textarea").all()
                        
                        # Generate tailored induction response
                        ans = brain_agent.chat("Write a single sentence explaining why Good Nurse, an official NDIS service provider, wants to join this Facebook networking group.")
                        for ta in textareas:
                            await ta.fill(ans)
                            await asyncio.sleep(0.5)
                            
                        # Agree to rules checkboxes
                        checkboxes = await page.locator("div[role='checkbox']").all()
                        for cb in checkboxes:
                            await cb.click()
                            
                        submit_btn = page.locator("div[aria-label='Submit']")
                        if await submit_btn.count() > 0:
                            await submit_btn.first.click()
                            await asyncio.sleep(3)
                            
                    logs.append(f"✅ Submitted Join Request to **Facebook Group**: [View Group]({group_url})")
                    joined_count += 1
                    
            except Exception as e:
                print(f"Facebook Drone Error: {e}")
            finally:
                await browser.close()
                
        return logs
