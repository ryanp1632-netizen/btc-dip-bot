"""Fast-curve graduation rider. Pure decision logic, shared by main.py and the local simulator."""

LAMPORTS = 1_000_000_000

P = {
    'max_age': 300,          # slots after create during which a coin may first qualify
    'min_rsol': 60 * LAMPORTS,
    'min_buyers': 30,
    'target': 1_000_000_000,  # lamports to put into one coin
    'stop_drop': 1000 * LAMPORTS,  # sell when real SOL falls this far under its peak since entry
    'trail': 0.3,          # or under (1 - trail) of that peak
    'floor': 0.75,           # or under this share of the real SOL at entry
    'max_hold': 1500,       # slots
    'ticket': 12_000_000,   # small round trip to meet the 20-coin bar
    'ticket_hold': 4,
    'tickets_wanted': 24,
    'slip': 3000,
}


class Coin:
    __slots__ = ('created', 'buyers', 'rsol', 'peak', 'qualified', 'entered', 'entry_slot', 'done', 'exiting',
                 'ticket', 'ticket_slot', 'spent', 'entry_rsol')

    def __init__(self, created):
        self.created = created
        self.buyers = set()
        self.rsol = 0
        self.peak = 0
        self.qualified = False
        self.entered = False
        self.entry_slot = -1
        self.done = False
        self.exiting = False
        self.ticket = False
        self.ticket_slot = -1
        self.spent = 0
        self.entry_rsol = 0


class Strategy:
    def __init__(self, params=None):
        self.p = dict(P)
        if params:
            self.p.update(params)
        self.coins = {}
        self.tickets_done = 0

    def decide(self, slot, events, positions, cash, pending_mints, reserves, max_positions, max_orders, tx_fee):
        """positions: mint -> tokens held; reserves(mint) -> (vsol, vtok, rsol, rtok) incl own impact or None."""
        p = self.p
        coins = self.coins
        for e in events:
            m = e['mint']
            k = e['event']
            if k == 'CreateEvent':
                coins[m] = Coin(slot)
                continue
            c = coins.get(m)
            if c is None:
                continue
            if k == 'CompleteEvent':
                c.done = True
                continue
            if e['is_buy']:
                c.buyers.add(e['user'])
        orders = []
        committed = set(positions) | set(pending_mints)
        free = cash
        # exits first
        for m, tok in positions.items():
            c = coins.get(m)
            if c is None or c.done or m in pending_mints or tok <= 0:
                continue
            r = reserves(m)
            if r is None:
                continue
            rsol = r[2]
            if c.ticket and not c.entered:
                if slot - c.ticket_slot >= p['ticket_hold']:
                    orders.append(('sell', m, tok))
                continue
            if rsol > c.peak:
                c.peak = rsol
            if (rsol < c.peak - p['stop_drop'] or rsol < c.peak * (1 - p['trail']) or rsol < c.entry_rsol * p['floor']
                    or slot - c.entry_slot > p['max_hold']):
                c.exiting = True
                orders.append(('sell', m, tok))
        # entries / adds
        for m, c in coins.items():
            if c.done or c.exiting or len(orders) >= max_orders:
                continue
            r = reserves(m)
            if r is None:
                continue
            rsol = r[2]
            age = slot - c.created
            if not c.entered:
                if age > p['max_age'] or rsol < p['min_rsol'] or len(c.buyers) < p['min_buyers']:
                    continue
                if m not in committed and len(committed) >= max_positions:
                    continue
                if m in pending_mints and m not in positions:
                    continue
                c.entered = True
                c.entry_slot = slot
                c.peak = rsol
                c.entry_rsol = rsol
                committed.add(m)
            if c.spent >= p['target'] or m in pending_mints:
                continue
            amt = min(rsol // 100, p['target'] - c.spent, free - tx_fee - 200_000_000)
            if amt < 5_000_000:
                continue
            orders.append(('buy', m, amt))
            c.spent += amt
            free -= amt + tx_fee
        # tickets for the 20-coin bar
        if self.tickets_done < p['tickets_wanted']:
            for m, c in coins.items():
                if len(orders) >= max_orders or len(committed) >= max_positions - 1:
                    break
                if c.done or c.entered or c.ticket or m in committed:
                    continue
                r = reserves(m)
                if r is None or slot - c.created > 400:
                    continue
                if r[2] < 3 * LAMPORTS or r[2] // 100 < p['ticket']:
                    continue
                c.ticket = True
                c.ticket_slot = slot
                committed.add(m)
                self.tickets_done += 1
                orders.append(('buy', m, p['ticket']))
                free -= p['ticket'] + tx_fee
        return orders
