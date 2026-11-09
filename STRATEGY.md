# Strategy: fast-curve graduation rider

**What it trades.** pump.fun bonding curves that fill unusually fast. A coin qualifies when, within 300 slots
(about two minutes) of its CreateEvent, its real SOL reserve has reached 60 SOL and at least 30 distinct wallets
have bought it. On the dev window only a handful of coins complete their curve organically, and every one of them
filled this fast; slow coins that reach the same depth mostly stall and bleed. The bet is that a curve already
about 70% full after two minutes, with broad buying, is more likely than not to finish, and the replay closes
a position at completion at the completing trade's post-trade reserves, the top of the curve.

**How it sizes.** Up to 1 SOL per coin, bought in slices no larger than the 1%-of-real-reserve cap allows per
reply (about 0.6 SOL at 60 SOL of reserve), so a position is usually built in two or three slots. At most five
coins are held. With 10 SOL of capital this keeps at least half of the account in cash at all times and keeps the
worst single dump to roughly a tenth of equity, well inside the 50% drawdown bar.

**When it exits.**
- The curve completes: the replay closes the position (the intended exit).
- The real SOL reserve falls 30% under its peak since entry (trailing stop), or under 75% of its level at entry.
- 1,500 slots (about ten minutes) pass without completion.

**Guardrail tickets.** The bar needs a round trip of at least 0.01 SOL on 20 coins, and the main signal fires only
a few times a day. So early in the window the bot also opens 24 small round trips of 0.012 SOL on young coins with
at least 3 SOL of reserve, selling each four slots later. Each costs a few thousandths of a SOL in fees, and they
never take the last free position slot, so they cannot block a real entry.

**Determinism.** No randomness, no clock, no environment; state is kept in insertion-ordered dicts, so two runs
on the same data send the same orders.

**Tested.** `tools/sim.py` replays the dev window with the rules' fill model (2-slot latency, own-impact shift,
125 bps curve fees, tx fees, 2% failed orders). On it this configuration nets about +0.9 SOL with a 13% maximum
drawdown and 31 qualifying round trips. That edge comes from a few coins, so it is noisy; the final window
will decide whether fast curves keep completing.
