#!/bin/bash

# sourcing the constants file using relative path
# since it is called from gitlab.yml

. cicd/constants.sh

set -euo pipefail

FAILURE=1
SUCCESS=0
STATUS=$?


function compose_msg() {

    local slack_msg_header
    local slack_msg_body
    local slack_channel

    # Populate header and define slack channels
    slack_msg_header=":x: *Deployment of Backend to <${CI_PIPELINE_URL}|${CI_ENVIRONMENT_NAME}> failed!*"
    slack_msg_body="Project: <${CI_PROJECT_URL}|${CI_PROJECT_TITLE}> \n Branch: <${CI_PROJECT_URL}/-/tree/${CI_COMMIT_BRANCH}|${CI_COMMIT_BRANCH}> \n Initiator: ${GITLAB_USER_NAME} \n Commit: <${CI_PROJECT_URL}/commits/${CI_COMMIT_BRANCH}|${CI_COMMIT_REF_NAME}>- ${CI_COMMIT_MESSAGE}"
    msg_margin_colour="#961D13"
    msg_image="https://emojis.slackmojis.com/emojis/images/1542340464/4968/fart.gif?1542340464"
    if [[ "${STATUS}" == "${SUCCESS}" ]]; then
        slack_msg_header="*Successfully Deployed the Backend to <${CI_PIPELINE_URL}|${CI_ENVIRONMENT_NAME}>*"
        msg_margin_colour="#36a64f"
        msg_image="https://emojis.slackmojis.com/emojis/images/1450694616/220/bananadance.gif?1450694616"
    fi

    # Create slack message body
    cat <<-SLACK
      {
        "channel": "${SLACK_CHANNEL}",
        "attachments": [
          {
            "color": "${msg_margin_colour}",
            "blocks": [
              {
                "type": "section",
                "text": {
                  "type": "mrkdwn",
                  "text": "${slack_msg_header}"
                }
              },
              {
                "type": "section",
                "text": {
                  "type": "mrkdwn",
                  "text": "${slack_msg_body}"
                },
                "accessory": {
                  "type": "image",
                  "image_url": "${msg_image}",
                  "alt_text": "done"
                }
              }
            ]
          }
        ]
}
SLACK
}

function slack_notify() {
    echo $(compose_msg)
    curl -X POST --data-urlencode "payload=$(compose_msg)" "${SLACK_WEBHOOK}"
}

slack_notify
