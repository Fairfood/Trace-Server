#!/bin/bash


PROJECT="fairtrace_v2"
# Directory to which the code is cloned
# PROJECT_DIR="$PROJECT"
PROJECT_DIR="fairtrace_v2"
# Location of manage.py file
MNAGE_DIR=$PROJECT
# DB name used to back up before migrating
DB_NAME=$PROJECT

#Slack notification web hook url
# # SLACK_WEBHOOK="https://hooks.slack.com/services/TQ9FM59BR/B018VA00BQD/\
#     wKYSkVYNJJpyI7RgK1oQ4s0r"

# DB backup before migration

# directory is created in the home
BACKUP_DIR='cicd_auto_db_backup'
BACKUP_NAME="$(date +%Y-%m-%d_%H-%M-%S)"
# only last MAX_BACKUPS - 1 (here recent 10 items) will kept inn remote server
declare -i MAX_BACKUPS=10
# Directories need to be backed up other than DB.
ADDITIONAL_BACKUP_PATHS=($PROJECT_DIR "/etc/secret/$PROJECT/secret.ini")


# Supervisor Services: used to restart the services in server reload.

SUPERVISOR_SERVS=(gunicorn celery-ci-queue celery-high celery-low celerybeat)


# SSH config key names in gitlab secrete for each env.
development="SSH_CONFIG_DEV"
stage="SSH_CONFIG_STAGE"
production="SSH_CONFIG_PROD"
demo="SSH_CONFIG_DEMO"
