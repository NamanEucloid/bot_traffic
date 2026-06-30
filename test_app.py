import os
import time
import random
from datetime import datetime
from collections import defaultdict
from playwright.sync_api import sync_playwright
 
from core.browser_runtime import build_context_options
from core.analytics import AnalyticsMonitor, wait_for_analytics_flush
 
# Import auth functions
from auth.signup import perform_signup
from auth.login import perform_login
 
# Import all built journey modules
from journeys import (
    bounce, category_browse, search_discovery, search_discovery_success,
    product_explore, cart_abandon, checkout_abandon, successful_purchase,
    deal_hunter, deal_hunter_success
)
 
JOURNEY_MAP = {
    "bounce": bounce,
    "category_browse": category_browse,
    "search_discovery": search_discovery,
    "search_discovery_success": search_discovery_success,
    "product_explore": product_explore,
    "cart_abandon": cart_abandon,
    "checkout_abandon": checkout_abandon,
    "successful_purchase": successful_purchase,
    "deal_hunter": deal_hunter,
    "deal_hunter_success": deal_hunter_success
}
 
CHUNK_SIZE = 10
 
def generate_user_flows():
    """
    Generates a small test list of random user flows (10-12) for App traffic.
    Guarantees that EVERY journey is covered exactly once, distributing any
    remaining bots randomly. Also maintains the authentication split.
    """
    total_users = random.randint(10, 12)
   
    # 1. Guarantee exactly 1 bot per journey to cover all 10 journeys
    journey_names = [
        "bounce", "category_browse", "search_discovery", "search_discovery_success",
        "product_explore", "cart_abandon", "checkout_abandon", "successful_purchase",
        "deal_hunter", "deal_hunter_success"
    ]
   
    # Add any extra bots to reach total_users (randomly)
    extra_bots = total_users - len(journey_names)
    if extra_bots > 0:
        journey_names.extend(random.choices(journey_names, k=extra_bots))
       
    random.shuffle(journey_names)
   
    # 2. Calculate Auth Split for the 10-12 bots
    # Roughly 75% Returning, 5% Signup, 20% Guest
    logged_in_count = int(round(total_users * 0.75))
    signup_count = int(round(total_users * 0.05))
    guest_count = total_users - (logged_in_count + signup_count)
   
    user_types = (
        ["returning_logged_in"] * logged_in_count +
        ["new_signup"] * signup_count +
        ["guest"] * guest_count
    )
    random.shuffle(user_types)
   
    # 3. Zip them together
    pool = []
    for i in range(total_users):
        pool.append({
            "user_type": user_types[i],
            "journey": journey_names[i]
        })
       
    return pool
 
def print_distribution_summary(pool):
    total = len(pool)
    type_summary = defaultdict(int)
    journey_summary = defaultdict(lambda: defaultdict(int))
   
    for session in pool:
        u_type = session['user_type']
        j_name = session['journey']
        type_summary[u_type] += 1
        journey_summary[j_name]['total'] += 1
        journey_summary[j_name][u_type] += 1
       
    print("\n==================================================")
    print("   DAILY APP TRAFFIC DISTRIBUTION SUMMARY")
    print("==================================================")
    print(f"Total App Bots Generated: {total}")
    print(f"Overall Auth Split:")
    print(f"  -> Returning Logged-In : {type_summary['returning_logged_in']}")
    print(f"  -> New Signups         : {type_summary['new_signup']}")
    print(f"  -> Logged-Out Guests   : {type_summary['guest']}")
    print("\nDetailed Journey Breakdown:")
   
    # Sort journeys by count descending
    for j_name, stats in sorted(journey_summary.items(), key=lambda x: x[1]['total'], reverse=True):
        j_total = stats['total']
        j_ret = stats['returning_logged_in']
        j_sign = stats['new_signup']
        j_guest = stats['guest']
       
        pct_of_total = round((j_total / total) * 100, 1)
        print(f"  [{j_name.upper()}] - Total: {j_total} ({pct_of_total}%)")
        print(f"      Auth: {j_ret} Returning | {j_sign} Signup | {j_guest} Guest")
    print("==================================================\n")
 
