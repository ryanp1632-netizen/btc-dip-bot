// Deep-dip reversion bot for cbBTC/USDC on 1-minute bars (agent-fun/bars-replay/v1).
//
// Idea: cbBTC on this pool barely moves most minutes, and a full round trip costs ~26 bps, so the
// bot trades rarely. It waits for a sharp sell-off that leaves the close far below a slow EMA,
// buys it, and sells when the price has reverted to the EMA, when a tight stop-loss is hit, or
// after a maximum holding time. Low turnover keeps fees from eating the PnL.
//
// Rules, evaluated on each batch's bar close (orders fill at the next bar's open):
//   - EMA of closes with span EMA_SPAN (seeded with the first close); no signal before WARM_BARS.
//   - Flat and close <= EMA * (1 - ENTRY_BPS/10000): buy with all cash (capped by weight room).
//   - Holding: sell the whole position when close >= EMA (reverted), when the position is worth
//     STOP_BPS under its cost, or when it has been held MAX_HOLD_BARS bars.
//   - Participation trade: the race guardrail needs at least 1 own filled trade, and a deep dip
//     may never come in 4 hours. So the bot buys PROBE_QUOTE (2 USDC) on its first batch and
//     sells it on the next one; it costs a fraction of a cent in fees.
//   - No order on the last bar's batch would fill (after_end), and the harness sells whatever is
//     left at the last close anyway.
// Everything is deterministic: float64 arithmetic on + - * / only, no clock, no randomness.

import { runBars, type BuyInput, type SellInput } from './vendor/makefun-bars.ts';

const EMA_SPAN = 120;
const WARM_BARS = 120;
const ENTRY_BPS = 150;
const STOP_BPS = 100n;
const MAX_HOLD_BARS = 240;
const MAX_SLIPPAGE_BPS = 100;
const PROBE_QUOTE = 2_000_000n; // 2 USDC in quote units

let ema: number | null = null;
let bars = 0;
let entryBar = -1;
let probeState: 'none' | 'bought' | 'done' = 'none';

await runBars({
  onBatch(state, batch) {
    const symbol = state.hello.symbols[0]!.symbol;
    const bar = batch.bars.find((b) => b.symbol === symbol);
    if (bar === undefined) return [];

    const close = Number(bar.c);
    ema = ema === null ? close : ema + (2 / (EMA_SPAN + 1)) * (close - ema);
    bars++;

    const held = state.positions.get(symbol);
    const minNotional = BigInt(state.hello.fees.min_notional_quote_units);

    // Participation probe: a tiny buy first, sold right after. If the probe buy was rejected
    // (no fill reported, nothing held), send it again on the next bar so the race guardrail of
    // at least one own trade is still met.
    if (probeState === 'bought' && held === undefined && !batch.fills.some((f) => f.status !== 'rejected')) {
      probeState = 'none';
    }
    if (probeState === 'none') {
      probeState = 'bought';
      const notional = PROBE_QUOTE > minNotional ? PROBE_QUOTE : minNotional;
      return [{ side: 'buy', symbol, notional_quote_units: notional, max_slippage_bps: MAX_SLIPPAGE_BPS } satisfies BuyInput];
    }
    if (probeState === 'bought') {
      probeState = 'done';
      return [{ side: 'sell', symbol, qty: held!.qty, max_slippage_bps: MAX_SLIPPAGE_BPS } satisfies SellInput];
    }

    if (bars < WARM_BARS) return [];

    if (held !== undefined) {
      if (entryBar < 0) entryBar = bars; // a position we did not see open (should not happen)
      const value = state.value(symbol, held.qty);
      const reverted = close >= ema;
      const stopped = value * 10_000n <= held.cost * (10_000n - STOP_BPS);
      const stale = bars - entryBar >= MAX_HOLD_BARS;
      if (reverted || stopped || stale) {
        return [{ side: 'sell', symbol, qty: held.qty, max_slippage_bps: MAX_SLIPPAGE_BPS } satisfies SellInput];
      }
      return [];
    }

    entryBar = -1;
    if (close <= ema * (1 - ENTRY_BPS / 10_000)) {
      let notional = state.cash;
      const room = state.weightRoom(symbol);
      if (room < notional) notional = room;
      if (notional < minNotional) return [];
      entryBar = bars;
      return [{ side: 'buy', symbol, notional_quote_units: notional, max_slippage_bps: MAX_SLIPPAGE_BPS } satisfies BuyInput];
    }
    return [];
  },
});
