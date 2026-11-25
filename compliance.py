import argparse,sqlite3,json,hashlib
from pathlib import Path
from datetime import date,timedelta
P=Path(__file__).parent
class Register:
    def __init__(self,path):
        self.db=sqlite3.connect(path);self.db.row_factory=sqlite3.Row;self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript("""CREATE TABLE IF NOT EXISTS vendors(id TEXT PRIMARY KEY,name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS evidence(vendor TEXT REFERENCES vendors(id),kind TEXT,expires TEXT NOT NULL,PRIMARY KEY(vendor,kind));
        CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY,vendor TEXT REFERENCES vendors(id),description TEXT NOT NULL,due TEXT NOT NULL,closed INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,payload TEXT NOT NULL,previous_hash TEXT NOT NULL,hash TEXT NOT NULL);""")
    def audit(self,event,data):
        prev=self.db.execute('SELECT hash FROM audit ORDER BY id DESC LIMIT 1').fetchone();prev=prev[0] if prev else 'GENESIS';payload=json.dumps({'event':event,'data':data},sort_keys=True,separators=(',',':'));digest=hashlib.sha256((prev+payload).encode()).hexdigest();self.db.execute('INSERT INTO audit(payload,previous_hash,hash) VALUES(?,?,?)',(payload,prev,digest))
    def vendor(self,id,name):
        with self.db:self.db.execute('INSERT INTO vendors VALUES(?,?)',(id,name));self.audit('vendor_created',{'id':id,'name':name})
    def evidence(self,vendor,kind,expires):
        expires=date.fromisoformat(expires).isoformat()
        with self.db:self.db.execute('INSERT INTO evidence VALUES(?,?,?) ON CONFLICT(vendor,kind) DO UPDATE SET expires=excluded.expires',(vendor,kind,expires));self.audit('evidence_updated',{'vendor':vendor,'kind':kind,'expires':expires})
    def action(self,vendor,description,due):
        due=date.fromisoformat(due).isoformat()
        with self.db:
            id=self.db.execute('INSERT INTO actions(vendor,description,due) VALUES(?,?,?)',(vendor,description,due)).lastrowid;self.audit('action_created',{'id':id,'vendor':vendor,'description':description,'due':due});return id
    def close(self,id):
        with self.db:
            row=self.db.execute('UPDATE actions SET closed=1 WHERE id=? AND closed=0',(id,))
            if row.rowcount!=1:raise ValueError('Open action not found')
            self.audit('action_closed',{'id':id})
    def report(self,as_of):
        d=date.fromisoformat(as_of);out=[]
        for v in self.db.execute('SELECT * FROM vendors ORDER BY id').fetchall():
            docs={x['kind']:date.fromisoformat(x['expires']) for x in self.db.execute('SELECT * FROM evidence WHERE vendor=?',(v['id'],))};missing=sorted({'insurance','service_agreement'}-docs.keys());expired=sorted(k for k,x in docs.items() if x<d);soon=sorted(k for k,x in docs.items() if d<=x<=d+timedelta(days=30));overdue=self.db.execute('SELECT COUNT(*) FROM actions WHERE vendor=? AND closed=0 AND due<?',(v['id'],d.isoformat())).fetchone()[0];status='High' if missing or expired or overdue else 'Review' if soon else 'Current';out.append({'id':v['id'],'name':v['name'],'risk':status,'missing':missing,'expired':expired,'expiring_soon':soon,'overdue_actions':overdue})
        return out
    def verify(self):
        prev='GENESIS'
        for row in self.db.execute('SELECT * FROM audit ORDER BY id'):
            if row['previous_hash']!=prev or row['hash']!=hashlib.sha256((prev+row['payload']).encode()).hexdigest():return False
            prev=row['hash']
        return True
def demo(as_of):
    r=Register(':memory:');d=date.fromisoformat(as_of)
    for id,name in [('V01','Atlas Transport'),('V02','Cedar Freight'),('V03','Pine Logistics')]:r.vendor(id,name)
    for id,days in [('V01',90),('V02',-10),('V03',15)]:
        r.evidence(id,'insurance',(d+timedelta(days=days)).isoformat());r.evidence(id,'service_agreement',(d+timedelta(days=180)).isoformat())
    r.action('V02','Submit renewed certificate',(d-timedelta(days=4)).isoformat());result={'as_of':as_of,'vendors':r.report(as_of),'audit_verified':r.verify()};r.db.close();return result
if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Fictional vendor compliance register');parser.add_argument('--db',default=str(P/'register.db'));sub=parser.add_subparsers(dest='command',required=True)
    d=sub.add_parser('demo');d.add_argument('--as-of',default='2025-11-01')
    v=sub.add_parser('vendor');v.add_argument('id');v.add_argument('name')
    e=sub.add_parser('evidence');e.add_argument('vendor');e.add_argument('kind');e.add_argument('expires')
    a=sub.add_parser('action');a.add_argument('vendor');a.add_argument('description');a.add_argument('due')
    c=sub.add_parser('close');c.add_argument('id',type=int)
    r=sub.add_parser('report');r.add_argument('--as-of',default=date.today().isoformat())
    sub.add_parser('verify');args=parser.parse_args()
    if args.command=='demo':
        result=demo(args.as_of);(P/'example_report.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    else:
        register=Register(args.db)
        try:
            if args.command=='vendor':register.vendor(args.id,args.name)
            elif args.command=='evidence':register.evidence(args.vendor,args.kind,args.expires)
            elif args.command=='action':print(register.action(args.vendor,args.description,args.due))
            elif args.command=='close':register.close(args.id)
            elif args.command=='report':print(json.dumps(register.report(args.as_of),indent=2))
            elif args.command=='verify':print('Audit chain valid' if register.verify() else 'Audit chain invalid')
        finally:register.db.close()
