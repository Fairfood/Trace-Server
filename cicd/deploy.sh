#!/bin/bash

# sourcing the constants file using relative path
# since it is called from gitlab.yml
. cicd/constants.sh

function setup_ssh(){
    echo "Setting up SSH ..."
    apt-get update && apt-get install -y openssh-client && apt-get \
        install -y rsync && apt-get install -y sshpass && \
        apt-get install pv && apt-get install -y curl && \
        apt-get install -y openssl && apt-get install -y zip && \
        apt-get install -y python-pip

    # setting up ssh
    mkdir -p ~/.ssh
    # expecting private key in the gitlab cicd varables (server auth key)
    echo "$SSH_PRIVATE_KEY" | tr -d '\r' > ~/.ssh/id_rsa
    # copying ssh info from the gitlab variable and updating ssh config
    # ${!CI_ENVIRONMENT_NAME} return key nane set in the constants
    # SSH_CONFIG_DEV
    HOST_KEY=${!CI_ENVIRONMENT_NAME}
    echo "dynamic variables: ${!HOST_KEY}"
    echo "${!HOST_KEY}" >> ~/.ssh/config
    echo "    IdentityFile ~/.ssh/id_rsa" >> ~/.ssh/config
    echo "    StrictHostKeyChecking no" >> ~/.ssh/config
    chmod 600 ~/.ssh/id_rsa
    echo "$(<~/.ssh/config)"
}


# function remove_old_folders() {
#     # List files, sort by modification time, select the most recent
#     # $MAX_BACKUPS, and print their names then use rm command to remove them
#     echo "remove_old_folders ..."
#     local MAX_BACKUPS=$1
#     local BACKUP_DIR=$2
#     echo "Backup dir: $BACKUP_DIR"
#     cd "$HOME/$BACKUP_DIR/"
#     old_folders=$(ls -lt | grep '^d' | head -n -10 | awk '{print $NF}')
#     for folder in $old_folders; do
#         sudo rm -rf "$folder_path/$folder"
#         echo "Removed folder: $folder_path/$folder"
#     done
# }

function remove_old_files() {
    # List files, sort by modification time, select the most recent
    # $MAX_BACKUPS, and print their names then use rm command to remove them
    local MAX_BACKUPS=$1
    local BACKUP_DIR=$2
    echo "Backup dir: $BACKUP_DIR"
    cd "$HOME/$BACKUP_DIR/"
    files=$(ls  -t | tail -n +$MAX_BACKUPS)

    # Check if any files were found
    if [ -n "$files" ]; then
        echo "Files to be removed:"
        # Loop through each file and print its name
        echo "$files" | while read file; do
            echo "$file"
            rm $file
        done
    fi
}


function remove_old_backups() {
    # using typeset to copy the function to remote and execute.
    echo "Cleaning up old backup files ..."
    typeset -f remove_old_files | ssh $CI_ENVIRONMENT_NAME "$(cat); \
        remove_old_files '$MAX_BACKUPS' '$BACKUP_DIR'"
}


function backup_db() {
    echo "Creating DB backup ..."
    sshpass -p "$USER_PASS" ssh $CI_ENVIRONMENT_NAME "echo '$USER_PASS' \
        | sudo -S -u postgres pg_dump -Fc \
        $DB_NAME > ~/$BACKUP_DIR/$BACKUP_NAME/$BACKUP_NAME.dump"
}

function backup_directories() {
    echo "Creating Directory backup ..."
    for path in "${ADDITIONAL_BACKUP_PATHS[@]}"; do
        echo "Copying up $path"
        sshpass -p "$USER_PASS" ssh $CI_ENVIRONMENT_NAME "echo '$USER_PASS' \
        | sudo -S cp -r $path ~/$BACKUP_DIR/$BACKUP_NAME/"
    done
}

