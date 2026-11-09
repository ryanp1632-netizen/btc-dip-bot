import gzip, json, pickle, sys, glob
K=sys.argv[1]
ev=[]
for f in sorted(glob.glob(K+'/dataset/events/*.ndjson.gz')):
    with gzip.open(f,'rt') as fh:
        for line in fh:
            e=json.loads(line)
            t=e['event']
            if t=='TradeEvent':
                ev.append((e['slot'],e['chain_seq'],'T',e['mint'],int(e['virtual_sol_reserves']),int(e['virtual_token_reserves']),int(e['real_sol_reserves']),int(e['real_token_reserves']),e['is_buy'],int(e['sol_amount']),e['user'],int(e['fee_basis_points']),int(e['creator_fee_basis_points']),e.get('block_time')))
            elif t=='CreateEvent':
                ev.append((e['slot'],e['chain_seq'],'C',e['mint'],int(e['virtual_sol_reserves']),int(e['virtual_token_reserves']),0,int(e['real_token_reserves']),None,0,e['creator'],0,0,e.get('block_time')))
            else:
                ev.append((e['slot'],e['chain_seq'],'X',e['mint'],0,0,0,0,None,0,e['user'],0,0,e.get('block_time')))
ev.sort(key=lambda x:(x[0],x[1]))
pickle.dump(ev,open('events.pkl','wb'))
print(len(ev), sum(1 for x in ev if x[2]=='C'), sum(1 for x in ev if x[2]=='X'))
