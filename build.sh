#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
flask db upgrade
flask list-users
flask force-reset-admin
