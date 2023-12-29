"""Fabfile for remote server deployment.

Built with fabric2 Reference: Gitlab APIs:
https://docs.gitlab.com/ee/api/users.html#add-ssh-key Postgres:
https://www.digitalocean.com/community/tutorials/how-to-install-and-use
-postgresql-on-ubuntu-18-04 503 Bad gateway Digital Ocean :
https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with
-postgres-nginx-and-gunicorn-on-ubuntu-16-04 Change user permissions:
https://kb.iu.edu/d/abdb
"""
import os
import socket

import requests
from django.utils.timezone import datetime
from fabric2 import task
from invoke import Responder
from invoke.context import Context

from .constants import Colours
from .constants import CONFIG_DIR
from .constants import DATABASE_DUMP_DIR
from .constants import DB_NAME
from .constants import DB_PACKAGES
from .constants import DB_USERNAME
from .constants import DEVELOPMENT_HOST
from .constants import GITLAB_HOST
from .constants import GITLAB_PRIVATE_TOKEN
from .constants import GITLAB_URL_ADD_DEPLOY_KEY
from .constants import HOST_SETTINGS
from .constants import PRODUCTION_HOST
from .constants import PROJECT_DIR
from .constants import PROJECT_NAME
from .constants import PROJECT_SECRETS_PATH
from .constants import REMOTE_PROJECT_HOME
from .constants import ROOT_PASSWORD
from .constants import ROOT_USER
from .constants import SSH_PORT
from .constants import SSL_SUPPORT_EMAIL
from .constants import STAGING_HOST
from .constants import TRANSITION_HOST
from .constants import VENV_CONFIG_DIR
from .constants import VIRUTLAL_ENV_DIR
from .git import accept_mr_to_master
from .git import accept_mr_to_transition
from .git import create_mr_to_master
from .git import create_mr_to_transition
from .git import get_current_branch
from .git import merge_to_development
from .git import merge_to_production
from .git import merge_to_staging
from .project_variables import PROJECT_GITLAB_SSH

# import logging
# logging.basicConfig(level=logging.DEBUG)

sudopass = Responder(
    pattern=r"\[sudo\] password:",
    response=f"{ROOT_PASSWORD}\n",
)

respond_yes = Responder(
    pattern=r"\[Y/n\]",
    response="\n",
)
respond_no = Responder(
    pattern=r"\[y/N\]",
    response="\n",
)
respond_yes_2 = Responder(
    pattern=r"\(y\|n\)",
    response="y\n",
)

watchers = [sudopass, respond_yes, respond_yes_2, respond_no]


def log(message):
    print(f"{Colours.BOLD}######### {message} #########{Colours.ENDC}")


def fail(message):
    print(f"{Colours.FAIL}######### {message} #########{Colours.ENDC}")


def alert(message):
    print(f"{Colours.WARNING} {message} {Colours.ENDC}")


def bold(message):
    print(f"{Colours.BOLD} {message} {Colours.ENDC}")


def sudo(c, *args, **kwargs):
    log("Running " + "|".join(args))
    c.sudo(watchers=watchers, *args, **kwargs)


def run(c, *args, **kwargs):
    log("Running " + "|".join(args))
    c.run(watchers=watchers, *args, **kwargs)


@task(hosts=[DEVELOPMENT_HOST])
def prepare_development_server(c):
    log("Setting up development server.")
    global host
    host = DEVELOPMENT_HOST
    prepare_server(c)


@task(hosts=[STAGING_HOST])
def prepare_staging_server(c):
    log("Setting up staging server.")
    global host
    host = STAGING_HOST
    prepare_server(c)


@task(hosts=[PRODUCTION_HOST])
def prepare_production_server(c):
    log("Setting up production server.")
    global host
    host = PRODUCTION_HOST
    prepare_server(c)


@task(hosts=[DEVELOPMENT_HOST])
def setup_development_server(c):
    log("Setting up development server.")
    global host
    host = DEVELOPMENT_HOST
    setup_server(c)


@task(hosts=[STAGING_HOST])
def setup_staging_server(c):
    log("Setting up staging server.")
    global host
    host = STAGING_HOST
    setup_server(c)


@task(hosts=[PRODUCTION_HOST])
def setup_production_server(c):
    log("Setting up production server.")
    global host
    host = PRODUCTION_HOST
    setup_server(c)


