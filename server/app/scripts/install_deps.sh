#!/bin/sh
set -eu

poetry install --no-interaction --no-ansi --without dev
