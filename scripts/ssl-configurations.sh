#!/bin/bash
set -e

sudo apt update && sudo apt install openssl -y

SERVER_IP=$(curl -s ifconfig.me)

echo "Generating ssl certificate files..."
openssl genrsa -out rootCA.key 4096
openssl genrsa -out server.key 4096
openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 3650 -out rootCA.crt -subj "/C=TR/CN=RootCA"
openssl req -new -key server.key -out server.csr -subj "/C=TR/CN=$SERVER_IP"
openssl x509 -req -in server.csr -CA rootCA.crt -CAkey rootCA.key -CAcreateserial -out server.crt -days 3650 -sha256 -extfile <(echo -e "subjectAltName=IP:$SERVER_IP")

echo "Organizing generated files..."
mkdir -p ./config/secrets/ssl
cp rootCA.crt server.crt server.key ./config/secrets/ssl
rm rootCA.key rootCA.crt rootCA.srl server.key server.csr server.crt

echo "Setting permissions for Postgresql..."
sudo chown 999:999 ./config/secrets/ssl/*
sudo chmod 600 ./config/secrets/ssl/*

echo "SSL configurations completed."