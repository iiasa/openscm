#!/usr/bin/env bash

set -e

docker build --file .ci/Dockerfile --tag openscm-tests .

docker run -it --rm -w /src -v "$(pwd):/src" openscm-tests \
  pip install .[tests] && pytest
