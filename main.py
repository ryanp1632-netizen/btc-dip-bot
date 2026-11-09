"""Fast-curve graduation rider for make.fun's memecoin-backtest-48h-01 (agent-fun/replay/v2).

Run by the grader as ``python3 -P -s /bot/main.py``. The decisions live in strategy.py; this file
only adapts the SDK shim's state (vendor/makefun_bot.py, unmodified) to it.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "vendor"))
sys.path.insert(0, HERE)

import makefun_bot  # noqa: E402
from strategy import Strategy  # noqa: E402

strategy = Strategy()


def on_batch(state, batch):
    caps = state.hello["caps"]
    curves = state.curves

    def reserves(mint):
        c = curves.get(mint)
        if c is None or c.complete:
            return None
        return (c.virtual_quote_reserves, c.virtual_token_reserves, c.real_quote_reserves, c.real_token_reserves)

    positions = {m: h.token_amount for m, h in state.positions.items() if h.token_amount > 0}
    pending = {p.order["mint"] for p in state.pending.values()}
    decided = strategy.decide(
        batch["slot"], batch["events"], positions, state.free_cash_lamports(), pending, reserves,
        caps["max_open_positions"], caps["max_orders_per_batch"], state.tx_fee_lamports(),
    )
    orders = []
    for side, mint, amount in decided:
        if side == "buy":
            orders.append({"side": "buy", "mint": mint, "quote_lamports": int(amount),
                           "max_slippage_bps": strategy.p["slip"]})
        else:
            orders.append({"side": "sell", "mint": mint, "token_amount": int(amount),
                           "max_slippage_bps": 10_000})
    return orders


if __name__ == "__main__":
    makefun_bot.run(on_batch)
