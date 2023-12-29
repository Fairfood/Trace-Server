"""Fabfile for remote server deployment.

Built with fabric2 Functions related to gitlab
"""
import requests
from fabric2 import task
from invoke.context import Context
from requests.exceptions import HTTPError

from .constants import GIT_STASH_NO_CHANGE_MSG
from .constants import GITLAB_PRIVATE_TOKEN
from .constants import GITLAB_URL_MERGE_REQ
from .constants import PROJECT_ID


def get_current_branch(c):
    """Returns active local branch."""
    current_branch = c.run("git rev-parse --abbrev-ref HEAD").stdout[:-1]
    return current_branch


def get_current_local_branch(c):
    """Returns active local branch."""
    local_c = Context(c.config)
    return get_current_branch(local_c)


def create_mr(source_branch, target_branch=None, title=None, skip_input=False):
    if not target_branch:
        target_branch = input("Enter destination branch: [master]") or "master"
    if not title:
        title = input("Enter title for merge request:") or source_branch
    if skip_input:
        close_source_branch = "n"
    else:
        close_source_branch = input("Close source branch? [y/N]: ") or "n"
    close_source_branch = True if close_source_branch.lower() == "y" else False

    print("Creating merge request")
    payload = {
        "id": PROJECT_ID,
        "title": title,
        "source_branch": source_branch,
        "target_branch": target_branch,
        "remove_source_branch": close_source_branch,
    }
    headers = {"Private-Token": GITLAB_PRIVATE_TOKEN}
    response = requests.post(
        GITLAB_URL_MERGE_REQ, json=payload, headers=headers
    )
    response.raise_for_status()
    json_resp = response.json()
    print("Merge request created at %s/diffs" % json_resp["web_url"])


def push_and_create_mr(c, target_branch=None, title=None, skip_input=False):
    """For push changes to remote and creating merge request in the gitlab
    repo."""
    local_c = Context(c.config)
    current_branch = get_current_branch(local_c)
    if skip_input:
        source_branch = current_branch
        title = current_branch
    else:
        source_branch = (
            input("Enter source branch: [%s]" % current_branch)
            or current_branch
        )
    local_c.run("git push origin %s" % source_branch)
    create_mr(source_branch, target_branch, title, skip_input)


@task
def create_mr_to_master(c, skip_input=False):
    """For creating merge request to master branch."""
    push_and_create_mr(c, "master", skip_input=skip_input)
    print("Successful!!")


@task
def create_mr_to_transition(c, skip_input=False):
    """For creating merge request to master branch."""
    push_and_create_mr(c, "transition", skip_input=skip_input)
    print("Successful!!")


def accept_mr(source_branch=None, target_branch=None, skip_input=False):
    if not skip_input:
        source_branch = (
            input("Enter source branch: [%s]" % source_branch) or source_branch
        )
    if not target_branch:
        target_branch = (
            input("Enter destination branch: [%s]" % "master") or "master"
        )

    print(
        "Fetcing merge requests from %s to %s" % (source_branch, target_branch)
    )

    headers = {"Private-Token": GITLAB_PRIVATE_TOKEN}
    response = requests.get(
        "%s/?state=opened" % GITLAB_URL_MERGE_REQ, headers=headers
    )
    response.raise_for_status()
    mrs_json = response.json()
    mrs = []
    for mr in mrs_json:
        mr_branch = mr["source_branch"]
        mr_target_branch = mr["target_branch"]
        if mr_branch == source_branch:
            if mr_target_branch == target_branch:
                mrs.append(
                    {
                        "iid": mr["iid"],
                        "remove_source_branch": mr[
                            "force_remove_source_branch"
                        ],
                        "source_branch": mr_branch,
                    }
                )
    if not mrs:
        raise HTTPError("No matching merge request found")
    merge_all = True
    if len(mrs) > 1:
        merge_all = (
            input(
                "%d merge requests found, do you want to merge all? [y/N]: "
                % len(mrs)
            ).lower()
            or "n"
        )
        merge_all = True if merge_all == "y" else False
    if merge_all:
        for mr in mrs:
            iid = mr["iid"]
            accept_merge_url = "%s/%d/merge" % (GITLAB_URL_MERGE_REQ, iid)
            print("Accepting merge request from %s" % mr["source_branch"])
            response = requests.put(accept_merge_url, headers=headers)

            response.raise_for_status()
    return mrs


def accept_mr_and_update_local(c, target_branch=None, skip_input=False):
    """For accepting merge request."""

    local_c = Context(c.config)
    current_branch = get_current_branch(local_c)

    mrs = accept_mr(current_branch, target_branch, skip_input)

    local_c.run("git fetch origin")
    no_stash = GIT_STASH_NO_CHANGE_MSG in local_c.run("git stash").stdout[:-1]
    local_c.run("git checkout %s" % target_branch)
    local_c.run("git merge origin/%s" % target_branch)
    for mr in mrs:
        close_source_branch = bool(mr["remove_source_branch"])
        source_branch = bool(mr["source_branch"])

        if close_source_branch and current_branch is source_branch:
            local_c.run("git checkout development")
        else:
            local_c.run("git checkout %s" % current_branch)
            if not no_stash:
                local_c.run("git stash pop")

        if close_source_branch:
            c.run.warn()
            local_c.run("git branch -D %s" % source_branch)
            local_c.run("git push origin :%s" % source_branch)


@task
def accept_mr_to_master(c, skip_input=False):
    """For accepting merge request to master branch."""
    accept_mr_and_update_local(c, "master", skip_input=skip_input)


@task
def accept_mr_to_transition(c, skip_input=False):
    """For accepting merge request to master branch."""
    accept_mr_and_update_local(c, "transition", skip_input=skip_input)


@task
def update_local(local):
    current_branch = get_current_branch(local)
    no_stash = GIT_STASH_NO_CHANGE_MSG in local.run("git stash").stdout[:-1]
    local.run("git fetch origin")
    local.run("git checkout master")
    local.run("git merge origin/master")
    local.run("git checkout %s" % current_branch)

    if not no_stash:
        local.run("git stash pop")


def merge_to_development(local):
    """For merging master branch to development.

    1. Fetches master from remote
    2. Merges master to development
    3. Pushes development to remote
    4. Pulls development branch to development server
    """
    create_mr(
        source_branch="master",
        target_branch="development",
        title="Automatic Merge",
        skip_input=True,
    )
    accept_mr(
        source_branch="master", target_branch="development", skip_input=True
    )


def merge_to_staging(local):
    """For merging development branch to staging.

    1. Fetches development from remote
    2. Merges development to staging
    3. Pushes staging to remote
    4. Pulls staging branch to staging server
    """
    create_mr(
        source_branch="development",
        target_branch="staging",
        title="Automatic Merge",
        skip_input=True,
    )
    accept_mr(
        source_branch="development", target_branch="staging", skip_input=True
    )


def merge_to_production(local):
    """For merging staging branch to production.

    1. Fetches staging from remote
    2. Merges staging to production
    3. Pushes production to remote
    4. Pulls production branch to production server
    """
    create_mr(
        source_branch="staging",
        target_branch="production",
        title="Automatic Merge",
        skip_input=True,
    )
    accept_mr(
        source_branch="staging", target_branch="production", skip_input=True
    )
