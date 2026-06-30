import random
import time
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
 
from config import BASE_URL, NAVIGATION_TIMEOUT, SEARCH_TERMS
from core import selectors
from auth.user_generator import generate_user
 
# =====================================================================
# --- CORE HUMAN SIMULATION HELPERS (WITH SMOOTH SCROLLING) ---
# =====================================================================
 
def human_delay(min_sec=2.0, max_sec=5.0):
    """Simulates a human reading or hesitating before an action."""
    time.sleep(random.uniform(min_sec, max_sec))
 
def human_scroll_down(page, total_distance=600, steps=6):
    """Simulates a human smoothly dragging/scrolling down a mobile viewport."""
    print(f"  -> [Action] Smooth scrolling down viewport...")
    try:
        for _ in range(steps):
            increment = total_distance // steps
            variance = random.randint(-15, 15)
            page.evaluate(f"window.scrollBy(0, {increment + variance})")
            time.sleep(random.uniform(0.3, 0.6))  # Human pace between drags
        human_delay(1.0, 2.0)
    except Exception as e:
        print(f"  -> [Action] Warning: Scroll action ran into a minor issue: {e}")
 
def human_click_element(element):
    """Simulates a realistic human click with micro and macro delays."""
    element.scroll_into_view_if_needed()
    human_delay(1.5, 3.0)  # Human reading/thinking time
    element.click(delay=random.randint(80, 300))  # Slower physical mouse press
 
def human_type_element(element, text):
    """Simulates realistic human typing with absolute focus and delays."""
    element.scroll_into_view_if_needed()
    human_delay(1.5, 3.0)
    element.click(delay=random.randint(80, 200))
    element.focus()  # Force absolute focus on input element before typing
    element.fill("")
    element.type(text, delay=random.randint(100, 250)) # Slower typing speed
 
def wait_for_page(page):
    """Wait for network load state, catching timeouts gracefully."""
    try:
        page.wait_for_load_state("load", timeout=NAVIGATION_TIMEOUT)
    except PlaywrightTimeoutError:
        print("  -> [Nav] Page load timeout exceeded, continuing anyway.")
 
# =====================================================================
# --- NAVIGATION & JOURNEYS ---
# =====================================================================
 
def goto_homepage(page):
    """Navigates to the homepage."""
    print("  -> [Nav] Opening Homepage")
    try:
        page.goto(BASE_URL, wait_until="load", timeout=NAVIGATION_TIMEOUT)
    except PlaywrightTimeoutError:
        print("  -> [Nav] Timeout opening homepage, continuing anyway.")
    human_delay(2.0, 4.0)
 
def click_random_category(page):
    """Finds all categories and clicks a random one, scrolling to them on mobile."""
    print("  -> [Nav] Clicking a random category")
    try:
        # 1. MOBILE CHECK: Scroll down slightly to bring category cards into view
        if getattr(page, 'is_mobile', False):
            print("  -> [Nav] Mobile detected: Scrolling down to category cards...")
            human_scroll_down(page, total_distance=300, steps=3)
 
        # 2. Proceed to interact with the category links directly on the page
        page.wait_for_selector(selectors.CATEGORY_SELECTOR, state="attached", timeout=15000)
        categories = page.locator(selectors.CATEGORY_SELECTOR)
       
        if categories.count() > 0:
            idx = random.randint(0, min(categories.count() - 1, 5))
            human_click_element(categories.nth(idx))
            wait_for_page(page)
        else:
            print("  -> [Nav] Warning: No categories found after counting.")
    except Exception:
        print("  -> [Nav] Warning: Timeout waiting for categories to attach to DOM.")
 
def execute_search(page):
    """Opens the mobile menu if necessary, targets the visible input by placeholder, and searches."""
    term = random.choice(SEARCH_TERMS)
    print(f"  -> [Nav] Preparing to search for: {term}")
   
    try:
        # 1. MOBILE CHECK: Open the hamburger menu first to expose search bar
        if getattr(page, 'is_mobile', False):
            print("  -> [Nav] Mobile detected: Opening hamburger menu to expose search bar...")
            mobile_menu_btn = page.get_by_role("button").first
           
            if mobile_menu_btn.count() > 0:
                human_click_element(mobile_menu_btn)
                time.sleep(2.0) # Wait for the CSS menu animation to slide open completely
            else:
                print("  -> [Nav] Warning: Hamburger menu button not found.")
               
            # Find input by its exact placeholder text, and ONLY select the one currently visible on screen
            search_input = page.get_by_placeholder("Search products...").filter(visible=True).first
 
        else:
            # DESKTOP BEHAVIOR: Use the standard selector
            page.wait_for_selector(selectors.SEARCH_INPUT_SELECTOR, state="visible", timeout=15000)
            search_input = page.locator(selectors.SEARCH_INPUT_SELECTOR).first
       
        # Ensure it is interactable
        search_input.wait_for(state="visible", timeout=10000)
       
        # Explicitly click to assert focus inside the newly expanded panel
        search_input.click()
        time.sleep(0.5)
       
        human_type_element(search_input, term)
        search_input.press("Enter", delay=random.randint(80, 200))
       
        wait_for_page(page)
        human_delay(3.0, 5.0)
       
    except PlaywrightTimeoutError:
        print("  -> [Nav] Warning: Timeout waiting for search input to become visible.")
    except Exception as e:
        print(f"  -> [Nav] Search execution error: {e}")
 
