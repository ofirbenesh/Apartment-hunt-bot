import re
from pathlib import Path
from loguru import logger
from playwright.sync_api import sync_playwright, Playwright, BrowserContext, Page


BROWSER_DATA_DIR = str(Path(__file__).parent.parent / ".fb_browser_data")


class FacebookScraper:
    def __init__(self, settings: dict, email: str, password: str):
        self.email    = email
        self.password = password
        self.headless = settings.get("facebook", {}).get("headless", False)
        self._playwright: Playwright     = None
        self._context:    BrowserContext = None
        self._page:       Page           = None

    def start(self):
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=BROWSER_DATA_DIR,
            headless=self.headless,
            locale="he-IL",
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        self._page = self._context.new_page()
        self._ensure_logged_in()

    def stop(self):
        if self._context:
            self._context.close()
        if self._playwright:
            self._playwright.stop()

    def scrape_group(self, group_url: str) -> list[dict]:
        try:
            self._page.goto(group_url, wait_until="domcontentloaded", timeout=30000)
            self._page.wait_for_selector('[role="article"]', timeout=15000)
            self._page.wait_for_timeout(2000)
            posts = self._extract_posts()
            logger.info(f"Scraped {len(posts)} posts from {group_url}")
            return posts
        except Exception as e:
            logger.error(f"Failed to scrape {group_url}: {e}")
            return []

    # ------------------------------------------------------------------ #

    def _ensure_logged_in(self):
        self._page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        self._page.wait_for_timeout(2000)
        if self._is_logged_out():
            logger.info("Not logged in — logging in now")
            self._login()
        else:
            logger.info("Facebook session active")

    def _is_logged_out(self) -> bool:
        url = self._page.url
        return "login" in url or self._page.locator("#email").is_visible()

    def _is_checkpoint(self) -> bool:
        url = self._page.url
        return any(word in url for word in ("checkpoint", "two_step", "verification", "security"))

    def _login(self):
        self._page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")
        self._page.fill("#email", self.email)
        self._page.fill("#pass", self.password)
        self._page.click('[name="login"]')
        self._page.wait_for_timeout(4000)

        # Facebook may show a 2FA / security checkpoint — let the user handle it manually
        if self._is_logged_out() or self._is_checkpoint():
            print("\n" + "=" * 60)
            print("ACTION REQUIRED — look at the browser window that opened.")
            print("Complete any 2FA code, CAPTCHA, or security check Facebook shows.")
            print("The bot will continue automatically once you are logged in.")
            print("You have 5 minutes.")
            print("=" * 60 + "\n")
            logger.info("Waiting for manual login completion (2FA / checkpoint)...")

            # Poll every 5 seconds for up to 5 minutes
            for _ in range(60):
                self._page.wait_for_timeout(5000)
                if not self._is_logged_out() and not self._is_checkpoint():
                    break
            else:
                raise RuntimeError(
                    "Login timed out after 5 minutes. "
                    "Please re-run the bot and complete the Facebook login promptly."
                )

        if self._is_logged_out():
            raise RuntimeError("Facebook login failed — check your email and password in .env")

        logger.info("Facebook login successful — session saved for future runs")

    def _extract_posts(self) -> list[dict]:
        posts: list[dict] = []
        seen_ids: set[str] = set()
        for article in self._page.locator('[role="article"]').all():
            try:
                post = self._extract_one(article)
                if post and post["post_id"] not in seen_ids:
                    seen_ids.add(post["post_id"])
                    posts.append(post)
            except Exception as e:
                logger.debug(f"Skipped article: {e}")
        return posts

    def _extract_one(self, article) -> dict | None:
        permalink = None
        for selector in ['a[href*="/posts/"]', 'a[href*="/permalink/"]']:
            links = article.locator(selector).all()
            if links:
                href = links[0].get_attribute("href")
                if href:
                    permalink = href
                    break
        if not permalink:
            return None
        post_id = self._post_id(permalink)
        if not post_id:
            return None
        return {
            "post_id":  post_id,
            "post_url": self._clean_url(permalink),
            "text":     article.inner_text(),
            "author":   self._extract_author(article),
        }

    @staticmethod
    def _post_id(url: str):
        m = re.search(r"/(?:posts|permalink)/(\d+)", url)
        return m.group(1) if m else None

    @staticmethod
    def _clean_url(url: str) -> str:
        base = url.split("?")[0]
        if not base.startswith("http"):
            base = "https://www.facebook.com" + base
        return base

    @staticmethod
    def _extract_author(article) -> str:
        try:
            strong = article.locator("strong").first
            if strong.count() and strong.is_visible():
                return strong.inner_text().strip()
        except Exception:
            pass
        return ""
