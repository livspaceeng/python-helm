FROM python:3.7-buster

ARG VCS_REF
ARG BUILD_DATE

# Metadata
LABEL org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.name="helm-kubectl" \
      org.label-schema.url="https://hub.docker.com/r/livspaceeng/python-helm/" \
      org.label-schema.vcs-url="https://github.com/livspaceeng/python-helm" \
      org.label-schema.build-date=$BUILD_DATE

# Note: Latest version of kubectl may be found at:
# https://github.com/kubernetes/kubernetes/releases
ENV KUBE_LATEST_VERSION="v1.16.2"
# Note: Latest version of helm may be found at:
# https://github.com/kubernetes/helm/releases
ENV HELM_VERSION="v2.11.0"

RUN wget -q https://storage.googleapis.com/kubernetes-release/release/${KUBE_LATEST_VERSION}/bin/linux/amd64/kubectl -O /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl \
    && wget -q https://storage.googleapis.com/kubernetes-helm/helm-${HELM_VERSION}-linux-amd64.tar.gz -O - | tar -xzO linux-amd64/helm > /usr/local/bin/helm \
    && chmod +x /usr/local/bin/helm

RUN pip install PyYaml

COPY build.py /usr/local/bin/build.py
COPY diff.py /usr/local/bin/diff.py
COPY helm-install.py /usr/local/bin/helm-install.py

RUN chmod +x /usr/local/bin/build.py /usr/local/bin/diff.py /usr/local/bin/helm-install.py

ENV CMD_BUILD="build.py"
ENV CMD_DIFF="diff.py"
ENV CMD_INSTALL="helm-install.py"
ENV VALUES_DIR="values"

WORKDIR /config

CMD bash
