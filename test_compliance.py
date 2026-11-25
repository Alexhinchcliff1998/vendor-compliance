from compliance import Register,demo
def test_risk():
    r=demo('2025-11-01');assert [v['risk'] for v in r['vendors']]==['Current','High','Review'];assert r['audit_verified']
def test_audit_and_close(tmp_path):
    r=Register(tmp_path/'demo.db');r.vendor('1','Demo');a=r.action('1','Follow up','2025-01-01');assert r.report('2025-02-01')[0]['overdue_actions']==1;r.close(a);assert r.report('2025-02-01')[0]['overdue_actions']==0;assert r.verify();r.db.execute("UPDATE audit SET payload='changed' WHERE id=1");assert not r.verify();r.db.close()
