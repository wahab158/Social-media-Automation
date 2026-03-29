import sqlite3

conn = sqlite3.connect('autopost.db')

# Check current user_settings columns
cols = [row[1] for row in conn.execute('PRAGMA table_info(user_settings)').fetchall()]
print('Current columns:', cols)

# Add missing columns
migrations = [
    ('post_day', 'TEXT DEFAULT "Monday"'),
    ('news_limit', 'INTEGER DEFAULT 10'),
    ('news_provider', 'TEXT DEFAULT "rss"'),
    ('llm_provider', 'TEXT DEFAULT "openai"'),
    ('post_time', 'TEXT DEFAULT "07:00"'),
    ('tone', 'TEXT DEFAULT "professional"'),
    ('topics', 'TEXT DEFAULT ""'),
    ('is_enabled', 'INTEGER DEFAULT 1'),
]

for col, col_def in migrations:
    if col not in cols:
        conn.execute(f'ALTER TABLE user_settings ADD COLUMN {col} {col_def}')
        print(f'Added column: {col}')
    else:
        print(f'Already exists: {col}')

# Also check brand_profiles for dna_config_json
cols2 = [row[1] for row in conn.execute('PRAGMA table_info(brand_profiles)').fetchall()]
print('brand_profiles columns:', cols2)
if 'dna_config_json' not in cols2:
    conn.execute('ALTER TABLE brand_profiles ADD COLUMN dna_config_json TEXT')
    print('Added dna_config_json to brand_profiles')

conn.commit()
conn.close()
print('Migration complete.')
