import pickle, sys, json, hashlib
from collections import defaultdict
from strategy import Strategy

TX = 105_000
FEE_BPS = 125

def run(params=None, ev=None, verbose=False, fail=True):
    ev = ev or pickle.load(open('events.pkl', 'rb'))
    strat = Strategy(params)
    rec = {}            # mint -> [vsol, vtok, rsol, rtok]
    ds = defaultdict(int); dt = defaultdict(int)
    complete = set()
    cash = 10 * 10**9
    pos = {}            # mint -> tokens
    cost = defaultdict(int)
    pnl_coin = defaultdict(int)
    rt_size = defaultdict(int)   # current round trip size
    rts = defaultdict(int)       # max qualifying round trip per coin
    pending = []        # (fill_slot, side, mint, amount, decided_reserves_out)
    n_orders = 0
    peak_eq = cash; maxdd = 0.0

    def eff(m):
        r = rec.get(m)
        if r is None: return None
        vsol, vtok, rsol, rtok = r
        d_t, d_s = dt[m], ds[m]
        f = 1.0
        if d_t > 0 and d_t > rtok: f = rtok / d_t if d_t else 1
        if d_s < 0 and -d_s > rsol: f = min(f, rsol / -d_s)
        st = int(d_t * f); ss = int(d_s * f)
        return (vsol + ss, vtok - st, rsol + ss, rtok - st)

    def sell_out(m, tok):
        vsol, vtok, rsol, rtok = eff(m)
        gross = vsol * tok // (vtok + tok)
        gross = min(gross, max(rsol, 0))
        return gross, gross - gross * FEE_BPS // 10000

    def do_sell(m, tok, closing=False):
        nonlocal cash
        gross, net = sell_out(m, tok)
        ds[m] -= gross; dt[m] -= tok
        cash += net
        pos[m] -= tok
        pnl_coin[m] += net
        if pos[m] <= 0:
            del pos[m]
            if rt_size[m] >= 10_000_000: rts[m] = 1
            rt_size[m] = 0

    def resolve(o):
        nonlocal cash, n_orders
        fslot, side, m, amt = o
        n_orders += 1
        if m in complete: return
        h = int(hashlib.sha256(f'{n_orders}'.encode()).hexdigest()[:8], 16)
        cash -= TX; pnl_coin[m] -= TX
        if fail and h % 100 < 2: return
        if side == 'buy':
            if cash < amt: return
            vsol, vtok, rsol, rtok = eff(m)
            net = amt * 10000 // (10000 + FEE_BPS)
            tok = vtok * net // (vsol + net)
            tok = min(tok, rtok)
            if tok <= 0: return
            cash -= amt; pnl_coin[m] -= amt
            ds[m] += net; dt[m] += tok
            pos[m] = pos.get(m, 0) + tok
            rt_size[m] += amt
        else:
            tok = min(amt, pos.get(m, 0))
            if tok > 0: do_sell(m, tok)

    def equity():
        e = cash
        for m, tok in pos.items():
            e += sell_out(m, tok)[1]
        return e

    i = 0; n = len(ev); last_eq_slot = 0
    while i < n:
        s = ev[i][0]
        j = i
        while j < n and ev[j][0] == s: j += 1
        # fills that land before this slot
        keep = []
        for o in pending:
            if o[0] < s: resolve(o)
            else: keep.append(o)
        pending = keep
        events = []
        for x in ev[i:j]:
            m = x[3]
            if x[2] == 'T':
                rec[m] = [x[4], x[5], x[6], x[7]]
                events.append({'event': 'TradeEvent', 'mint': m, 'is_buy': x[8], 'user': x[10], 'sol_amount': x[9]})
            elif x[2] == 'C':
                rec[m] = [x[4], x[5], 0, x[7]]
                events.append({'event': 'CreateEvent', 'mint': m})
            else:
                events.append({'event': 'CompleteEvent', 'mint': m})
        keep = []
        for o in pending:
            if o[0] == s: resolve(o)
            else: keep.append(o)
        pending = keep
        for x in ev[i:j]:
            if x[2] == 'X':
                m = x[3]
                complete.add(m)
                if m in pos: do_sell(m, pos[m], True)
        if s - last_eq_slot >= 300:
            last_eq_slot = s
            eqv = equity(); peak_eq = max(peak_eq, eqv)
            maxdd = max(maxdd, 1 - eqv / peak_eq)
        pmints = {o[2] for o in pending}
        orders = strat.decide(s, events, dict(pos), cash, pmints, lambda m: None if m in complete else eff(m), 5, 16, TX)
        for side, m, amt in orders:
            pending.append((s + 2, side, m, amt))
        i = j
    for o in pending: resolve(o)
    for m in list(pos): do_sell(m, pos[m])
    pnl = (cash - 10 * 10**9) / 1e9
    if verbose:
        top = sorted(pnl_coin.items(), key=lambda z: z[1])
        print('worst', [(m[:5], round(v / 1e9, 3)) for m, v in top[:8]])
        print('best', [(m[:5], round(v / 1e9, 3)) for m, v in top[-8:]])
    return pnl, maxdd, sum(rts.values()), len(pnl_coin)

if __name__ == '__main__':
    params = json.loads(sys.argv[1]) if len(sys.argv) > 1 else None
    print(run(params, verbose=True))
