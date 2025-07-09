#!/bin/bash
set -e

echo "Generating log files..."
touch primary.log standby.log rabbitmq.log

echo "Organizing generated files..."
mkdir -p ./logs
mv primary.log standby.log rabbitmq.log ./logs

echo "Setting permissions for Postgresql..."
sudo chown 999:999 ./logs
sudo chown 999:999 ./logs/*
sudo chmod 777 ./logs
sudo chmod 666 ./logs/*

echo "Log configurations completed."