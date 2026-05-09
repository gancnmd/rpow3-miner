# RPOW3 Miner CLI ⛏️

Multi-account parallel mining CLI for [RPOW3](https://rpow3.com) — a modern tribute to Hal Finney's original RPOW.

> "AI 实现了代码小白当个科学家的梦！" — Inspired by [@CG_BRC20](https://x.com/CG_BRC20/status/2052957208854573091)

## Features

- 🔐 **Multi-account** — Mine with multiple email accounts simultaneously
- ⚡ **Parallel mining** — Each account runs in a separate process (no GIL)
- 📧 **Magic link auth** — No passwords needed, just email verification
- 💰 **Auto-mint** — Solutions are submitted automatically
- 📊 **Real-time stats** — Hashrate, progress, and balance tracking
- 🎯 **Zero dependencies** — Uses only Python stdlib + curl

## Quick Start

```bash
# Clone
git clone https://github.com/gancnmd/rpow3-miner.git
cd rpow3-miner

# Add account (sends magic link to your email)
python3 rpow3.py --add your@email.com

# Click the link in your email, then verify
python3 rpow3.py --verify "https://api.rpow3.com/auth/verify?token=..."

# Add more accounts (optional)
python3 rpow3.py --add another@email.com
python3 rpow3.py --verify "https://api.rpow3.com/auth/verify?token=..."

# Start mining!
python3 rpow3.py
```

## Usage

```
python3 rpow3.py                    # Start mining (all verified accounts)
python3 rpow3.py --add <email>      # Add account and send magic link
python3 rpow3.py --verify <url>     # Verify magic link from email
python3 rpow3.py --balance          # Check all account balances
python3 rpow3.py --accounts         # List configured accounts
python3 rpow3.py --remove <email>   # Remove account
python3 rpow3.py --help             # Show help
```

## How It Works

1. **Challenge**: Server sends a random nonce prefix + difficulty target
2. **Search**: Worker tries SHA256(nonce_prefix + counter) billions of times
3. **Submit**: When a hash with enough leading zero bits is found, submit to server
4. **Mint**: Server verifies and mints RPOW tokens to your account

Each account runs in its own process for true parallel mining. Current difficulty is 32 bits (~4.3 billion hashes per solution on average).

## Requirements

- Python 3.8+
- curl (usually pre-installed)
- No pip packages needed!

## Performance

- ~1 MH/s per process (Python SHA256)
- ~75 min average per solution per account
- Scales linearly with accounts

## License

MIT — A tribute to Hal Finney's RPOW (2004-2024)

## Acknowledgments

- [Hal Finney](https://en.wikipedia.org/wiki/Hal_Finney) — Creator of the original RPOW
- [RPOW3](https://rpow3.com) — Modern tribute implementation
- [@CG_BRC20](https://x.com/CG_BRC20) — Inspiration for this CLI
