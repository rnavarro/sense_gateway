#!/bin/bash

export PATH="${HOME}/.local/bin:${PATH}"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd ${DIR}

pipenv run python main.py