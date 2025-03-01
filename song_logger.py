import sqlite3

def incr_music_counter(url: str, name: str):
    conn = sqlite3.connect('botmusic.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS music_counter (
            url TEXT PRIMARY KEY,
            count INTEGER,
            name TEXT
        )
    ''')
    cursor.execute('''
        INSERT OR IGNORE INTO music_counter (url, count, name) VALUES (?, ?, ?)
    ''', (url, 0, name))
    cursor.execute('''
        UPDATE music_counter SET count = count + 1 WHERE url=?
    ''', (url,))
    conn.commit()
    conn.close()
    
def get_music_counts(num: int) -> list[tuple[str, int, str]]:
    conn = sqlite3.connect('botmusic.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM music_counter ORDER BY count DESC;
    ''')
    return cursor.fetchmany(num)

