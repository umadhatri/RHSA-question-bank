FROM docker:27-cli

# The worker is trusted orchestration code. It needs Python for the private
# graders and the Docker CLI to launch the untrusted rhsa-base sandbox.
RUN apk add --no-cache \
      aws-cli \
      bash \
      ca-certificates \
      coreutils \
      findutils \
      python3 \
      py3-jsonschema \
      py3-yaml

WORKDIR /opt/question-bank

COPY grader/ ./grader/
COPY schemas/ ./schemas/
COPY labs/ ./labs/
COPY worker/ ./worker/
COPY course.yaml ./course.yaml

ARG QUESTION_BANK_REVISION=unknown
ARG WORKER_VERSION=unknown
ENV QUESTION_BANK_ROOT=/opt/question-bank \
    QUESTION_BANK_REVISION=${QUESTION_BANK_REVISION} \
    RHSA_WORKER_VERSION=${WORKER_VERSION} \
    PYTHONUNBUFFERED=1 \
    DOCKER_HOST=unix:///var/run/docker.sock

LABEL org.opencontainers.image.title="CyberRange RHSA Grading Worker" \
      org.opencontainers.image.description="Trusted grading worker for Linux sysadmin Bash labs" \
      org.opencontainers.image.revision="${QUESTION_BANK_REVISION}" \
      org.opencontainers.image.version="${WORKER_VERSION}"

# Reference answers are instructor conveniences and are intentionally excluded
# from the runtime worker. Hidden grader.py files remain here, but never enter
# the student execution sandbox created by grader/runner.py.
RUN find /opt/question-bank/labs -type d -name reference -prune -exec rm -rf '{}' '+' \
    && chmod 0755 /opt/question-bank/worker/run_job.py

ENTRYPOINT ["python3", "/opt/question-bank/worker/run_job.py"]
