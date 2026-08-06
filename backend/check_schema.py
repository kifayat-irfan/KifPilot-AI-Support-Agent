import sqlite3
conn = sqlite3.connect('E:/kifpilot-ai-support-agent/backend/data/kifpilot.db')
cursor = conn.cursor()

# Check tables
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('Tables:', tables)

# Check documents table schema
cursor.execute('PRAGMA table_info(documents)')
cols = cursor.fetchall()
print('documents columns:')
for col in cols:
    print(f'  {col[1]}: {col[2]} notnull={col[3]} pk={col[5]}')

# Check document_chunks table schema
cursor.execute('PRAGMA table_info(document_chunks)')
cols = cursor.fetchall()
print('document_chunks columns:')
for col in cols:
    print(f'  {col[1]}: {col[2]} notnull={col[3]} pk={col[5]}')

# Check indexes
cursor.execute('SELECT name FROM sqlite_master WHERE type="index"')
indexes = cursor.fetchall()
print('Indexes:', indexes)

# Check foreign keys
cursor.execute('PRAGMA foreign_key_list(document_chunks)')
fks = cursor.fetchall()
print('Foreign keys:', fks)

conn.close()