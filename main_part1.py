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
 
def generate_user_flows():
    """
    Generates a fully dynamic list of random user flows (150-250) for Desktop traffic.
    Applies a two-level randomized distribution (Journeys first, then Auth-type),
    with deterministic rounding correction to maintain exact bot counts.
    """
    total_users = random.randint(150, 250)
   
    journey_ranges = {
        "bounce": (22, 28),
        "category_browse": (12, 16),
        "search_discovery": (6, 9),
        "search_discovery_success": (3, 5),
        "product_explore": (10, 14),
        "cart_abandon": (12, 16),
        "checkout_abandon": (6, 9),
        "successful_purchase": (7, 10),
        "deal_hunter": (8, 11),
        "deal_hunter_success": (3, 5)
    }
   
    # 1. Generate and Normalize Journey Percentages
    raw_percentages = {j: random.uniform(r[0], r[1]) for j, r in journey_ranges.items()}
    total_raw = sum(raw_percentages.values())
    normalized_percentages = {j: raw / total_raw for j, raw in raw_percentages.items()}
   
    # 2. Allocate Bots per Journey (with rounding correction)
    journey_bots = {}
    allocated_bots = 0
    for j, pct in normalized_percentages.items():
        bots = int(round(total_users * pct))
        journey_bots[j] = bots
        allocated_bots += bots
       
    diff = total_users - allocated_bots
    if diff != 0:
        largest_journey = max(journey_bots, key=journey_bots.get)
        journey_bots[largest_journey] += diff
       
    pool = []
   
    # 3. Sub-allocate User Types per Journey
    for journey, bots in journey_bots.items():
        if bots == 0:
            continue
           
        guest_pct = random.uniform(55, 65)
        sign_pct = random.uniform(5, 10)
        ret_pct = 100.0 - (guest_pct + sign_pct)
        
        guest_bots = int(round(bots * (guest_pct / 100.0)))
        signup_bots = int(round(bots * (sign_pct / 100.0)))
        returning_bots = bots - (guest_bots + signup_bots)
        
        if returning_bots < 0:
            signup_bots += returning_bots
            returning_bots = 0
            if signup_bots < 0:
                guest_bots += signup_bots
                signup_bots = 0
           
        user_types = (
            ["returning_logged_in"] * returning_bots +
            ["new_signup"] * signup_bots +
            ["guest"] * guest_bots
        )
        random.shuffle(user_types)
       
        for u in user_types:
            pool.append({
                "user_type": u,
                "journey": journey
            })
           
    random.shuffle(pool)
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
    print("   DAILY DESKTOP TRAFFIC DISTRIBUTION SUMMARY")
    print("==================================================")
    print(f"Total Desktop Bots Generated: {total}")
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
    print("   SINGITRONIC TRAFFIC ENGINE: DESKTOP WRAPPER")
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
                print(f"  -> Initiating Desktop Flow | Auth: {user_type} | Journey: {journey_name}")
               
                context = None
                try:
                    # Device Emulation Setup (Desktop 1920x1080)
                    context_kwargs = build_context_options()
                    context_kwargs.update({
                        'viewport': {'width': 1920, 'height': 1080},
                        'user_agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                    })
                   
                    # Create isolated context
                    context = browser.new_context(**context_kwargs)
                    
                    page = context.new_page()
                    page.is_mobile = False
                   
                    # Telemetry/Analytics Monitoring
                    analytics_monitor = AnalyticsMonitor(f"Desktop Session #{user_id}")
                    analytics_monitor.attach(page)
                   
                    # Auth Execution
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
                           
                    # Journey Execution
                    journey_module = JOURNEY_MAP.get(journey_name)
                    if journey_module:
                        journey_module.run_journey(page)
                       
                    # Flush and Log Success
                    wait_for_analytics_flush(page, f"Desktop Session #{user_id}")
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
            print(f"   SUCCESS: ALL {TOTAL_USERS} DESKTOP BOTS COMPLETED")
            print(f"   Successfully Executed: {len(successful_runs)}")
            print("==================================================")
           
        except Exception as e:
            print(f"Critical error during execution: {e}")
           
        finally:
            if browser:
                browser.close()
 
if __name__ == "__main__":
    main()