function compress_backup() {
    echo "Backup name $BACKUP_NAME"
    echo "Current dir: $(pwd)"
    echo "Compressing Backup..."
    BACKUP="~/$BACKUP_DIR/$BACKUP_NAME"
    ssh $CI_ENVIRONMENT_NAME zip --password $USER_PASS -r "$BACKUP.zip" "$BACKUP"
    # echo "Encrypting Backup..."
    # ssh $CI_ENVIRONMENT_NAME openssl enc -aes-256-cbc -salt -in "$BACKUP.zip" -out  \
    #     -pass file:"$BACKUP.enc" -pass pass:"$USER_PASS"

    # ssh $CI_ENVIRONMENT_NAME rm "$BACKUP.zip"
    sshpass -p "$USER_PASS" ssh $CI_ENVIRONMENT_NAME "echo '$USER_PASS' \
        | sudo -S rm -r $BACKUP"

}

function config_aws_cli() {
    echo "configuring CLI..."
    aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID"
    aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY"
    aws configure set default.region "$AWS_REGION"
    aws configure set default.output "json"
}


function install_aws_cli() {
    echo "Installing CLI..."
    pip install awscli

}

function upload_backup() {
    echo "Uploading backup to s3 ..."
    install_aws_cli
    config_aws_cli
    # copy file from remote to runner to upload
    rsync -avz  $CI_ENVIRONMENT_NAME:"$BACKUP_DIR/$BACKUP_NAME.zip" .
    # upload to s3 and remove the file
    aws s3 cp "$BACKUP_NAME.zip" s3://$BACKUP_BUCKET/"$PROJECT-$CI_ENVIRONMENT_NAME"/
    rm -f "$BACKUP_NAME.zip"
    echo "Completed uploading..."
}

function backup() {
    # All the files are copied to a folder in backup dir and then
    # kept as zips in the backup directory.
    echo "Creating Backup ..."
    # create the backup dir if doesn't exists
    ls
    ssh $CI_ENVIRONMENT_NAME test -d "~/$BACKUP_DIR" || \
    ssh $CI_ENVIRONMENT_NAME mkdir "~/$BACKUP_DIR"
    echo "directory is created"

    # All the files are copied to a folder and kept as zip in backup dir
    echo "Backup name $BACKUP_NAME"
    ssh $CI_ENVIRONMENT_NAME mkdir $"~/$BACKUP_DIR/$BACKUP_NAME"

    backup_directories
    backup_db
    compress_backup
    remove_old_backups
    if [ "$EXTERNAL_BACKUP" = "true" ]; then
        upload_backup
    fi
}



function reload_server() {
    echo "Reloading server ..."
    echo "Updating Supervisor.."
    sshpass -p "$USER_PASS" ssh $CI_ENVIRONMENT_NAME "echo '$USER_PASS' \
        | sudo -S supervisorctl update"
    echo "Restarting nginx.."
    sshpass -p "$USER_PASS" ssh $CI_ENVIRONMENT_NAME "echo '$USER_PASS' \
        | sudo -S service nginx restart"

    for process in "${SUPERVISOR_SERVS[@]}"
    do
        echo "Restarting $process"
        sshpass -p "$USER_PASS" ssh $CI_ENVIRONMENT_NAME "echo '$USER_PASS' \
        | sudo -S supervisorctl restart $process"
    done
    echo "Status.."
    sshpass -p "$USER_PASS" ssh $CI_ENVIRONMENT_NAME "echo '$USER_PASS' \
        | sudo -S supervisorctl status"
}


function load_code(){
    echo 'Installing requirements ...'
    ssh $CI_ENVIRONMENT_NAME "/bin/bash -l -c 'workon $PROJECT && \
        pip install -r ~/$PROJECT/requirements/$CI_ENVIRONMENT_NAME.txt' "
    echo 'Collecting static files ...'
    ssh $CI_ENVIRONMENT_NAME "/bin/bash -l -c 'workon $PROJECT && \
        python $MNAGE_DIR/manage.py collectstatic --noinput' "
    echo 'Running migrations ...'
    ssh $CI_ENVIRONMENT_NAME "/bin/bash -l -c 'workon $PROJECT && \
        python $MNAGE_DIR/manage.py migrate' "
}

function copy_code(){
    # copying repo content to server using rsync
    rsync -az ./ $CI_ENVIRONMENT_NAME:$PROJECT_DIR/
}

function deploy() {
    setup_ssh
    backup
    copy_code
    load_code
    reload_server
}