@task
def prepare_server(c):
    log(f"SSHing to {host} host.")
    sudo(c, "apt-get update")
    setup_stage(1)
    install_essentials(c)
    setup_stage(6)
    setup_nginx(c)
    setup_stage(1)
    setup_ufw(c)
    setup_stage(3)
    setup_fail2ban(c)
    setup_stage(3)
    create_user(c)
    setup_stage(2)
    update_config(c)
    setup_ssl(c)
    setup_stage(11)
    log(f"SSH port has been changed to {SSH_PORT}")
    log(f"User {ROOT_USER} has been created")
    log("Update SSH Config and add lines")
    log(f"\t1) Port {SSH_PORT}")
    log(f"\t2) user {ROOT_USER}")


@task
def setup_server(c):
    environment = HOST_SETTINGS[host]["environment"]
    setup_stage(4)
    setup_db(c, environment)
    setup_stage(5)
    setup_virtualenwrapper(c, environment)
    setup_stage(7)
    setup_supervisor(c)
    setup_stage(8)
    setup_gitlab_ssh(c)
    setup_stage(9)
    sudo(c, "apt-get update")
    run_bash(c, "source /usr/local/bin/virtualenvwrapper.sh")
    setup_project(c, environment, host)
    setup_stage(10)
    print("Successful!!")


def update_config(c):
    sudo(
        c,
        "sudo sed -re"
        " 's/^(\#)(PasswordAuthentication)"  # noqa W605
        "([[:space:]]+)(.*)/\\2\\3\\4/'"
        " -i.`date -I` /etc/ssh/sshd_config",
    )
    sudo(
        c,
        "sudo sed -re 's/^(PasswordAuthentication)([[:space:]]+)yes/\\1\\2no/'"
        " -i.`date -I` /etc/ssh/sshd_config",
    )
    sudo(
        c,
        "sudo sed -re 's/^(\#)(Port)([[:space:]]*)"  # noqa W605
        "(.*)/\\2\\3\\4/' -i.`date"
        " -I` /etc/ssh/sshd_config",
    )
    sudo(
        c,
        "sudo sed -re 's/^(Port)([[:space:]]*)22/\\1\\2%d/' -i.`date -I`"
        " /etc/ssh/sshd_config" % SSH_PORT,
    )
    sudo(c, "service ssh restart")


def create_user(c):
    try:
        create_user_cmd = (
            'adduser --disabled-password --force-badname --gecos ""'
            f" {ROOT_USER}"
        )
        print(create_user_cmd)
        sudo(c, create_user_cmd)
        set_password_comand = (
            f'echo "{ROOT_PASSWORD}\n{ROOT_PASSWORD}" | sudo passwd'
            f" {ROOT_USER}"
        )
        run(c, set_password_comand)
        grant_sudo_access_cmd = f"usermod -a -G sudo {ROOT_USER}"
        sudo(c, grant_sudo_access_cmd)
        sudo(c, f"cp -r /root/.ssh {REMOTE_PROJECT_HOME}/")
        sudo(c, f"chown -R {ROOT_USER}:{ROOT_USER} {REMOTE_PROJECT_HOME}/")
        sudo(
            c,
            "sed -re 's/^(.*)(ssh-rsa)(.*)/\\2\\3/' -i.`date -I`"
            f" {REMOTE_PROJECT_HOME}/.ssh/authorized_keys",
        )
    except Exception:
        print("User already exists")


def install_essentials(c):
    log("Installing essentials.")
    install(c, "python-dev")
    install(c, "python3-pip")
    install(c, "git")


def setup_ufw(c):
    install(c, "ufw")
    install(c, "ssh")
    sudo(c, "ufw allow 'Nginx Full'")
    sudo(c, f"ufw allow {SSH_PORT}/tcp")
    sudo(c, "ufw allow 'OpenSSH'")
    sudo(c, "ufw enable")
    sudo(c, "systemctl reload nginx")
    sudo(c, "service ssh restart")


