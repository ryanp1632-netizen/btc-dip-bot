"""Feed the dev data to main.py over the replay/v2 protocol (no fills simulated): checks the protocol path and determinism."""
import gzip, json, glob, subprocess, sys, hashlib
K, BOT, LIMIT = sys.argv[1], sys.argv[2], int(sys.argv[3])
hello = {"type": "hello", "protocol": "agent-fun/replay/v2", "seed": "1",
         "universe": {"program": "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P", "quote": "SOL", "mayhem": "excluded",
                      "exclude_cashback": True, "sample": {"hash": "sha256", "modulus": 16, "residue": 15}},
         "capital": {"lamports": "10000000000"},
         "caps": {"max_open_positions": 5, "max_order_bps_of_real_reserve": 100, "max_orders_per_batch": 16,
                  "shorts": False, "leverage": False},
         "latency_slots": 2,
         "fees": {"protocol_bps_fallback": 95, "creator_bps_fallback": 30, "base_fee_lamports": "5000",
                  "priority_fee_lamports": "100000", "failed_tx_bps": 200}}
evs = []
for f in sorted(glob.glob(K + '/dataset/events/*.ndjson.gz')):
    with gzip.open(f, 'rt') as fh:
        for line in fh:
            evs.append(json.loads(line))
            if len(evs) >= LIMIT: break
    if len(evs) >= LIMIT: break
evs.sort(key=lambda e: (e['slot'], e['chain_seq']))
p = subprocess.Popen(['python3', '-P', '-s', BOT + '/main.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open('bot.err','w'), text=True,
                     env={'PYTHONHASHSEED': '0', 'PATH': '/usr/bin:/bin'})
p.stdin.write(json.dumps(hello) + '\n'); p.stdin.flush()
h = hashlib.sha256(); n = 0; seq = 0; i = 0
while i < len(evs):
    s = evs[i]['slot']; j = i
    while j < len(evs) and evs[j]['slot'] == s: j += 1
    seq += 1
    b = {"type": "batch", "seq": seq, "slot": s, "events": evs[i:j], "marks": [], "fills": [],
         "account": {"cash_lamports": "10000000000", "positions": []}}
    p.stdin.write(json.dumps(b) + '\n'); p.stdin.flush()
    r = p.stdout.readline(); h.update(r.encode())
    o = json.loads(r); assert o['seq'] == seq, r; n += len(o['orders'])
    i = j
seq += 1
p.stdin.write(json.dumps({"type": "done", "seq": seq, "reason": "end_of_data", "account": {"cash_lamports": "10000000000", "positions": []}}) + '\n')
p.stdin.close(); p.wait()
print('batches', seq - 1, 'orders', n, 'exit', p.returncode, 'digest', h.hexdigest()[:16])
