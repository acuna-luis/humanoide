# The installer checks the existing parent image ID before this local build.
ARG APP2_BASE_IMAGE=app2-rfdetr:1.11.2-torch2.10.0-cu128
FROM ${APP2_BASE_IMAGE}
USER root
COPY requirements.txt /opt/app2/workflow-requirements.txt
RUN python -m pip install --report /opt/app2/workflow-install-report.json -r /opt/app2/workflow-requirements.txt \
    && python -m pip check \
    && python -m pip freeze --all > /opt/app2/workflow-environment.freeze.txt \
    && python3 -m venv /opt/app2/cvat-sdk-venv \
    && /opt/app2/cvat-sdk-venv/bin/python -m pip install --report /opt/app2/cvat-sdk-install-report.json cvat-sdk==2.79.0 \
    && /opt/app2/cvat-sdk-venv/bin/python -m pip check \
    && /opt/app2/cvat-sdk-venv/bin/python -m pip freeze --all > /opt/app2/cvat-sdk-environment.freeze.txt
COPY --chown=10001:10001 . /opt/app2/workflow/
ENV PYTHONPATH=/opt/app2/workflow:/opt/app2/training:/opt/app2/cvat
WORKDIR /opt/app2/workflow
USER 10001:10001
CMD ["python", "demo.py", "--help"]