def setup_fail2ban(c):
    install(c, "fail2ban")
    sudo(c, "cp /etc/fail2ban/fail2ban.conf /etc/fail2ban/fail2ban.local")
    sudo(c, "cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local")
    sudo(c, "fail2ban-client set sshd bantime 35m")
    sudo(c, "fail2ban-client set sshd findtime 12m")
    sudo(c, "fail2ban-client set sshd maxretry 3")

    jail_local = render_config_file(
        os.path.join(CONFIG_DIR, "fail2ban", "jail.local")
    )
    log(jail_local)
    upload_file(
        c,
        local_path=jail_local,
        remote_path=None,
        mode=600,
        temp=True,
        use_sudo=True,
        home=None,
    )
    slack_notify = render_config_file(
        os.path.join(CONFIG_DIR, "fail2ban", "slack-notify.conf")
    )
    log(slack_notify)
    upload_file(
        c,
        local_path=slack_notify,
        remote_path="/etc/fail2ban/action.d/slack-notify.conf",
        home=None,
        mode=600,
        temp=True,
        use_sudo=True,
    )

    sudo(c, "cat ~/jail.local_temp | sudo tee -a /etc/fail2ban/jail.local")
    sudo(c, "systemctl restart fail2ban")


def setup_db(c, environment):
    """For setting up database."""
    log("Preparing the DB.")
    sudo(c, "apt-get install " + " ".join(DB_PACKAGES) + " --assume-yes")
    try:
        create_user_cmd = "CREATE USER %s WITH PASSWORD '%s';" % (
            DB_USERNAME,
            HOST_SETTINGS[host]["db_password"],
        )
        mk_superuser_cmd = f"ALTER ROLE {DB_USERNAME} SUPERUSER;"
        sudo(c, f'-u postgres psql -c "{create_user_cmd}"')
        sudo(c, f'-u postgres psql -c "{mk_superuser_cmd}"')
        sudo(c, f"-u postgres createdb -O {DB_USERNAME} {DB_NAME}")
    except Exception:
        log(f"DB {DB_NAME} was already created.")


def setup_virtualenwrapper(c, environment):
    log("Setting up virtualenvwrapper")
    sudo(c, "-H pip3 install virtualenvwrapper")
    bash_profile = render_config_file(
        os.path.join(VENV_CONFIG_DIR, "bash_profile")
    )
    log("Moving config file.")
    log(f"{REMOTE_PROJECT_HOME}/.bash_profile")
    upload_file(
        c, bash_profile, f"{REMOTE_PROJECT_HOME}/.bash_profile", "0664", True
    )
    log("Bash profile file moved.")
    run(c, f"source {REMOTE_PROJECT_HOME}/.bash_profile")
    log("Virtualenvwrapper setup completed")


def setup_nginx(c):
    install(c, "nginx")


def setup_supervisor(c):
    install(c, "supervisor")


def setup_gitlab_ssh(c):
    log("setting up Gitlab SSH keys in remote")
    try:
        run(
            c,
            f"ssh-keygen -t rsa -b 4096 -f {REMOTE_PROJECT_HOME}/.ssh/id_rsa"
            " -q -N ''",
        )
    except Exception:
        log("Proceeding with the existing pub key")
    download_file(c, f"{REMOTE_PROJECT_HOME}/.ssh/id_rsa.pub")
    with open("id_rsa.pub", "r") as keyfile:
        key = keyfile.read()
    os.remove("id_rsa.pub")

    title = f"{PROJECT_NAME}-{HOST_SETTINGS[host]['environment']}"
    title = f"{title} key added from {socket.gethostname()}"
    data = {"key": key, "title": title, "can_push": False}
    headers = {"PRIVATE-TOKEN": GITLAB_PRIVATE_TOKEN}
    print(GITLAB_URL_ADD_DEPLOY_KEY)
    response = requests.request(
        "POST", GITLAB_URL_ADD_DEPLOY_KEY, headers=headers, data=data
    )
    print(response.json())
    run(c, f"ssh -o StrictHostKeyChecking=no {GITLAB_HOST}")


