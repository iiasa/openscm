FROM scottyhardy/docker-wine:2.0.1

# installing python 3.7
ARG VIRTUAL_ENV=/opt/python3
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y make curl git unzip graphviz python3.7 python3-pip python3.7-dev python3.7-venv && \
    rm -rf /var/lib/apt/lists/*

RUN python3.7 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN which pip
RUN pip install --upgrade pip==20.0.2 && \
    chown -R wineuser ${VIRTUAL_ENV}

COPY . /work
RUN chown -R wineuser /work
