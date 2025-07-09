#!/bin/bash
set -e

echo "Starting entrypoint-standby.sh..."

# Primary’nin hazır olmasını bekle
until pg_isready -h primary_db -p 5432 -U "$REPLICATION_USER"; do
    echo "Waiting for primary to be ready..."
    sleep 3
done

# güncel veriyi çek
echo "Pulling data from primary..."
PGPASSWORD="$REPLICATION_PASSWORD" pg_basebackup -h primary_db -p 5432 -U "$REPLICATION_USER" -D /var/lib/postgresql/data --wal-method=stream -R -P

# Varsayılan Docker entrypoint'i çalıştır
echo "Handing over to docker..."
exec docker-entrypoint.sh -c config_file=/etc/postgresql/postgresql.conf -c hba_file=/etc/postgresql/pg_hba.conf