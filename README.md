# Fast-curve graduation rider

Paper-trading entry for make.fun's "Beat our trading bots on a Solana replay" (`memecoin-backtest-48h-01`).
No real money is traded: the bot only speaks the agent-fun/replay/v2 protocol on stdin/stdout.

- `main.py` (Python 3.13, standard library only): adapts the SDK shim's state to the strategy.
- `strategy.py`: entry, sizing and exit rules (see [STRATEGY.md](STRATEGY.md)).
- `vendor/makefun_bot.py`: the kit's Python SDK shim, unmodified.
- `tools/`: local replay simulator (`load.py`, `sim.py`) and a protocol driver (`drive.py`) used for tuning.

Run: `PYTHONHASHSEED=0 python3 -P -s main.py` with the harness on stdin. MIT licensed.
