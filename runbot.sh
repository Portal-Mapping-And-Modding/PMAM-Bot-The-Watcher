#!/bin/bash

export $(grep -v '^#' .env | xargs)

echo "Pulling any new changes on PMAM-Bot/main..."
git pull
echo "Finished git pull!"

echo "Starting The Watcher..."

if ! ./.venv/bin/python3 pmam_bot.py; then
   echo "Bot has shutdown with a error!"
   echo "Backing up the database..."
   cp database.db database_backup.db
   echo "Backup complete!"
   exit 1
fi

echo "The Watcher has been shutdown, backing up the database..."
cp database.db database_backup.db
echo "Backup complete!"