from psycopg_pool import ConnectionPool
from cashew.config import DATABASE_URL

pool: ConnectionPool = ConnectionPool(
    DATABASE_URL,
    min_size=1,
    max_size=5,
)