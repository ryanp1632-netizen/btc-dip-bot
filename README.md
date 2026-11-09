# cbBTC deep-dip reversion bot

Paper-trading entry for the make.fun bounty "Race a BTC trading bot live for 4 hours" (btc-race-4h-01).
No real money is traded: the bot only speaks the agent-fun/bars-replay/v1 protocol on stdin/stdout.

- `main.ts` (Node 22): buys only when the 1-minute close is at least 150 bps under its 120-bar EMA,
  sells on reversion to the EMA, a 100 bps stop under cost, or after 240 bars. A 2 USDC probe buy/sell
  at the start makes sure the bot has at least one trade even if no dip comes.
- `vendor/makefun-bars.ts`: the kit's TypeScript SDK shim, unmodified.

Why so few trades: a full round trip costs about 26 bps (4 bps fee + 2 bps slippage + price impact per side),
and on the dev window most minutes move far less than that. Only the deep dip clears costs.