def main():
    print("==================================================")
    print("   SINGITRONIC TRAFFIC ENGINE: APP WRAPPER")
    print("==================================================\n")
   
    cdp_url = os.environ.get("CHROME_CDP", "http://127.0.0.1:9222")
    user_flows = generate_user_flows()
    TOTAL_USERS = len(user_flows)
   
    print_distribution_summary(user_flows)
    time.sleep(2)
   
    successful_runs = []
   
    with sync_playwright() as p:
        browser = None
        try:
            print(f"Connecting to Chrome remote instance via CDP at: {cdp_url}")
            browser = p.chromium.connect_over_cdp(cdp_url)
           
            # Process bots strictly sequentially, one by one
            for i in range(TOTAL_USERS):
                user_id = i + 1
                config = user_flows[i]
                user_type = config["user_type"]
                journey_name = config["journey"]
               
                print(f"\n>>> Starting Bot #{user_id} of {TOTAL_USERS} <<<")
                print(f"  -> Initiating App Flow | Auth: {user_type} | Journey: {journey_name}")
               
                context = None
                try:
                    # 1. Device Emulation Setup
                    context_kwargs = build_context_options()
                    pixel_7_device = p.devices['Pixel 7']
                    context_kwargs.update(pixel_7_device)
                   
                    # Add extra header (excluding X-Requested-With to avoid CORS issues)
                    extra_headers = context_kwargs.get("extra_http_headers", {})
                    context_kwargs["extra_http_headers"] = extra_headers
                   
                    # Create isolated context
                    context = browser.new_context(**context_kwargs)
                   
                    # 2. Capacitor Bridge Injection (CRITICAL)
                    context.add_init_script("""
                        window.androidBridge = {
                            postMessage: function(data) { console.log("Spoofed Android Bridge received:", data); }
                        };
                        (function() {
                            var _cap = {
                                platform: 'android',
                                isNativePlatform: function() { return true; },
                                getPlatform: function() { return 'android'; },
                                isPluginAvailable: function() { return true; },
                                Plugins: {}
                            };
                            Object.defineProperty(window, 'Capacitor', {
                                get: function() { return _cap; },
                                set: function() { /* silently ignore */ },
                                configurable: false
                            });
                        })();
                    """)
                   
                    page = context.new_page()
                    page.is_mobile = True
                   
                    # 3. Telemetry/Analytics Monitoring
                    analytics_monitor = AnalyticsMonitor(f"App Session #{user_id}")
                    analytics_monitor.attach(page)
                   
                    # 4. Auth Execution
                    if user_type == "returning_logged_in":
                        print(f"  -> [Bot #{user_id}] Authenticating returning user...")
                        if not perform_login(page):
                            print(f"  -> [Bot #{user_id}] Login failed. Aborting.")
                            continue
                    elif user_type == "new_signup":
                        print(f"  -> [Bot #{user_id}] Executing guest signup...")
                        creds = perform_signup(page)
                        if creds:
                            perform_login(page, custom_email=creds[0], custom_password=creds[1])
                           
                    # 5. Journey Execution
                    journey_module = JOURNEY_MAP.get(journey_name)
                    if journey_module:
                        journey_module.run_journey(page)
                       
                    # 6. Flush and Log Success
                    wait_for_analytics_flush(page, f"App Session #{user_id}")
                    time.sleep(3.0)
                    analytics_monitor.print_summary()
                   
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"  -> [Bot #{user_id}] Journey {journey_name} completed successfully at {timestamp}")
                    successful_runs.append(journey_name)
                   
                except Exception as e:
                    print(f"  -> [Bot #{user_id}] Flow execution failed: {e}")
                   
                finally:
                    # Clean up context strictly immediately after each bot
                    print(f"  -> Cleaning up browser context for Bot #{user_id}...")
                    if context:
                        try:
                            context.close()
                        except Exception:
                            pass
                           
            print("\n==================================================")
            print(f"   SUCCESS: ALL {TOTAL_USERS} APP BOTS COMPLETED")
            print(f"   Successfully Executed: {len(successful_runs)}")
            print("==================================================")
           
        except Exception as e:
            print(f"Critical error during execution: {e}")
           
        finally:
            if browser:
                browser.close()
 
if __name__ == "__main__":
    main()
 
 
 