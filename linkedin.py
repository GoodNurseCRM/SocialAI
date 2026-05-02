import os
import asyncio
from playwright.async_api import async_playwright

class LinkedInAgent:
    def __init__(self, user_data_dir="./browser_profiles/linkedin"):
        self.user_data_dir = user_data_dir
        os.makedirs(self.user_data_dir, exist_ok=True)
        
    async def fetch_recent_posts(self, keyword="NDIS Search Coordinator", max_posts=3):
        """
        Launches browser, searches for recent posts about the keyword, and returns their text.
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
            
            # Robust Search URL with content filter
            search_url = f"https://www.linkedin.com/search/results/content/?keywords={keyword.replace(' ', '%20')}&sortBy=%22date_posted%22"
            print(f"Navigating to LinkedIn search: {search_url}")
            
            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(5) # Let dynamic results settle
                
                # REPRODUCIBLE LOGIN CHECK: Check for global-nav instead of just URL
                is_logged_in = await page.locator("#global-nav").count() > 0
                if not is_logged_in:
                    # Try one more check for login markers
                    if "login" in page.url or "authwall" in page.url or await page.locator("button[type='submit']").count() > 0:
                        print("Error: Not logged into LinkedIn. Redirected to login/authwall.")
                        await page.screenshot(path="linkedin_login_wall.png")
                        await browser.close()
                        return [{"error": "not_logged_in"}]
                
                # Wait for post elements - try multiple common content markers
                found_selector = None
                for selector in ["div[data-urn]", ".feed-shared-update-v2", "article"]:
                    try:
                        await page.wait_for_selector(selector, timeout=7000)
                        found_selector = selector
                        break
                    except:
                        continue
                
                if not found_selector:
                    print(f"No posts found for keyword '{keyword}' on LinkedIn search page.")
                    await page.screenshot(path="debug_linkedin_no_results.png")
                    await browser.close()
                    return []
                
                post_elements = await page.query_selector_all(found_selector)
                count = 0
                for element in post_elements:
                    if count >= max_posts:
                        break
                    
                    urn = await element.get_attribute("data-urn")
                    # Try more robust text selectors
                    text_el = None
                    for ts in ["div.update-components-text", "span.break-words", ".feed-shared-update-v2__description-wrapper"]:
                        text_el = await element.query_selector(ts)
                        if text_el: break
                    
                    if text_el:
                        text = await text_el.inner_text()
                        url = f"https://www.linkedin.com/feed/update/{urn}/" if urn else page.url
                        scraped_posts.append({
                            "text": text.strip(),
                            "url": url if urn else url,
                            "platform": "linkedin"
                        })
                        count += 1
                        
            except Exception as e:
                print(f"LinkedIn scraping error: {e}")
                await page.screenshot(path="debug_linkedin_error.png")
            finally:
                await browser.close()
                
        return scraped_posts

    async def post_comment(self, post_url, comment_text):
        """Autonomously publish a comment onto a specific LinkedIn post URL"""
        print(f"Autonomously posting to {post_url} on LinkedIn...")
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = await browser.new_page()
            try:
                await page.goto(post_url, wait_until="networkidle")
                
                # Wait for LinkedIn comment box (Quill editor)
                await page.wait_for_selector('div.ql-editor', timeout=15000)
                
                # Sometimes LinkedIn needs a click to focus the box
                await page.click('div.ql-editor')
                await asyncio.sleep(0.5)
                await page.fill('div.ql-editor', comment_text)
                await asyncio.sleep(1.5)
                
                # Click the submit button
                await page.click('button.comments-comment-box__submit-button')
                await asyncio.sleep(4) # Wait for network
                return True
                
            except Exception as e:
                print(f"Failed to post on LinkedIn: {e}")
                return False
            finally:
                await browser.close()

    async def discover_and_connect(self, memory_store, brain_agent, keyword="Support Coordinator", daily_limit=2):
        """Autonomously search for professionals, visit their profiles, and send tailored connection requests."""
        print(f"Autonomous Drone: Searching LinkedIn for un-networked '{keyword}' professionals...")
        connected_count = 0
        logs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = await browser.new_page()
            try:
                search_url = f"https://www.linkedin.com/search/results/people/?keywords={keyword.replace(' ', '%20')}"
                await page.goto(search_url, wait_until="networkidle")
                
                await page.wait_for_selector('a.app-aware-link', timeout=15000)
                await asyncio.sleep(2)
                
                links = await page.eval_on_selector_all(
                    'a.app-aware-link', 
                    "elements => elements.map(el => el.href).filter(href => href.includes('/in/') && !href.includes('/recent-activity/'))"
                )
                unique_profiles = list(set([l.split('?')[0] for l in links]))
                
                for profile_url in unique_profiles:
                    if connected_count >= daily_limit:
                        break
                        
                    if memory_store.has_networked("linkedin", profile_url):
                        continue
                        
                    print(f"Investigating un-networked Profile: {profile_url}")
                    memory_store.record_networked("linkedin", profile_url)
                    
                    await page.goto(profile_url, wait_until="networkidle")
                    await asyncio.sleep(3)
                    
                    # Look for Connect button
                    connect_btn = None
                    for selector in ["button[aria-label^='Invite'][aria-label$='to connect']", "button.pvs-profile-actions__action:has-text('Connect')"]:
                        if await page.locator(selector).count() > 0:
                            connect_btn = page.locator(selector).first
                            break
                    
                    if not connect_btn:
                        continue # Already connected or Message-only
                        
                    await connect_btn.click()
                    await asyncio.sleep(2)
                    
                    # Provide an AI personalized note!
                    add_note_btn = page.locator("button[aria-label='Add a note']")
                    if await add_note_btn.count() > 0:
                        await add_note_btn.click()
                        await asyncio.sleep(1)
                        
                        try:
                            name_el = await page.locator("h1.text-heading-xlarge").first.inner_text()
                            person_name = name_el.split(" ")[0]
                        except:
                            person_name = "there"
                            
                        ans = brain_agent.chat(f"Write a friendly 1-sentence LinkedIn connection request from Good Nurse (an NDIS provider) to someone named {person_name}. It must be under 200 chars total.")
                        await page.fill('textarea[name="message"]', ans)
                        await asyncio.sleep(1)
                        
                        await page.locator("button[aria-label='Send invitation']").click()
                        await asyncio.sleep(3)
                    else:
                        # Direct send
                        send_now = page.locator("button[aria-label='Send now']")
                        if await send_now.count() > 0:
                            await send_now.click()
                            await asyncio.sleep(3)
                        
                    logs.append(f"✅ Sent LinkedIn Connection Request to: [View Profile]({profile_url})")
                    connected_count += 1
                    
            except Exception as e:
                print(f"LinkedIn Drone Error: {e}")
            finally:
                await browser.close()
                
        return logs