def setup_project(c, environment, host):
    log("Setting up the project.")
    try:
        run_bash(c, f"mkproject -p python3 {PROJECT_NAME}")
    except Exception:
        pass
    with c.cd(PROJECT_DIR):
        try:
            run(c, f"git clone {PROJECT_GITLAB_SSH} .")
        except Exception:
            pass
        run(c, f"git fetch origin {HOST_SETTINGS[host]['branch']}")
        run(c, f"git checkout {HOST_SETTINGS[host]['branch']}")
        run(c, f"git pull origin {HOST_SETTINGS[host]['branch']}")

    upload_file(
        c,
        render_config_file(os.path.join(VENV_CONFIG_DIR, "postactivate")),
        f"{VIRUTLAL_ENV_DIR}/bin/postactivate",
        664,
        temp=True,
    )
    upload_file(
        c,
        render_config_file(os.path.join(VENV_CONFIG_DIR, "postdeactivate")),
        f"{VIRUTLAL_ENV_DIR}/bin/postdeactivate",
        664,
        temp=True,
    )

    try:
        sudo(c, "mkdir -p /etc/secret/")
        sudo(c, f"mkdir -p /etc/secret/{PROJECT_NAME}/")
    except Exception:
        print("Secret directory already exists")
        pass
    upload_secret_file(c, host)

    run_bash(c, "source /usr/local/bin/virtualenvwrapper.sh")

    workon(
        c, f"pip3 install -r ~/{PROJECT_NAME}/requirements/{environment}.txt"
    )
    workon(c, f"python3 {PROJECT_NAME}/manage.py collectstatic --noinput")
    workon(c, f"python3 {PROJECT_NAME}/manage.py migrate")

    # sudo('python manage.py initializedb')
    # sudo('python manage.py createcustomers')
    create_superuser = input("Create superuser? [y/n] : ")
    if create_superuser.lower() in ["y", "yes"]:
        workon(c, f"python3 {PROJECT_NAME}/manage.py createsuperuser")

    try:
        run(
            c,
            f"mkdir {PROJECT_DIR}/logs && touch"
            f" {PROJECT_DIR}/logs/gunicorn.log",
        )
    except Exception:
        log("Seems like logs DIRECTORY already exists")
    try:
        run(c, f"mkdir {PROJECT_DIR}/run")
    except Exception:
        log("Seems like run DIRECTORY already exists")
    upload_file(
        c,
        render_config_file(
            os.path.join(CONFIG_DIR, "supervisor", "project.conf")
        ),
        f"/etc/supervisor/conf.d/{PROJECT_NAME}.conf",
        600,
        True,
        use_sudo=True,
    )
    sudo(c, "supervisorctl update")

    upload_file(
        c,
        render_config_file(os.path.join(CONFIG_DIR, "nginx", "project")),
        f"/etc/nginx/sites-available/{PROJECT_NAME}",
        600,
        True,
        use_sudo=True,
    )
    sudo(
        c,
        "ln -sf"
        f" /etc/nginx/sites-available/{PROJECT_NAME}"
        " /etc/nginx/sites-enabled/",
    )
    sudo(c, "rm -f /etc/nginx/sites-enabled/default")
    sudo(c, "service nginx restart")


def setup_ssl(c):
    install(c, "ufw")
    sudo(c, "add-apt-repository ppa:certbot/certbot")
    install(c, "python-certbot-nginx")
    sudo(c, "systemctl reload nginx")
    domain = HOST_SETTINGS[host]["domain"]
    sudo(
        c,
        f"certbot --nginx -d {domain} --email {SSL_SUPPORT_EMAIL} --redirect"
        " --non-interactive --agree-tos",
    )


def reload_celery(c):
    """To reload celery."""
    sudo(c, "supervisorctl restart celery-high")
    sudo(c, "supervisorctl status celery-high")
    sudo(c, "supervisorctl restart celery-low")
    sudo(c, "supervisorctl status celery-low")


def reload_celerybeat(c):
    """To reload celery."""
    sudo(c, "supervisorctl restart celerybeat")
    sudo(c, "supervisorctl status celerybeat")


def reload_django(c):
    """To reload server."""
    print("Updating Supervisor..")
    sudo(c, "supervisorctl update")
    print("Restarting nginx..")
    sudo(c, "service nginx restart")
    print("Restarting gunicorn..")
    sudo(c, "supervisorctl restart gunicorn")


def clear_redis_cache(c):
    """Clear redis cache."""
    print("Clearing Cache..")
    run(c, "redis-cli flushall")


def reload_project(c):
    """To reload project."""
    reload_django(c)
    reload_celery(c)
    reload_celerybeat(c)
    clear_redis_cache(c)


def upload_secret_file(c, host):
    upload_file(
        c,
        PROJECT_SECRETS_PATH % HOST_SETTINGS[host]["branch"],
        f"{REMOTE_PROJECT_HOME}/secret.ini",
    )
    sudo(
        c,
        f"mv {REMOTE_PROJECT_HOME}/secret.ini"
        f" /etc/secret/{PROJECT_NAME}/secret.ini",
    )


