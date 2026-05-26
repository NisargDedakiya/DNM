import sqlite3
import datetime

conn = sqlite3.connect('nisarghunter.db')
cursor = conn.cursor()

user_id = 'd91b2ba38b4848be81d19c8dafd297c8'
org_id = '707bde9589404ae2afbd9d2e3002d777'

program_id = '99999999999999999999999999999999'
scan_id = '88888888888888888888888888888888'
finding_id = '77777777777777777777777777777777'

now = datetime.datetime.utcnow().isoformat()

# Insert test program
cursor.execute("SELECT id FROM programs WHERE id = ?", (program_id,))
if not cursor.fetchone():
    cursor.execute("""
        INSERT INTO programs (id, name, platform, scope, description, created_by, organization_id, created_at, updated_at, handle, is_private, scope_json, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (program_id, 'Acme Security Program', 'hackerone', '*.acme.com', 'Acme Vulnerability Disclosure Program', user_id, org_id, now, now, 'acme', 0, '{}', 1))

# Insert test scan
cursor.execute("SELECT id FROM scans WHERE id = ?", (scan_id,))
if not cursor.fetchone():
    cursor.execute("""
        INSERT INTO scans (id, program_id, organization_id, created_by_id, scan_type, status, started_at, completed_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (scan_id, program_id, org_id, user_id, 'recon', 'running', now, None, now, now))

# Insert test finding
cursor.execute("SELECT id FROM findings WHERE id = ?", (finding_id,))
if not cursor.fetchone():
    cursor.execute("""
        INSERT INTO findings (id, program_id, organization_id, scan_id, created_by_id, title, severity, description, endpoint, evidence, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (finding_id, program_id, org_id, scan_id, user_id, 'SQL Injection in /api/v1/user', 'critical', 'A blind SQL Injection vulnerability was identified in the user profile page. An attacker can use this to retrieve administrative records.', '/api/v1/user?id=1', 'SELECT * FROM users WHERE id = 1\nReturned HTTP 200 with admin data', 'open', now, now))

conn.commit()
conn.close()
print("Seeding successful!")
