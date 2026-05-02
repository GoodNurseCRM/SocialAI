import os
import asyncio
from playwright.async_api import async_playwright

class InstagramAgent:
    def __init__(self, user_data_dir="./browser_profiles/ig_profile"):
        self.user_data_dir = user_data_dir
        os.makedirs(self.user_data_dir, exist_ok=True)
        
    async def fetch_hashtag_posts(self, hashtag="ndisaustralia", max_posts=2):
        scraped_posts = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            page = await browser.new_page()
            
            print(f"Navigating to Instagram hashtag: #{hashtag}")
            try:
                tag_url = f"https://www.instagram.com/explore/tags/{hashtag}/"
                await page.goto(tag_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(5)
                
                # REPRODUCIBLE LOGIN CHECK: Check for Instagram logo or navigation
                is_logged_in = await page.locator("svg[aria-label='Instagram']").count() > 0 or await page.locator("nav").count() > 0
                if not is_logged_in:
                    if "login" in page.url or await page.locator("input[name='username']").count() > 0:
                        print("Error: Not logged into Instagram. Redirected to login page.")
                        await page.screenshot(path="instagram_login_wall.png")
                        await browser.close()
                        return [{"error": "not_logged_in"}]
                
                # Wait for post elements
                found_selector = None
                for selector in ["article a", "div._ac7v a", "div._aabd a"]:
                    try:
                        await page.wait_for_selector(selector, timeout=10000)
                        found_selector = selector
                        break
                    except:
                        continue
                
                if not found_selector:
                    print(f"No posts found for hashtag #{hashtag} on Instagram.")
                    await page.screenshot(path="debug_instagram_no_results.png")
                    await browser.close()
                    return []
                
                post_elements = await page.query_selector_all(found_selector)
                post_urls = []
                for element in post_elements[:max_posts]:
                    href = await element.get_attribute("href")
                    if href:
                        post_urls.append(f"https://www.instagram.com{href}")
                
                for url in post_urls:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(3) # Prevent rapid scraping bans
                    
                    # Grab caption (usually first h1 or a specific div)
                    try:
                        # Try first h1 (caption) or comet-style caption
                        text = await page.locator('h1').first.inner_text(timeout=5000)
                    except:
                        try:
                            text = await page.locator('div[data-testid="post-comment-root"]').first.inner_text(timeout=5000)
                        except:
                            text = "No caption found"
                        
                    scraped_posts.append({
                        "text": text,
                        "url": url,
                        "platform": "instagram"
                    })
                    
            except Exception as e:
                print(f"Instagram scraping error: {e}")
                await page.screenshot(path="debug_instagram_error.png")
            finally:
                await browser.close()
                
        return scraped_posts

    async def post_comment(self, post_url, comment_text):
        """Autonomously publish a comment onto a specific Instagram post URL"""
        print(f"Autonomously posting to {post_url} on Instagram...")
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            page = await browser.new_page()
            try:
                await page.goto(post_url, wait_until="networkidle")
                
                await page.wait_for_selector('textarea[aria-label="Add a comment…"]', timeout=15000)
                await page.fill('textarea[aria-label="Add a comment…"]', comment_text)
                await asyncio.sleep(1) # Humanize delay
                
                # The post button appears after typing
                await page.locator('div[role="button"]:has-text("Post")').click()
                await asyncio.sleep(4) # Wait for network confirmation
                
                return True
                
            except Exception as e:
                print(f"Failed to post on Instagram: {e}")
                return False
            finally:
                await browser.close()