def view_random_product(page):
    """Clicks 'View Product' or the product itself on a random item, handling custom landing pages."""
    print("  -> [Nav] Viewing a random product (PDP)")
   
    try:
        # Scroll slightly down the homepage to ensure layout/images lazy-load completely
        human_scroll_down(page, total_distance=400, steps=4)
 
        page.wait_for_selector(selectors.PRODUCT_CARD_SELECTOR, state="visible", timeout=45000)
        cards = page.locator(selectors.PRODUCT_CARD_SELECTOR)
       
        if cards.count() > 0:
            idx = random.randint(0, min(cards.count() - 1, 9))
            selected_card = cards.nth(idx)
           
            view_btn = selected_card.locator(selectors.VIEW_PRODUCT_TEXT).first
            if view_btn.count() > 0:
                human_click_element(view_btn)
            else:
                # FIX: Fallback to the first actual Link inside the card container
                product_link = selected_card.locator("a[href*='/product']").first
                if product_link.count() > 0:
                    human_click_element(product_link)
                else:
                    human_click_element(selected_card)
               
            wait_for_page(page)
 
            # FIX: If we redirected to a product landing page, navigate to the details page
            if "product-landing" in page.url:
                print("  -> [Nav] Landing page detected. Clicking 'View Product' to go to details page...")
                view_prod_btn = page.locator("a:has-text('View Product'), a:has-text('VIEW PRODUCT')").first
                human_click_element(view_prod_btn)
                wait_for_page(page)
        else:
            print("  -> [Nav] Warning: Zero product cards found on page layout.")
           
    except Exception as e:
        print(f"  -> [Nav] Warning: Timeout waiting for product cards to become visible: {e}")
 
def add_to_cart(page):
    """Clicks the Add to Cart button on a product page, protecting against React hydration lag."""
    print("  -> [Nav] Adding item to cart")
    try:
        # SCROLL FIX: Smoothly slide down the PDP page to bring mobile actions into active view
        human_scroll_down(page, total_distance=500, steps=5)
 
        page.wait_for_selector(selectors.ADD_TO_CART_TEXT, state="visible", timeout=15000)
        btn = page.locator(selectors.ADD_TO_CART_TEXT).first
 
        # Wait for React hydration to complete before attempting clicks
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except PlaywrightTimeoutError:
            pass
        human_delay(1.0, 2.0)
       
        # FIX: Retry loop to click and verify via toast or network response
        success = False
        for attempt in range(3):
            try:
                print(f"  -> [Nav] Attempt {attempt + 1}: Clicking Add to Cart...")
                human_click_element(btn)
                # Wait for the success toast message (react-hot-toast uses role="status")
                toast = page.locator("div[role='status']").first
                toast.wait_for(state="visible", timeout=5000)
                success = True
                print("  -> [Nav] Success toast detected! Item successfully added.")
                break
            except Exception:
                print("  -> [Nav] Warning: Success toast not detected. Retrying click...")
                human_delay(1.0, 2.0)
 
        if not success:
            # Final fallback: force-click and use network response as confirmation
            print("  -> [Nav] Final fallback: force-clicking and waiting for cart API response...")
            try:
                with page.expect_response(lambda r: "/api/cart" in r.url or "/cart" in r.url, timeout=10000) as resp_info:
                    btn.click(force=True)
                print(f"  -> [Nav] Cart API responded with status: {resp_info.value.status}")
            except Exception:
                # Last resort: just force click and wait
                btn.click(force=True)
                human_delay(2.0, 3.0)
       
    except PlaywrightTimeoutError:
        print("  -> [Nav] Warning: Timeout waiting for 'Add to Cart' button.")
 
def proceed_to_checkout(page):
    """Clicks Buy Now and waits for the checkout form."""
    print("  -> [Nav] Proceeding to checkout")
    try:
        # Give the cart element processing a quick layout scroll if it's pushed low
        human_scroll_down(page, total_distance=200, steps=2)
 
        page.wait_for_selector(selectors.BUY_NOW_TEXT, state="visible", timeout=15000)
        buy_btn = page.locator(selectors.BUY_NOW_TEXT).first
        human_click_element(buy_btn)
        wait_for_page(page)
       
    except PlaywrightTimeoutError:
        print("  -> [Nav] Warning: Timeout waiting for 'Buy Now' button.")
 
