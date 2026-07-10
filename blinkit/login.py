import json
from datetime import datetime
from playwright.sync_api import sync_playwright

with sync_playwright() as p:

    browser = p.chromium.launch(headless=False)

    context = browser.new_context()

    page = context.new_page()

    page.goto("https://blinkit.com")

    print("Log into Blinkit manually...")

    input("Press ENTER after login is complete...")

    context.storage_state(path="storage.json")

    browser.close()

    print("Session saved!")

    # Write the login timestamp to last_login.json
    login_data = {
        "time": datetime.now().isoformat()
    }
    with open("last_login.json", "w", encoding="utf-8") as f:
        json.dump(login_data, f)
    
    print("Login timestamp saved to last_login.json")
