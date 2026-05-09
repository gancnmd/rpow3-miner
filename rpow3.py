#!/usr/bin/env python3
"""
RPOW3 Multi-Account Miner CLI
A tribute to Hal Finney's RPOW - mine rpow3 tokens with multiple accounts.

Usage:
    python3 rpow3.py                    # Start mining with config.json
    python3 rpow3.py --add <email>      # Add account and send magic link
    python3 rpow3.py --verify <url>     # Verify magic link
    python3 rpow3.py --balance          # Check all balances
    python3 rpow3.py --accounts         # List configured accounts
    python3 rpow3.py --remove <email>   # Remove account

Setup:
    1. pip install (no deps needed, uses stdlib only)
    2. python3 rpow3.py --add your@email.com
    3. Click the magic link in your email
    4. python3 rpow3.py --verify "https://api.rpow3.com/auth/verify?token=..."
    5. python3 rpow3.py                # Start mining!

Author: Jack (https://github.com/gancnmd)
License: MIT
"""

import hashlib
import json
import multiprocessing
import os
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path

VERSION = "1.0.0"
API = "https://api.rpow3.com"
CONFIG_FILE = Path(__file__).parent / "accounts.json"
LOG_FILE = Path(__file__).parent / "miner.log"

# ANSI colors
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

def banner():
    print(f"""{C.CYAN}{C.BOLD}
╔══════════════════════════════════════════════════╗
║   RPOW3 Miner CLI v{VERSION:<29s}║
║   Multi-account parallel mining                   ║
║   A tribute to Hal Finney's RPOW                  ║
╚══════════════════════════════════════════════════╝{C.RESET}
""")

# ─── API Layer ───────────────────────────────────────────────────
def api_request(path, cookie=None, method="GET", data=None):
    """Make API request via curl (no dependencies)."""
    cmd = ["curl", "-s", "-m", "30", "-X", method, f"{API}{path}"]
    if cookie:
        cmd += ["-H", f"Cookie: rpow_session={cookie}"]
    cmd += ["-H", "Origin: https://rpow3.com"]
    if method == "POST":
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data or {})]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        return json.loads(r.stdout) if r.stdout.strip() else None
    except Exception:
        return None

def request_magic_link(email):
    """Send magic link to email."""
    return api_request("/auth/request", method="POST", data={"email": email})

