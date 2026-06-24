import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

class PostgresCursor:
    def __init__(self, items):
        self.items = items

    def sort(self, key_or_list, direction=None):
        sort_keys = []
        if isinstance(key_or_list, list):
            sort_keys = key_or_list
        elif isinstance(key_or_list, str):
            direction_val = direction if direction is not None else 1
            sort_keys = [(key_or_list, direction_val)]
            
        def get_val(item, key):
            val = item.get(key)
            if val is None:
                return ""
            return val
            
        for key, dir_val in reversed(sort_keys):
            reverse = (dir_val == -1)
            self.items.sort(key=lambda x: get_val(x, key), reverse=reverse)
            
        return self

    async def to_list(self, length=None):
        if length is not None:
            return self.items[:length]
        return self.items

class services_collection:
    def __init__(self, db_url):
        self.db_url = db_url

    def _connect(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    async def find_one(self, filter, projection=None):
        conn = self._connect()
        cursor = conn.cursor()
        
        where_clauses = []
        params = []
        for k, v in filter.items():
            where_clauses.append(f"{k} = %s")
            params.append(v)
            
        where_str = " AND ".join(where_clauses)
        query = f"SELECT * FROM services WHERE {where_str}"
        
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()
        
        if row:
            d = dict(row)
            d["active"] = bool(d["active"])
            return d
        return None

    async def count_documents(self, filter):
        conn = self._connect()
        cursor = conn.cursor()
        query = "SELECT COUNT(*) FROM services"
        params = []
        if filter:
            where_clauses = []
            for k, v in filter.items():
                where_clauses.append(f"{k} = %s")
                params.append(v)
            query += " WHERE " + " AND ".join(where_clauses)
        cursor.execute(query, params)
        count = cursor.fetchone()['count']
        conn.close()
        return count

    def find(self, filter=None, projection=None):
        conn = self._connect()
        cursor = conn.cursor()
        query = "SELECT * FROM services"
        params = []
        if filter:
            where_clauses = []
            for k, v in filter.items():
                where_clauses.append(f"{k} = %s")
                params.append(v)
            query += " WHERE " + " AND ".join(where_clauses)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        items = []
        for r in rows:
            d = dict(r)
            d["active"] = bool(d["active"])
            items.append(d)
            
        return PostgresCursor(items)

    async def insert_one(self, doc):
        conn = self._connect()
        cursor = conn.cursor()
        columns = ", ".join(doc.keys())
        placeholders = ", ".join(["%s"] * len(doc))
        values = list(doc.values())
        
        cursor.execute(f"INSERT INTO services ({columns}) VALUES ({placeholders})", values)
        conn.commit()
        conn.close()

    async def insert_many(self, docs):
        if not docs:
            return
        conn = self._connect()
        cursor = conn.cursor()
        columns = ", ".join(docs[0].keys())
        placeholders = ", ".join(["%s"] * len(docs[0]))
        
        values_list = [list(doc.values()) for doc in docs]
        cursor.executemany(f"INSERT INTO services ({columns}) VALUES ({placeholders})", values_list)
        conn.commit()
        conn.close()

    async def update_one(self, filter, update):
        conn = self._connect()
        cursor = conn.cursor()
        
        where_clauses = []
        where_params = []
        for k, v in filter.items():
            where_clauses.append(f"{k} = %s")
            where_params.append(v)
            
        set_clauses = []
        set_params = []
        for k, v in update.get("$set", {}).items():
            set_clauses.append(f"{k} = %s")
            set_params.append(v)
            
        query = f"UPDATE services SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
        cursor.execute(query, set_params + where_params)
        conn.commit()
        conn.close()

    async def delete_one(self, filter):
        conn = self._connect()
        cursor = conn.cursor()
        
        where_clauses = []
        where_params = []
        for k, v in filter.items():
            where_clauses.append(f"{k} = %s")
            where_params.append(v)
            
        query = f"DELETE FROM services WHERE {' AND '.join(where_clauses)}"
        cursor.execute(query, where_params)
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        class DeleteResult:
            def __init__(self, count):
                self.deleted_count = count
        return DeleteResult(deleted_count)

class bookings_collection:
    def __init__(self, db_url):
        self.db_url = db_url

    def _connect(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    async def find_one(self, filter, projection=None):
        conn = self._connect()
        cursor = conn.cursor()
        
        where_clauses = []
        params = []
        for k, v in filter.items():
            where_clauses.append(f"{k} = %s")
            params.append(v)
            
        where_str = " AND ".join(where_clauses)
        query = f"SELECT * FROM bookings WHERE {where_str}"
        
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None

    def find(self, filter=None, projection=None):
        conn = self._connect()
        cursor = conn.cursor()
        
        query = "SELECT * FROM bookings"
        params = []
        
        if filter:
            where_clauses = []
            for k, v in filter.items():
                if k == "$or":
                    or_clauses = []
                    for or_cond in v:
                        sub_clauses = []
                        for sub_k, sub_v in or_cond.items():
                            sub_clauses.append(f"{sub_k} = %s")
                            params.append(sub_v)
                        or_clauses.append("(" + " AND ".join(sub_clauses) + ")")
                    where_clauses.append("(" + " OR ".join(or_clauses) + ")")
                elif isinstance(v, dict) and "$regex" in v:
                    regex_val = v["$regex"]
                    if regex_val.startswith("^"):
                        regex_val = regex_val[1:]
                    where_clauses.append(f"{k} LIKE %s")
                    params.append(f"{regex_val}%")
                else:
                    where_clauses.append(f"{k} = %s")
                    params.append(v)
                    
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
                
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        items = [dict(r) for r in rows]
        return PostgresCursor(items)

    async def insert_one(self, doc):
        conn = self._connect()
        cursor = conn.cursor()
        
        columns = ", ".join(doc.keys())
        placeholders = ", ".join(["%s"] * len(doc))
        values = list(doc.values())
        
        cursor.execute(f"INSERT INTO bookings ({columns}) VALUES ({placeholders})", values)
        conn.commit()
        conn.close()

    async def update_one(self, filter, update):
        conn = self._connect()
        cursor = conn.cursor()
        
        where_clauses = []
        where_params = []
        for k, v in filter.items():
            where_clauses.append(f"{k} = %s")
            where_params.append(v)
            
        set_clauses = []
        set_params = []
        for k, v in update.get("$set", {}).items():
            set_clauses.append(f"{k} = %s")
            set_params.append(v)
            
        query = f"UPDATE bookings SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
        cursor.execute(query, set_params + where_params)
        conn.commit()
        conn.close()

    async def update_many(self, filter, update):
        pass

    async def delete_one(self, filter):
        conn = self._connect()
        cursor = conn.cursor()
        
        where_clauses = []
        where_params = []
        for k, v in filter.items():
            where_clauses.append(f"{k} = %s")
            where_params.append(v)
            
        query = f"DELETE FROM bookings WHERE {' AND '.join(where_clauses)}"
        cursor.execute(query, where_params)
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        class DeleteResult:
            def __init__(self, count):
                self.deleted_count = count
        return DeleteResult(deleted_count)

class config_collection:
    def __init__(self, db_url):
        self.db_url = db_url

    def _connect(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    async def find_one(self, filter, projection=None):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM config WHERE id = %s", (filter.get("_id", "pins"),))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"_id": row["id"], "worker_pin": row["worker_pin"], "owner_pin": row["owner_pin"]}
        return None

    async def insert_one(self, doc):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO config (id, worker_pin, owner_pin) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (doc["_id"], doc["worker_pin"], doc["owner_pin"])
        )
        conn.commit()
        conn.close()

    async def update_one(self, filter, update):
        conn = self._connect()
        cursor = conn.cursor()
        set_clauses = []
        params = []
        for k, v in update.get("$set", {}).items():
            set_clauses.append(f"{k} = %s")
            params.append(v)
        params.append(filter.get("_id", "pins"))
        query = f"UPDATE config SET {', '.join(set_clauses)} WHERE id = %s"
        cursor.execute(query, params)
        conn.commit()
        conn.close()

class counters_collection:
    def __init__(self, db_url):
        self.db_url = db_url

    def _connect(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    async def find_one_and_update(self, filter, update, upsert=False, return_document=False):
        conn = self._connect()
        cursor = conn.cursor()
        counter_id = filter.get("_id")
        
        cursor.execute("SELECT seq FROM counters WHERE id = %s FOR UPDATE", (counter_id,))
        row = cursor.fetchone()
        
        inc_val = update.get("$inc", {}).get("seq", 1)
        
        if not row:
            if upsert:
                cursor.execute("INSERT INTO counters (id, seq) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET seq = counters.seq + EXCLUDED.seq", (counter_id, inc_val))
                seq = inc_val
            else:
                conn.close()
                return None
        else:
            seq = row["seq"] + inc_val
            cursor.execute("UPDATE counters SET seq = %s WHERE id = %s", (seq, counter_id))
            
        conn.commit()
        conn.close()
        
        return {"_id": counter_id, "seq": seq}

class PostgresDB:
    def __init__(self, db_url):
        self.db_url = db_url
        self.services = services_collection(db_url)
        self.bookings = bookings_collection(db_url)
        self.config = config_collection(db_url)
        self.counters = counters_collection(db_url)
        self._init_tables()

    def _init_tables(self):
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id TEXT PRIMARY KEY,
            category_id TEXT NOT NULL,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT,
            active BOOLEAN DEFAULT TRUE
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id TEXT PRIMARY KEY,
            token TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            vehicle_number TEXT NOT NULL,
            vehicle_photo TEXT,
            category_id TEXT NOT NULL,
            category_label TEXT NOT NULL,
            parent_category_id TEXT,
            parent_category_label TEXT,
            service_id TEXT NOT NULL,
            service_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            payment_provider TEXT,
            payment_status TEXT NOT NULL,
            status TEXT NOT NULL,
            worker_photo TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            id TEXT PRIMARY KEY,
            worker_pin TEXT,
            owner_pin TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS counters (
            id TEXT PRIMARY KEY,
            seq INTEGER NOT NULL DEFAULT 0
        )
        """)
        
        conn.commit()
        conn.close()

    def close(self):
        pass
