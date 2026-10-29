import json
import sqlite3
from threading import RLock


class Store:
    def __init__(self, path):
        self.lock = RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS state (kind TEXT, id TEXT, value TEXT, PRIMARY KEY(kind,id))')
        self.db.execute('CREATE TABLE IF NOT EXISTS revision (id INTEGER PRIMARY KEY, value INTEGER)')
        self.db.execute('INSERT OR IGNORE INTO revision VALUES (1,0)')
        self.db.commit()

    def values(self, kind):
        return {key: json.loads(value) for key, value in self.db.execute('SELECT id,value FROM state WHERE kind=?', (kind,))}

    def revision(self):
        return self.db.execute('SELECT value FROM revision WHERE id=1').fetchone()[0]

    def put(self, kind, key, value):
        with self.lock, self.db:
            self.db.execute('INSERT OR REPLACE INTO state VALUES (?,?,?)', (kind, key, json.dumps(value)))
            self.db.execute('UPDATE revision SET value=value+1 WHERE id=1')

    def delete(self, kind, key=None):
        with self.lock, self.db:
            if key is None:
                self.db.execute('DELETE FROM state WHERE kind=?', (kind,))
            else:
                self.db.execute('DELETE FROM state WHERE kind=? AND id=?', (kind, key))
            self.db.execute('UPDATE revision SET value=value+1 WHERE id=1')
