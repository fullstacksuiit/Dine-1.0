from django.db.backends.signals import connection_created


def set_sqlite_pragmas(sender, connection, **kwargs):
    """Optimize SQLite performance with WAL mode and tuned pragmas."""
    if connection.vendor == 'sqlite':
        cursor = connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('PRAGMA synchronous=NORMAL;')
        cursor.execute('PRAGMA cache_size=-64000;')    # 64MB cache
        cursor.execute('PRAGMA temp_store=MEMORY;')
        cursor.execute('PRAGMA mmap_size=268435456;')  # 256MB mmap


connection_created.connect(set_sqlite_pragmas)
