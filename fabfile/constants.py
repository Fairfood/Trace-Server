"""File contains constants related to fabric.

This wouldn't need to be changed normally. Changing values in
project_variables.py would be sufficient.
"""
import os
import subprocess
import sys
import webbrowser
from configparser import NoOptionError
from configparser import NoSectionError
from configparser import RawConfigParser
from pathlib import Path

from hashids import Hashids

from .project_variables import DOMAIN_FORMAT
from .project_variables import PROJECT_ID
from .project_variables import PROJECT_NAME

# Packages

DB_PACKAGES = [
    "postgresql",
    "postgresql-contrib",
    "libpq-dev",
    "gdal-bin",
    "postgis",
]


# Base Configurations

SECRETS_PATH = "/etc/secret"
LOCAL_FAB_CONFIG_PATH = f"{SECRETS_PATH}/fabric/secret.ini"
HASHHID_MIN_LENGTH = 5
PASSWORD_MULTIPLIER = 50

MASTER_BRANCH = "master"
GITLAB_HOST = "git@git.cied.in"
GITLAB_URL_API_ROOT = "https://git.cied.in/api/v4"

SSL_SUPPORT_EMAIL = "support@cied.in"
SSH_PORT = 9261

COMMON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DUMP_DIR = os.path.join(
    COMMON_DIR, f"{PROJECT_NAME}", "database_dumps"
)

# Derived Configs

CONFIG_PATH = f"{SECRETS_PATH}/{PROJECT_NAME}/%s.ini"

DB_NAME = PROJECT_NAME
DB_USERNAME = PROJECT_NAME

try:
    fab_config = RawConfigParser()
    fab_config.read(LOCAL_FAB_CONFIG_PATH)
    GITLAB_PRIVATE_TOKEN = fab_config.get("gitlab", "TOKEN")
except (NoOptionError, NoSectionError) as e:
    if os.geteuid() != 0:
        subprocess.call(["sudo", "fab2", *sys.argv])
        sys.exit()

    Path(f"{SECRETS_PATH}/fabric").mkdir(parents=True, exist_ok=True)
    Path(LOCAL_FAB_CONFIG_PATH).touch(exist_ok=True)
    fab_config = RawConfigParser()
    fab_config.read(LOCAL_FAB_CONFIG_PATH)

    print(
        "You need to setup a personal gitlab token before you can access fab"
        " commands for gitlab"
    )
    print(
        "    1) Visit https://git.cied.in/profile/personal_access_tokens to"
        " create access_token"
    )
    print("    2) Provide a name (fabfile-token)")
    print("    3) Leave expiry date empty")
    print("    4) Check the api checkbox")
    print("    5) Create access token")
    print("    6) Copy access token")
    input("Click submit to go to url:")
    webbrowser.open_new_tab(
        "https://git.cied.in/profile/personal_access_tokens"
    )
    token = input("Enter token from GitLab: ")
    if isinstance(e, NoSectionError):
        fab_config.add_section("gitlab")
    fab_config["gitlab"]["TOKEN"] = token
    with open(LOCAL_FAB_CONFIG_PATH, "w") as configfile:
        fab_config.write(configfile)

HASHHID_SALT = fab_config.get("general", "HASHHID_SALT")
hasher = Hashids(min_length=HASHHID_MIN_LENGTH, salt=HASHHID_SALT)

# Git
GITLAB_URL_MERGE_REQ = (
    f"{GITLAB_URL_API_ROOT}/projects/{PROJECT_ID}/merge_requests"
)
GITLAB_URL_ADD_DEPLOY_KEY = (
    f"{GITLAB_URL_API_ROOT}/projects/{PROJECT_ID}/deploy_keys"
)
GIT_STASH_NO_CHANGE_MSG = "No local changes to save"

# Remote User
ROOT_USER = f"{PROJECT_NAME}user" + hasher.encode(PROJECT_ID)
ROOT_PASSWORD = hasher.encode(PROJECT_ID**PASSWORD_MULTIPLIER)
REMOTE_PROJECT_HOME = f"/home/{ROOT_USER}"
PROJECT_DIR = f"{REMOTE_PROJECT_HOME}/{PROJECT_NAME}"
PROJECT_GIT_DIR = f"{REMOTE_PROJECT_HOME}/{PROJECT_NAME}/.git"
VIRUTLAL_ENV_DIR = f"{REMOTE_PROJECT_HOME}/.virtualenvs/{PROJECT_NAME}"
PROJECT_SECRETS_PATH = f"{SECRETS_PATH}/{PROJECT_NAME}/%s.ini"

# Local configs
CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "configs"
)
VENV_CONFIG_DIR = os.path.join(CONFIG_DIR, "virtualenvwrapper")


DEVELOPMENT_HOST = f"{PROJECT_NAME}-dev"
STAGING_HOST = f"{PROJECT_NAME}-staging"
PRODUCTION_HOST = f"{PROJECT_NAME}-prod"
DEMO_HOST = f"{PROJECT_NAME}-demo"
TRANSITION_HOST = f"{PROJECT_NAME}-transition"

HOST_SETTINGS = {
    DEVELOPMENT_HOST: {
        "branch": "development",
        "environment": "development",
        "domain": DOMAIN_FORMAT.format(env=".dev"),
    },
    STAGING_HOST: {
        "branch": "staging",
        "environment": "staging",
        "domain": DOMAIN_FORMAT.format(env=".staging"),
    },
    PRODUCTION_HOST: {
        "branch": "production",
        "environment": "production",
        "domain": DOMAIN_FORMAT.format(env=""),
    },
    DEMO_HOST: {
        "branch": "demo",
        "environment": "production",
        "domain": DOMAIN_FORMAT.format(env=".demo"),
    },
    TRANSITION_HOST: {
        "branch": "transition",
        "environment": "development",
        "domain": DOMAIN_FORMAT.format(env=".transition"),
    },
}

for host, data in HOST_SETTINGS.items():
    env_config = RawConfigParser()
    env_config.read(CONFIG_PATH % data["branch"])
    try:
        HOST_SETTINGS[host]["db_password"] = env_config.get(
            "database", "DB_PASSWORD"
        )
    except Exception:
        HOST_SETTINGS[host]["db_password"] = PROJECT_NAME


class Colours:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