def update_project(c, host):
    """To update project from git."""
    branch = HOST_SETTINGS[host]["branch"]
    environment = HOST_SETTINGS[host]["environment"]
    cmd = ""
    cmd += "cd %s;" % PROJECT_DIR
    cmd += "git checkout -f %s;" % branch
    cmd += "git fetch origin;"
    cmd += "git merge origin/%s --ff-only;" % branch
    run(c, cmd)

    cmd = "source %s/bin/activate;" % VIRUTLAL_ENV_DIR
    cmd += "cd %s;" % PROJECT_DIR
    cmd += "pip3 install -r requirements/%s.txt" % environment
    print("Installing requirements ...")
    run(c, cmd)

    cmd = "source %s/bin/activate;" % VIRUTLAL_ENV_DIR
    cmd += "cd %s;" % PROJECT_DIR
    cmd += (
        "python %s/manage.py collectstatic --settings=%s.settings.%s --noinput"
        % (
            PROJECT_NAME,
            PROJECT_NAME,
            environment,
        )
    )
    print("Collecting static files ...")
    run(c, cmd)

    cmd = "source %s/bin/activate;" % VIRUTLAL_ENV_DIR
    cmd += "cd %s;" % PROJECT_DIR
    cmd += "python %s/manage.py migrate --settings=%s.settings.%s" % (
        PROJECT_NAME,
        PROJECT_NAME,
        environment,
    )
    print("Migrate database ...")
    run(c, cmd)

    # cmd = 'source %s/bin/activate;' % VIRUTLAL_ENV_DIR
    # cmd += 'cd %s;' % PROJECT_DIR
    # cmd += 'python %s/manage.py install_labels --settings=%s.settings.%s' \
    #        % (PROJECT_NAME, PROJECT_NAME, environment)
    # print('Insalling Graph Labels ...')
    # run(c, cmd)


def deploy(c, host):
    """To deploy code to an environment."""
    update_project(c, host)
    reload_project(c)


@task(hosts=[DEVELOPMENT_HOST])
def reload_development(c):
    """Reloading development server."""
    deploy(c, DEVELOPMENT_HOST)
    print("Successful!!")


@task(hosts=[STAGING_HOST])
def reload_staging(c):
    """Reloading staging server."""
    deploy(c, STAGING_HOST)
    print("Successful!!")


@task(hosts=[PRODUCTION_HOST])
def reload_production(c):
    """Reloading production server."""
    deploy(c, PRODUCTION_HOST)
    print("Successful!!")


@task(hosts=[DEVELOPMENT_HOST])
def push_to_development(c):
    """
    For pushing code to development server
        1. Merges master branch to development
        2. Reloads nginx, gunicorn, celery, beat etc in development server
    """
    local_c = Context(c.config)
    current_branch = get_current_branch(local_c)
    merge_to_development(local_c)
    deploy(c, DEVELOPMENT_HOST)

    local_c.run("git checkout %s" % current_branch)
    print("Successful!!")


@task(hosts=[STAGING_HOST])
def release_to_staging(c):
    """
    For pushing code to staging server
        1. Merges development branch to staging
        2. Reloads nginx, gunicorn, celery, celery beat etc in staging server
    """
    local_c = Context(c.config)
    current_branch = get_current_branch(local_c)
    merge_to_staging(local_c)
    deploy(c, STAGING_HOST)

    local_c.run("git checkout %s" % current_branch)
    print("Successful!!")


@task(hosts=[PRODUCTION_HOST])
def release_to_production(c):
    """
    For pushing code to production server
        1. Merges staging branch to production
        2. Reloads nginx, gunicorn, celery, beat etc in production server
    """
    confirm = input(
        "Are you sure you want to push the code in staging to production?"
        " [y/N] :"
    )
    if not confirm.lower() == "y":
        return False
    local_c = Context(c.config)
    current_branch = get_current_branch(local_c)
    merge_to_production(local_c)
    deploy(c, PRODUCTION_HOST)

    local_c.run("git checkout %s" % current_branch)
    print("Successful!!")


@task(hosts=[DEVELOPMENT_HOST])
def quick_merge_to_master(c):
    create_mr_to_master(c, skip_input=True)
    accept_mr_to_master(c, skip_input=True)


