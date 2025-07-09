#!/bin/bash
set -e

# Replikasyon kullanıcısını oluştur
echo "Creating replication user '$REPLICATION_USER'..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -d postgres <<-EOSQL
    CREATE ROLE $REPLICATION_USER WITH LOGIN PASSWORD '$REPLICATION_PASSWORD' REPLICATION;
EOSQL

echo "Replication setup completed on primary server."