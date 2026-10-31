import json
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS settings(guild TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS preferences(user TEXT PRIMARY KEY, language TEXT, name TEXT);
        CREATE TABLE IF NOT EXISTS sent(guild TEXT, day TEXT, event TEXT, channel TEXT,
            state TEXT NOT NULL, message TEXT, variant INTEGER NOT NULL,
            PRIMARY KEY(guild,day,event));
        CREATE TABLE IF NOT EXISTS ai(day TEXT PRIMARY KEY, calls INTEGER NOT NULL, reserved REAL NOT NULL);
        ''')
        self.db.commit()

    def settings(self, guild, default_channel):
        row = self.db.execute("SELECT value FROM settings WHERE guild=?", (str(guild),)).fetchone()
        return json.loads(row[0]) if row else dict(channel=str(default_channel), time="09:00", language="lv", disabled=[])

    def save_settings(self, guild, value):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (str(guild), json.dumps(value)))

    def preference(self, user):
        row = self.db.execute("SELECT language,name FROM preferences WHERE user=?", (str(user),)).fetchone()
        return row if row else (None, None)

    def set_preference(self, user, *, language=None, name=None, set_name=False):
        old_language, old_name = self.preference(user)
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO preferences VALUES (?,?,?)", (str(user), language or old_language, name if set_name else old_name))

    def variant(self, guild, event, size):
        row = self.db.execute("SELECT variant FROM sent WHERE guild=? AND event=? AND state='sent' ORDER BY day DESC LIMIT 1", (str(guild), event)).fetchone()
        return (row[0] + 1) % size if row else 0

    def claim(self, guild, day, event, channel, variant):
        with self.db:
            cursor = self.db.execute("INSERT OR IGNORE INTO sent VALUES (?,?,?,?, 'pending',NULL,?)", (str(guild), day, event, str(channel), variant))
        return cursor.rowcount == 1

    def is_sent(self, guild, day, event):
        row = self.db.execute("SELECT state FROM sent WHERE guild=? AND day=? AND event=?", (str(guild), day, event)).fetchone()
        return bool(row and row[0] == 'sent')

    def finish(self, guild, day, event, message):
        with self.db:
            self.db.execute("UPDATE sent SET state='sent',message=? WHERE guild=? AND day=? AND event=?", (str(message), str(guild), day, event))

    def reserve_ai(self, day, cap, request_budget, daily_budget):
        if cap <= 0 or request_budget <= 0 or daily_budget <= 0:
            return False
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO ai VALUES (?,0,0)", (day,))
            cur = self.db.execute("UPDATE ai SET calls=calls+1,reserved=reserved+? WHERE day=? AND calls<? AND reserved+?<=?", (request_budget, day, cap, request_budget, daily_budget))
        return cur.rowcount == 1