def backup_db(c, host):
    """Backup postgres dump from server and download to local."""
    print(host)
    local_c = Context(c.config)
    print("Creating db dump ...")
    sudo(c, "-u postgres pg_dump -Fc %s > ~/db.dump" % DB_NAME)
    print("Fetching dump from remote to local ..")
    time_stamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    env = HOST_SETTINGS[host]["environment"]
    dump_path = f"{DATABASE_DUMP_DIR}/{time_stamp}_{env}.dump"
    run(local_c, f"scp %s:~/db.dump {dump_path}" % host)
    sudo(c, "rm ~/db.dump")


@task(hosts=[DEVELOPMENT_HOST])
def backup_development_db(c):
    """Backup development DB."""
    backup_db(c, DEVELOPMENT_HOST)


@task(hosts=[STAGING_HOST])
def backup_staging_db(c):
    """Backup staging DB."""
    backup_db(c, STAGING_HOST)


@task(hosts=[PRODUCTION_HOST])
def backup_production_db(c):
    """Backup production DB."""
    backup_db(c, PRODUCTION_HOST)


@task(hosts=[TRANSITION_HOST])
def backup_transition_db(c):
    """Backup production DB."""
    backup_db(c, TRANSITION_HOST)


@task(hosts=[TRANSITION_HOST])
def reload_transition(c):
    """Reloading transition server."""
    deploy(c, TRANSITION_HOST)
    print("Successful!!")


@task(hosts=[TRANSITION_HOST])
def push_to_transition(c):
    """
    For pushing code to development server
        1. Merges from current branch to transition
        2. Reloads nginx, gunicorn, celery, beat etc in transition server
    """
    reload_transition(c)
    print("Successful!!")


@task(hosts=[TRANSITION_HOST])
def quick_push_to_transition(c):
    create_mr_to_transition(c, skip_input=True)
    accept_mr_to_transition(c, skip_input=True)
    push_to_transition(c)


@task(hosts=[DEVELOPMENT_HOST])
def quick_push_to_development(c):
    quick_merge_to_master(c)
    push_to_development(c)


def install(c, packages):
    """For installing packages."""
    log(f"Installing {packages}.")
    sudo(c, f"apt install {packages} --assume-yes")


def upload_file(
    c,
    local_path=None,
    remote_path=None,
    mode=664,
    temp=False,
    use_sudo=False,
    home=REMOTE_PROJECT_HOME,
):
    """For uploading file."""
    home = "" if not home else home + "/"
    if local_path is None:
        local_path = c.prompt("Source file (relative path): ")

    if use_sudo:
        log(f"Uploading from {local_path} to {home}")
        c.put(local_path, home, mode)
        if remote_path:
            sudo(
                c,
                f"mv {home}{get_filename_from_path(local_path)} {remote_path}",
            )

    else:
        c.put(local_path, remote_path, mode)

    if temp:
        os.remove(local_path)


def download_file(c, remote_path=None, local_path=None):
    """For downloading file."""
    c.get(remote_path, local_path)


def setup_stage(level):
    # os.system('clear')
    stages = [
        "Successful: Completed updation in remote.",
        "Successful: Updated configs.",
        "Successful: Created User.",
        "Successful: Installed essentials",
        "Successful: DB setup completed",
        "Successful: Virtualenvwrapper configured.",
        "Successful: nginx installed.",
        "Successful: Supervisor installed.",
        "Successful: Setup gitlab SSH.",
        (
            "Successful: Setting up repository and project"
            " completedSuccessful: Setting up SSL completed"
        ),
    ]
    for stage in stages[:level]:
        print(f"{stages.index(stage) + 1}/{len(stages)}. {stage}")


def render_config_file(source_path):
    substitues = {
        "PROJECT_NAME": PROJECT_NAME,
        "DIRECTORY": os.getcwd(),
        "HOST_ENV": HOST_SETTINGS[host]["environment"],
        "PROJECT_DIR": PROJECT_DIR,
        "ROOT_USER": ROOT_USER,
        "REMOTE_PROJECT_HOME": REMOTE_PROJECT_HOME,
        "DOMAIN": HOST_SETTINGS[host]["domain"],
    }

    file_name = get_filename_from_path(source_path)
    print(f"Creating {file_name}....")
    template = open(source_path, "rt")
    output_file = open(f"{source_path}_temp", "w")

    for line in template:
        for key, value in substitues.items():
            line = line.replace(key, value)
        output_file.write(line)

    return output_file.name


