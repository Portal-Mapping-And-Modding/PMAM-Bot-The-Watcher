#!/bin/bash

echo "Starting The Watcher..."
./env/bin/python3 pmam_bot.py

echo "The Watcher has been shutdown, backing up the database..."
cp database.db database_backup.db
echo "Backup complete!"