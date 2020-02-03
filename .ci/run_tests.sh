#!/usr/bin/env bash

set -e

docker build --file .ci/Dockerfile --tag openscm-tests .

docker run -it --rm -w /work \
  openscm-tests \
  bash -c "pip install -e .[tests,model-MAGICC6,model-MAGICC7] && pytest -x"
