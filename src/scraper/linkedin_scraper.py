"""
LinkedIn Job Scraper using Playwright (headless browser).
Scrapes public LinkedIn Jobs search without requiring login.
"""
import asyncio
import re
import urllib.parse
from dataclasses import dataclass, asdict
from typing import Optional

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout
from src.utils.logger import log


@dataclass
class Job:
    job_id: str
    title: str
    company: str
    location: str
    url: str
    posted_time: str
    description_snippet: str
    salary: Optional[str] = None


def build_search_url(keyword: str, location: str, date_posted: str,
                     experience_level: str, job_type: str) -> str:
    """Build LinkedIn Jobs search URL with filters."""
    base = "https://www.linkedin.com/jobs/search/"
    params = {
        "keywords": keyword,
        "location": location,
        "f_TPR": date_posted,          # Time posted (r86400 = last 24h)
        "f_E": experience_level,        # Experience: 2 = Entry level
        "f_JT": job_type,              # Job type: F = Full-time
        "f_WT": "1",                   # Workplace type: 1 = On-site
        "sortBy": "DD",                # Sort by: DD = Most recent
    }
    return base + "?" + urllib.parse.urlencode(params)


def extract_job_id(url: str) -> str:
    """Extract job ID from LinkedIn job URL."""
    match = re.search(r"/jobs/view/(\d+)", url)
    if match:
        return match.group(1)
    # Fallback: use URL hash
    return str(hash(url))


async def scrape_jobs_for_keyword(
    page: Page,
    keyword: str,
    location: str,
    date_posted: str,
    experience_level: str,
    job_type: str,
    max_jobs: int = 25,
    scroll_count: int = 5,
) -> list[dict]:
    """Scrape jobs for a single keyword."""
    url = build_search_url(keyword, location, date_posted, experience_level, job_type)
    log.info(f"Scraping: {keyword} | URL: {url}")

    jobs = []
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        # Handle cookie/sign-in modal if present
        try:
            dismiss = page.locator('[data-tracking-control-name="public_jobs_contextual-sign-in-modal_modal_dismiss"]')
            if await dismiss.count() > 0:
                await dismiss.first.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

        # Scroll to load more jobs
        for i in range(scroll_count):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)
            log.debug(f"Scroll {i+1}/{scroll_count}")

        # Extract job cards — try multiple selectors (LinkedIn changes HTML structure often)
        job_cards = page.locator(
            "ul.jobs-search__results-list > li, "
            "div.jobs-search__results-list > ul > li, "
            "li.jobs-search-results__list-item"
        )
        count = await job_cards.count()
        log.info(f"Found {count} job cards for '{keyword}'")

        for i in range(min(count, max_jobs)):
            try:
                card = job_cards.nth(i)

                # Title — multiple fallback selectors
                title = ""
                for title_sel in [
                    "h3.base-search-card__title",
                    "h3.job-search-card__title",
                    "a[data-tracking-control-name] span[aria-hidden]",
                    "h3",
                ]:
                    title_el = card.locator(title_sel).first
                    if await title_el.count() > 0:
                        title = (await title_el.text_content() or "").strip()
                        if title:
                            break

                # Company — multiple fallback selectors
                company = ""
                for comp_sel in [
                    "h4.base-search-card__subtitle",
                    "h4.job-search-card__company-name",
                    "a[data-tracking-control-name*='company']",
                    "h4",
                ]:
                    comp_el = card.locator(comp_sel).first
                    if await comp_el.count() > 0:
                        company = (await comp_el.text_content() or "").strip()
                        if company:
                            break

                # Location
                loc = ""
                for loc_sel in [
                    "span.job-search-card__location",
                    "span[class*='location']",
                ]:
                    loc_el = card.locator(loc_sel).first
                    if await loc_el.count() > 0:
                        loc = (await loc_el.text_content() or "").strip()
                        if loc:
                            break

                # Posted time
                posted_text = ""
                time_el = card.locator("time").first
                if await time_el.count() > 0:
                    posted_text = (await time_el.text_content() or "").strip()
                    if not posted_text:
                        posted_text = (await time_el.get_attribute("datetime") or "").strip()

                # URL — find the main job link
                href = ""
                for link_sel in [
                    "a.base-card__full-link",
                    "a[href*='/jobs/view/']",
                    "a[data-tracking-control-name*='search_srp']",
                    "a[href*='linkedin.com/jobs']",
                ]:
                    link_el = card.locator(link_sel).first
                    if await link_el.count() > 0:
                        href = (await link_el.get_attribute("href") or "").strip()
                        if href:
                            break

                clean_url = href.split("?")[0] if href else ""

                # Salary (if shown)
                salary = None
                salary_el = card.locator("span.job-search-card__salary-info").first
                if await salary_el.count() > 0:
                    salary = (await salary_el.text_content() or "").strip()

                if not title or not clean_url:
                    log.debug(f"Skipping card {i}: missing title or URL")
                    continue

                job_id = extract_job_id(clean_url) or str(hash(clean_url))

                job = Job(
                    job_id=job_id,
                    title=title,
                    company=company,
                    location=loc,
                    url=clean_url,
                    posted_time=posted_text,
                    description_snippet="",
                    salary=salary,
                )
                jobs.append(asdict(job))

            except Exception as e:
                log.warning(f"Error parsing card {i}: {e}")
                continue

    except PWTimeout:
        log.error(f"Timeout scraping '{keyword}'")
    except Exception as e:
        log.error(f"Error scraping '{keyword}': {e}")

    log.success(f"Scraped {len(jobs)} jobs for '{keyword}'")
    return jobs


async def run_scraper(config: dict) -> list[dict]:
    """Main scraper entry point. Returns all new jobs."""
    linkedin_cfg = config["linkedin"]
    scraper_cfg = config.get("scraper", {})

    keywords = linkedin_cfg["keywords"]
    location = linkedin_cfg["location"]
    date_posted = linkedin_cfg.get("date_posted", "r86400")
    experience_level = linkedin_cfg.get("experience_level", "2")
    job_type = linkedin_cfg.get("job_type", "F")
    max_jobs = scraper_cfg.get("max_jobs_per_keyword", 25)
    scroll_count = scraper_cfg.get("scroll_count", 5)
    headless = scraper_cfg.get("headless", True)

    all_jobs = []
    seen_ids = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = await context.new_page()

        # Block unnecessary resources to speed up
        await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2}", lambda r: r.abort())

        for keyword in keywords:
            jobs = await scrape_jobs_for_keyword(
                page=page,
                keyword=keyword,
                location=location,
                date_posted=date_posted,
                experience_level=experience_level,
                job_type=job_type,
                max_jobs=max_jobs,
                scroll_count=scroll_count,
            )
            # Deduplicate across keywords
            for job in jobs:
                if job["job_id"] not in seen_ids:
                    seen_ids.add(job["job_id"])
                    all_jobs.append(job)
            
            # Be polite between requests
            await asyncio.sleep(2)

        await browser.close()

    log.info(f"Total unique jobs scraped: {len(all_jobs)}")
    return all_jobs
