from database import get_random_user
 
from config import BASE_URL, NAVIGATION_TIMEOUT
 
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
 
 
 
def perform_login(page, custom_email=None, custom_password=None):
 
    """Logs a user in, either from newly passed credentials or fetching from the DB."""
 
   
 
    if custom_email and custom_password:
 
        print(f"  -> [Auth] Using newly created credentials for: {custom_email}")
 
        email = custom_email
 
        password = custom_password
 
    else:
 
        print("  -> [Auth] Fetching credentials from local database...")
 
        user = get_random_user()
 
        if not user:
 
            print("  -> [Auth] ERROR: No users found in the local SQLite database. Please run a signup flow first!")
 
            return False
 
        email, password = user
 
 
 
    print(f"  -> [Auth] Attempting login for user: {email}")
 
 
 
    try:
 
        page.goto(f"{BASE_URL}/login", wait_until="load", timeout=NAVIGATION_TIMEOUT)
 
 
 
        page.fill('input[type="email"]', email)
 
        page.fill('input[name="password"]', password)
 
 
 
        print("  -> [Auth] Submitting login credentials...")
 
        page.click('button[type="submit"]')
 
 
 
        page.wait_for_load_state("networkidle", timeout=NAVIGATION_TIMEOUT)
 
 
 
        # Wait for the page to navigate away from the login page
        try:
            page.wait_for_url(lambda url: "/login" not in url.lower(), timeout=15000)
            print("  -> [Debug] Post-Login Success: Redirected away from login page. Session is active!")
            return True
        except PlaywrightTimeoutError:
            print("  -> [Debug] Post-Login Warning: Form submitted, but did not redirect away from /login.")
            return False
 
 
 
    except PlaywrightTimeoutError:
 
        print("  -> [Auth] ERROR: Login execution timed out.")
 
        return False
 
    except Exception as e:
 
        print(f"  -> [Auth] ERROR: An unexpected login failure occurred: {e}")
 
        return False
 
 
 