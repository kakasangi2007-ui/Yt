import os
import time
from playwright.sync_api import sync_playwright, TimeoutError

VIDEO_DIR = "shorts"

def safe_click(page, selector):
    try:
        page.wait_for_selector(selector, timeout=15000)
        page.click(selector)
    except TimeoutError:
        print(f"[WARN] Selector not found: {selector}")


def upload_short(video_path, title, description="#shorts"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state="playwright/.auth/storage.json")
        page = context.new_page()

        print("⏳ Opening upload page...")
        page.goto("https://www.youtube.com/upload", timeout=0)

        # Upload file
        print("📤 Uploading video...")
        page.set_input_files("input[type='file']", video_path)

        time.sleep(10)  # Wait for processing

        # Title
        print("📝 Setting title...")
        safe_click(page, "textarea#title-textarea")
        page.fill("textarea#title-textarea", title)

        # Description
        print("📝 Setting description...")
        safe_click(page, "textarea#description-textarea")
        page.fill("textarea#description-textarea", description)

        # Audience
        print("👶 Audience...")
        safe_click(page, "#audience > ytcp-video-metadata-editor-audience-select")
        safe_click(page, "tp-yt-paper-radio-button[name='NOT_MADE_FOR_KIDS']")

        # Next buttons
        print("➡️ Clicking Next…")
        for _ in range(3):
            safe_click(page, "ytcp-button:has-text('Next')")
            time.sleep(2)

        # Publish
        print("🚀 Publishing...")
        safe_click(page, "ytcp-button:has-text('Publish')")

        time.sleep(8)
        browser.close()
        print("✅ Upload finished!")


def main():
    for file in os.listdir(VIDEO_DIR):
        if file.endswith(".mp4"):
            path = os.path.join(VIDEO_DIR, file)
            title = os.path.splitext(file)[0]
            upload_short(path, title)
            os.remove(path)


if __name__ == "__main__":
    main()