def run_bash(c, command):
    run(c, f"/bin/bash -l -c '{command}'")


def prefix_bash(c, command):
    return c.prefix(f"/bin/bash -l -c '{command}'")


def cd_bash(c, command):
    return c.cd(f"/bin/bash -l -c '{command}'")


def workon(c, command):
    run_bash(c, f"workon {PROJECT_NAME} && {command}")


def get_filename_from_path(path):
    try:
        name = path.split("/")[-1]
        if not name:
            name = "temp_file"
    except Exception:
        name = path
    return name


@task(hosts=[DEVELOPMENT_HOST])
def upload_development_secret(c):
    """Upload /etc/secrets/projectname/development.ini to development
    server."""
    global host
    host = DEVELOPMENT_HOST
    upload_secret_file(c, host)


@task(hosts=[STAGING_HOST])
def upload_staging_secret(c):
    """Upload /etc/secrets/projectname/staging.ini to staging server."""
    global host
    host = STAGING_HOST
    upload_secret_file(c, host)


@task(hosts=[PRODUCTION_HOST])
def upload_production_secret(c):
    """Upload /etc/secrets/projectname/production.ini to production server."""
    global host
    host = PRODUCTION_HOST
    upload_secret_file(c, host)


@task(hosts=[DEVELOPMENT_HOST])
def development_root_pass(c):
    """To print development root pass."""
    global host
    host = DEVELOPMENT_HOST
    print(ROOT_PASSWORD)


def setup_celery(c):
    environment = HOST_SETTINGS[host]["environment"]
    log(f"Setting up celery and beat in {host}")
    alert("Please Make Sure the following.")
    alert(
        "1. Make sure the followings are added in the host requirements.txt."
    )
    alert("    1.1. celery")
    alert("    1.2. redis")

    alert(
        "2. File celery.py is added in the location of"
        "settings folder and values are adjusted. celery "
        "app is added in the init.py of the same folder"
    )
    alert(f"3. All changes are pushed to the {host} server.")

    configured = input("Have you configured all the above(y/n)?")
    if configured.lower() in ["n", "no"]:
        fail("Aborting. Re-run the command after configuring the above.")
        exit()

    workon(
        c, f"pip3 install -r ~/{PROJECT_NAME}/requirements/{environment}.txt"
    )
    try:
        workon(c, "celery --version")
    except ImportError as e:
        print(e)
        fail("Celery setup failed.")
        alert(f"Make sure Celery is added in the {host} requirements.")
        exit()

    install(c, "redis-server")

    upload_file(
        c,
        render_config_file(
            os.path.join(CONFIG_DIR, "celery", "celery-high.conf")
        ),
        "/etc/supervisor/conf.d/celery-high.conf",
        600,
        True,
        use_sudo=True,
    )
    upload_file(
        c,
        render_config_file(
            os.path.join(CONFIG_DIR, "celery", "celery-low.conf")
        ),
        "/etc/supervisor/conf.d/celery-low.conf",
        600,
        True,
        use_sudo=True,
    )

    upload_file(
        c,
        render_config_file(
            os.path.join(CONFIG_DIR, "celery", "celerybeat.conf")
        ),
        "/etc/supervisor/conf.d/celerybeat.conf",
        600,
        True,
        use_sudo=True,
    )

    try:
        sudo(c, "mkdir /var/log/celery/")
    except Exception:
        print("/logs/celery is already exists.")

    sudo(c, "touch /var/log/celery/worker.log")
    sudo(c, "touch /var/log/celery/beat.log")

    sudo(c, "supervisorctl reread")
    sudo(c, "supervisorctl update")

    reload_celery(c)
    reload_celerybeat(c)
    bold("Celery setup completed Successfully.")


@task(hosts=[DEVELOPMENT_HOST])
def setup_celery_development(c):
    """To setup celery."""
    global host
    host = DEVELOPMENT_HOST
    setup_celery(c)


@task(hosts=[STAGING_HOST])
def setup_celery_staging(c):
    """To setup celery."""
    global host
    host = STAGING_HOST
    setup_celery(c)


@task(hosts=[PRODUCTION_HOST])
def setup_celery_production(c):
    """To setup celery."""
    global host
    host = PRODUCTION_HOST
    setup_celery(c)