def fill_checkout_form(page):
    """Generates fake data and waits for the checkout form using precise selectors."""
    print("  -> [Nav] Waiting for checkout form to become visible and interactive...")
    try:
        page.wait_for_selector('input[name="name-input"]', state="visible", timeout=45000)
        print("  -> [Nav] React checkout form rendered! Processing fields...")
        human_delay(1.0, 2.0)
    except PlaywrightTimeoutError:
        print("  -> [Nav] ERROR: Checkout form elements did not become visible within the timeout limit.")
        return
       
    user = generate_user()
    try:
        if page.locator('input[name="phone-input"]').count() > 0:
            page.fill('input[name="phone-input"]', "9400000000")
 
        if page.locator('input[name="name-input"]').count() > 0 and page.locator('input[name="name-input"]').input_value() == "":
            page.fill('input[name="name-input"]', user["firstname"])
            time.sleep(0.2)
           
        if page.locator('input[name="lastname-input"]').count() > 0 and page.locator('input[name="lastname-input"]').input_value() == "":
            page.fill('input[name="lastname-input"]', user["lastname"])
            time.sleep(0.2)
           
        # SCROLL FIX PART 2: Scroll down mid-way through the long mobile checkout form
        human_scroll_down(page, total_distance=400, steps=4)
 
        if page.locator('input[name="email-address"]').count() > 0 and page.locator('input[name="email-address"]').input_value() == "":
            page.fill('input[name="email-address"]', user["email"])
            time.sleep(0.2)
           
        if page.locator('input[name="company"]').count() > 0 and page.locator('input[name="company"]').input_value() == "":
            page.fill('input[name="company"]', user["company"])
            time.sleep(0.2)
           
        if page.locator('input[name="address"]').count() > 0 and page.locator('input[name="address"]').input_value() == "":
            page.fill('input[name="address"]', user["addressline"])
            time.sleep(0.2)
           
        if page.locator('input[name="apartment"]').count() > 0 and page.locator('input[name="apartment"]').input_value() == "":
            page.fill('input[name="apartment"]', user["apartment"])
            time.sleep(0.2)
           
        # Final block form scroll down
        human_scroll_down(page, total_distance=350, steps=3)
 
        if page.locator('input[name="city"]').count() > 0 and page.locator('input[name="city"]').input_value() == "":
            page.fill('input[name="city"]', user["city"])
            time.sleep(0.2)
           
        if page.locator('input[name="region"]').count() > 0 and page.locator('input[name="region"]').input_value() == "":
            page.fill('input[name="region"]', "United States")
            time.sleep(0.2)
           
        if page.locator('input[name="postal-code"]').count() > 0 and page.locator('input[name="postal-code"]').input_value() == "":
            page.fill('input[name="postal-code"]', user["postalcode"])
           
        print("  -> [Nav] Checkout form validation complete.")
        human_delay(2.0, 4.0)
       
    except Exception as e:
        print(f"  -> [Nav] Checkout form fill error: {e}")
 
def place_order(page):
    """Clicks Place Order to complete a purchase, safely waiting for API resolution."""
    print("  -> [Nav] Placing order")
   
    try:
        # 1. Scroll down to make sure the Place Order button is visible
        human_scroll_down(page, total_distance=600, steps=4)
 
        # 2. Wait for the button to be ready
        page.wait_for_selector(selectors.PLACE_ORDER_TEXT, state="visible", timeout=15000)
        place_btn = page.locator(selectors.PLACE_ORDER_TEXT).first
       
        print("  -> [Nav] Clicking Place Order button and waiting for API response...")
       
        # 3. Click the button (PostHog will intercept and we don't want false positives)
        # Using force=True internally by dispatching event if it's covered by floating UI
        try:
            human_click_element(place_btn)
        except Exception:
            place_btn.click(force=True, delay=200)
           
        print("  -> [Nav] Waiting for React to redirect to /thank-you...")
        try:
            page.wait_for_url("**/thank-you*", timeout=20000)
            print("  -> [Nav] API confirmed order! Redirected to thank you page.")
            human_delay(2.0, 3.0)
        except PlaywrightTimeoutError:
            print("  -> [Nav] Thank-you redirect did not occur. Checking for validation errors...")
            # Capture full page screenshot to debug validation errors
            import os
            os.makedirs("screenshots", exist_ok=True)
            page.screenshot(path="screenshots/checkout_failed.png", full_page=True)
            print("  -> [Nav] Captured screenshots/checkout_failed.png to inspect form validation errors.")
           
            # Last resort: check for any toast message indicating success/failure
            toast = page.locator("div[role='status']").first
            try:
                toast.wait_for(state="visible", timeout=3000)
                print(f"  -> [Nav] Toast notification detected: {toast.text_content().strip()}")
            except Exception:
                print("  -> [Nav] WARNING: No confirmation detected. Order status is uncertain.")
            human_delay(2.0, 3.0)
           
    except PlaywrightTimeoutError:
        print("  -> [Nav] ERROR: The checkout process timed out. The server took too long to respond.")
    except Exception as e:
        print(f"  -> [Nav] ERROR: An unexpected issue occurred during checkout: {e}")
 
 
 