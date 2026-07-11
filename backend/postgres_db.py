import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
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

class db_connection_context:
    def __init__(self, pool):
        self.pool = pool
        self.conn = None

    def __enter__(self):
        self.conn = self.pool.getconn()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is not None:
                try:
                    self.conn.rollback()
                except Exception:
                    pass
            self.pool.putconn(self.conn)

class services_collection:
    def __init__(self, pool):
        self.pool = pool

    async def find_one(self, filter, projection=None):
        with db_connection_context(self.pool) as conn:
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
            
            if row:
                d = dict(row)
                d["active"] = bool(d["active"])
                return d
            return None

    async def count_documents(self, filter):
        with db_connection_context(self.pool) as conn:
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
            return count

    def find(self, filter=None, projection=None):
        with db_connection_context(self.pool) as conn:
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
            
            items = []
            for r in rows:
                d = dict(r)
                d["active"] = bool(d["active"])
                items.append(d)
                
            return PostgresCursor(items)

    async def insert_one(self, doc):
        with db_connection_context(self.pool) as conn:
            cursor = conn.cursor()
            columns = ", ".join(doc.keys())
            placeholders = ", ".join(["%s"] * len(doc))
            values = list(doc.values())
            
            cursor.execute(f"INSERT INTO services ({columns}) VALUES ({placeholders})", values)
            conn.commit()

    async def insert_many(self, docs):
        if not docs:
            return
        with db_connection_context(self.pool) as conn:
            cursor = conn.cursor()
            columns = ", ".join(docs[0].keys())
            placeholders = ", ".join(["%s"] * len(docs[0]))
            values_list = [list(doc.values()) for doc in docs]
            cursor.executemany(f"INSERT INTO services ({columns}) VALUES ({placeholders})", values_list)
            conn.commit()

    async def update_one(self, filter, update):
        with db_connection_context(self.pool) as conn:
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
            rowcount = cursor.rowcount
            conn.commit()
            return rowcount

    async def delete_one(self, filter):
        with db_connection_context(self.pool) as conn:
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
            
            class DeleteResult:
                def __init__(self, count):
                    self.deleted_count = count
            return DeleteResult(deleted_count)

class bookings_collection:
    def __init__(self, pool):
        self.pool = pool

    async def find_one(self, filter, projection=None):
        with db_connection_context(self.pool) as conn:
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
            
            if row:
                return dict(row)
            return None

    def find(self, filter=None, projection=None):
        with db_connection_context(self.pool) as conn:
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
            
            items = []
            for r in rows:
                d = dict(r)
                if projection:
                    for k, v in projection.items():
                        if v == 0:
                            d.pop(k, None)
                items.append(d)
            return PostgresCursor(items)

    async def insert_one(self, doc):
        with db_connection_context(self.pool) as conn:
            cursor = conn.cursor()
            columns = ", ".join(doc.keys())
            placeholders = ", ".join(["%s"] * len(doc))
            values = list(doc.values())
            
            cursor.execute(f"INSERT INTO bookings ({columns}) VALUES ({placeholders})", values)
            conn.commit()

    async def update_one(self, filter, update):
        with db_connection_context(self.pool) as conn:
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
            rowcount = cursor.rowcount
            conn.commit()
            return rowcount

    async def update_many(self, filter, update):
        with db_connection_context(self.pool) as conn:
            cursor = conn.cursor()
            where_clauses = []
            where_params = []
            for k, v in filter.items():
                if isinstance(v, dict):
                    if "$lt" in v:
                        where_clauses.append(f"{k} < %s")
                        where_params.append(v["$lt"])
                    elif "$exists" in v:
                        if v["$exists"] is False:
                            where_clauses.append(f"{k} IS NULL")
                        else:
                            where_clauses.append(f"{k} IS NOT NULL")
                else:
                    where_clauses.append(f"{k} = %s")
                    where_params.append(v)
                    
            set_clauses = []
            set_params = []
            for k, v in update.get("$set", {}).items():
                set_clauses.append(f"{k} = %s")
                set_params.append(v)
                
            where_str = " AND ".join(where_clauses) if where_clauses else "1=1"
            query = f"UPDATE bookings SET {', '.join(set_clauses)} WHERE {where_str}"
            cursor.execute(query, set_params + where_params)
            conn.commit()

    async def delete_one(self, filter):
        with db_connection_context(self.pool) as conn:
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
            
            class DeleteResult:
                def __init__(self, count):
                    self.deleted_count = count
            return DeleteResult(deleted_count)

class config_collection:
    def __init__(self, pool):
        self.pool = pool

    async def find_one(self, filter, projection=None):
        with db_connection_context(self.pool) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM config WHERE id = %s", (filter.get("_id", "pins"),))
            row = cursor.fetchone()
            if row:
                return {"_id": row["id"], "worker_pin": row["worker_pin"], "owner_pin": row["owner_pin"]}
            return None

    async def insert_one(self, doc):
        with db_connection_context(self.pool) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO config (id, worker_pin, owner_pin) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
                (doc["_id"], doc["worker_pin"], doc["owner_pin"])
            )
            conn.commit()

    async def update_one(self, filter, update):
        with db_connection_context(self.pool) as conn:
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

class counters_collection:
    def __init__(self, pool):
        self.pool = pool

    async def find_one_and_update(self, filter, update, upsert=False, return_document=False):
        with db_connection_context(self.pool) as conn:
            cursor = conn.cursor()
            counter_id = filter.get("_id")
            inc_val = update.get("$inc", {}).get("seq", 1)
            
            query = """
            INSERT INTO counters (id, seq) VALUES (%s, %s)
            ON CONFLICT (id)
            DO UPDATE SET seq = counters.seq + EXCLUDED.seq
            RETURNING seq
            """
            cursor.execute(query, (counter_id, inc_val))
            row = cursor.fetchone()
            conn.commit()
            
            seq = row["seq"] if row else inc_val
            return {"_id": counter_id, "seq": seq}

class PostgresDB:
    def __init__(self, db_url):
        self.db_url = db_url
        self.pool = ThreadedConnectionPool(minconn=2, maxconn=20, dsn=db_url, cursor_factory=RealDictCursor)
        self.services = services_collection(self.pool)
        self.bookings = bookings_collection(self.pool)
        self.config = config_collection(self.pool)
        self.counters = counters_collection(self.pool)
        self._init_tables()

    def _init_tables(self):
        with db_connection_context(self.pool) as conn:
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
                completed_at TEXT,
                booking_source TEXT
            )
            """)
            try:
                cursor.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booking_source TEXT")
            except Exception:
                pass
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
            # Add performance indexes
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_status_payment ON bookings (status, payment_method, payment_status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_created_at ON bookings (created_at DESC)")
            except Exception as e:
                logger.warning(f"Could not create performance indexes: {e}")
            conn.commit()

    def close(self):
        if self.pool:
            try:
                self.pool.closeall()
            except Exception:
                pass