def verify_link(url):
    """Verify magic link and extract cookie."""
    cmd = ["curl", "-s", "-m", "15", "-o", "/dev/null", "-D", "-", url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    for line in r.stdout.split("\n"):
        if "rpow_session=" in line.lower():
            start = line.index("rpow_session=") + len("rpow_session=")
            end = line.index(";", start) if ";" in line[start:] else len(line)
            return line[start:end].strip()
    return None

def get_balance(cookie):
    """Get account balance."""
    return api_request("/me", cookie=cookie)

def get_challenge(cookie):
    """Get mining challenge."""
    return api_request("/challenge", cookie=cookie, method="POST")

def submit_mint(cookie, challenge_id, solution_nonce):
    """Submit mining solution."""
    return api_request("/mint", cookie=cookie, method="POST", data={
        "challenge_id": challenge_id,
        "solution_nonce": str(solution_nonce)
    })

# ─── Account Management ─────────────────────────────────────────
def load_accounts():
    """Load accounts from config file."""
    if not CONFIG_FILE.exists():
        return []
    try:
        return json.loads(CONFIG_FILE.read_text())
    except Exception:
        return []

def save_accounts(accounts):
    """Save accounts to config file."""
    CONFIG_FILE.write_text(json.dumps(accounts, indent=2))

def add_account(email):
    """Add new account and send magic link."""
    accounts = load_accounts()
    if any(a["email"] == email for a in accounts):
        print(f"{C.YELLOW}⚠ Account {email} already exists{C.RESET}")
        return
    print(f"{C.CYAN}Sending magic link to {email}...{C.RESET}")
    result = request_magic_link(email)
    if result and result.get("ok"):
        accounts.append({"email": email, "cookie": None, "added": time.strftime("%Y-%m-%d %H:%M")})
        save_accounts(accounts)
        print(f"{C.GREEN}✅ Magic link sent! Check your email.{C.RESET}")
        print(f"{C.DIM}Then run: python3 rpow3.py --verify <link>{C.RESET}")
    else:
        print(f"{C.RED}❌ Failed to send link: {result}{C.RESET}")

def verify_account(url):
    """Verify magic link and save cookie."""
    # Extract email hint from URL or just verify
    cookie = verify_link(url)
    if not cookie:
        print(f"{C.RED}❌ Invalid or expired link{C.RESET}")
        return
    # Get email from token
    info = api_request("/me", cookie=cookie)
    if not info or "email" not in info:
        print(f"{C.RED}❌ Failed to get account info{C.RESET}")
        return
    email = info["email"]
    accounts = load_accounts()
    found = False
    for a in accounts:
        if a["email"] == email:
            a["cookie"] = cookie
            found = True
            break
    if not found:
        accounts.append({"email": email, "cookie": cookie, "added": time.strftime("%Y-%m-%d %H:%M")})
    save_accounts(accounts)
    print(f"{C.GREEN}✅ {email} verified! Balance: {info.get('balance', 0)} rpow{C.RESET}")

def remove_account(email):
    """Remove account."""
    accounts = load_accounts()
    accounts = [a for a in accounts if a["email"] != email]
    save_accounts(accounts)
    print(f"{C.GREEN}✅ Removed {email}{C.RESET}")

def list_accounts():
    """List all accounts."""
    accounts = load_accounts()
    if not accounts:
        print(f"{C.YELLOW}No accounts configured. Use --add <email> to add.{C.RESET}")
        return
    print(f"\n{C.BOLD}Configured accounts:{C.RESET}")
    for i, a in enumerate(accounts, 1):
        status = f"{C.GREEN}✅ ready{C.RESET}" if a.get("cookie") else f"{C.RED}❌ not verified{C.RESET}"
        print(f"  {i}. {a['email']} [{status}]")
    print()

def check_balances():
    """Check all account balances."""
    accounts = load_accounts()
    if not accounts:
        print(f"{C.YELLOW}No accounts configured.{C.RESET}")
        return
    total = 0
    print(f"\n{C.BOLD}Account Balances:{C.RESET}")
    for a in accounts:
        if not a.get("cookie"):
            print(f"  {a['email']}: {C.RED}not verified{C.RESET}")
            continue
        info = get_balance(a["cookie"])
        if info:
            bal = info.get("balance", 0)
            minted = info.get("minted", 0)
            total += bal
            print(f"  {a['email']}: {C.GREEN}{bal} rpow{C.RESET} (minted: {minted})")
        else:
            print(f"  {a['email']}: {C.RED}error{C.RESET}")
    print(f"\n  {C.BOLD}Total: {total} rpow{C.RESET}\n")

# ─── Mining Core ─────────────────────────────────────────────────
def leading_zeros(difficulty_bits):
    """Calculate required leading zero hex chars."""
    return (difficulty_bits + 3) // 4

def check_solution(nonce_bytes, difficulty_bits):
    """Check if nonce produces valid hash."""
    h = hashlib.sha256(nonce_bytes).digest()
    bits = 0
    for byte in h:
        if byte == 0:
            bits += 8
        else:
            bits += 8 - byte.bit_length()
            break
    return bits >= difficulty_bits

def mine_worker(cookie, email_short, stop_event, result_queue, log_lock):
    """Mining worker process."""
    prefix = email_short[:8]
    
    while not stop_event.is_set():
        # Get challenge
        challenge = get_challenge(cookie)
        if not challenge or "challenge_id" not in challenge:
            time.sleep(5)
            continue
        
        cid = challenge["challenge_id"]
        nonce_prefix = bytes.fromhex(challenge["nonce_prefix"])
        difficulty = challenge["difficulty_bits"]
        zeros = leading_zeros(difficulty)
        
        # Search
        nonce = 0
        start_time = time.time()
        last_report = start_time
        data = bytearray(nonce_prefix)
        data.extend(b'\x00' * 8)
        
        while not stop_event.is_set():
            # Set nonce bytes (little-endian)
            struct.pack_into('<Q', data, len(nonce_prefix), nonce)
            
            if check_solution(bytes(data), difficulty):
                elapsed = time.time() - start_time
                with log_lock:
                    print(f"\n{C.GREEN}{C.BOLD}🎉 [{prefix}] FOUND SOLUTION! nonce={nonce} ({elapsed:.0f}s){C.RESET}")
                    print(f"{C.CYAN}   Submitting mint...{C.RESET}")
                
                result = submit_mint(cookie, cid, nonce)
                if result and "token" in result:
                    token = result["token"]
                    with log_lock:
                        print(f"{C.GREEN}{C.BOLD}💰 [{prefix}] MINTED! ID: {token.get('id','?')}{C.RESET}")
                    result_queue.put(("minted", prefix, token))
                else:
                    with log_lock:
                        print(f"{C.RED}❌ [{prefix}] Mint failed: {result}{C.RESET}")
                    result_queue.put(("failed", prefix, result))
                break
            
            nonce += 1
            
            # Progress report every 10M hashes
            if nonce % 10_000_000 == 0:
                now = time.time()
                elapsed = now - start_time
                rate = nonce / elapsed / 1_000_000
                report_elapsed = now - last_report
                if report_elapsed >= 10:
                    with log_lock:
                        print(f"{C.DIM}⏳ [{prefix}] {nonce/1_000_000:.0f}M | {rate:.2f} MH/s | {elapsed:.0f}s{C.RESET}")
                    last_report = now

def start_mining():
    """Start multi-process mining."""
    accounts = [a for a in load_accounts() if a.get("cookie")]
    if not accounts:
        print(f"{C.RED}No verified accounts. Use --add and --verify first.{C.RESET}")
        return
    
    print(f"{C.GREEN}Starting {len(accounts)} mining processes...{C.RESET}\n")
    
    stop_event = multiprocessing.Event()
    result_queue = multiprocessing.Queue()
    log_lock = multiprocessing.Lock()
    
    processes = []
    for a in accounts:
        p = multiprocessing.Process(
            target=mine_worker,
            args=(a["cookie"], a["email"], stop_event, result_queue, log_lock),
            daemon=True
        )
        p.start()
        processes.append(p)
        time.sleep(1)  # Stagger start
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print(f"\n{C.YELLOW}Stopping miners...{C.RESET}")
        stop_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Wait for processes
    minted = 0
    try:
        while not stop_event.is_set():
            for p in processes:
                p.join(timeout=1)
                if not p.is_alive():
                    # Restart dead processes
                    idx = processes.index(p)
                    email = accounts[idx]["email"]
                    cookie = accounts[idx]["cookie"]
                    new_p = multiprocessing.Process(
                        target=mine_worker,
                        args=(cookie, email, stop_event, result_queue, log_lock),
                        daemon=True
                    )
                    new_p.start()
                    processes[idx] = new_p
            
            # Check results
            while not result_queue.empty():
                status, prefix, data = result_queue.get_nowait()
                if status == "minted":
                    minted += 1
    except KeyboardInterrupt:
        stop_event.set()
    
    for p in processes:
        p.join(timeout=3)
    
    print(f"\n{C.CYAN}Mining stopped. Total minted: {minted}{C.RESET}")

# ─── CLI Entry Point ─────────────────────────────────────────────
def main():
    banner()
    
    if len(sys.argv) < 2:
        start_mining()
        return
    
    cmd = sys.argv[1]
    
    if cmd == "--add" or cmd == "-a":
        if len(sys.argv) < 3:
            print(f"{C.RED}Usage: rpow3.py --add <email>{C.RESET}")
            return
        add_account(sys.argv[2])
    
    elif cmd == "--verify" or cmd == "-v":
        if len(sys.argv) < 3:
            print(f"{C.RED}Usage: rpow3.py --verify <magic_link_url>{C.RESET}")
            return
        verify_account(sys.argv[2])
    
    elif cmd == "--balance" or cmd == "-b":
        check_balances()
    
    elif cmd == "--accounts" or cmd == "-l":
        list_accounts()
    
    elif cmd == "--remove" or cmd == "-r":
        if len(sys.argv) < 3:
            print(f"{C.RED}Usage: rpow3.py --remove <email>{C.RESET}")
            return
        remove_account(sys.argv[2])
    
    elif cmd == "--help" or cmd == "-h":
        print(__doc__)
    
    elif cmd == "--version":
        print(f"RPOW3 Miner CLI v{VERSION}")
    
    else:
        print(f"{C.RED}Unknown command: {cmd}{C.RESET}")
        print(f"Run {C.CYAN}rpow3.py --help{C.RESET} for usage.")

if __name__ == "__main__":
    main()
