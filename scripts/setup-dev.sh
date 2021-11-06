#!/bin/sh

setup() {
    poetry update
    poetry install pre-commit
}

if ! [ command -v poetry &> /dev/null ]; then
    setup
else
    echo "Poetry is not installed."
    exit
fi
