# Base image pinned by digest (multi-arch index of python:3.13-slim, 2026-10-28): a re-pushed tag
# can't change what gets built. Dependabot (docker ecosystem) proposes digest updates weekly.
# Both stages must use the same base so the venv's Python matches at runtime.

# ---- build stage: install deps into an isolated venv ----
FROM python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb AS build
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip uninstall -y pip

# ---- runtime stage: minimal image, non-root user ----
FROM python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb
ARG APP_VERSION=dev
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=${APP_VERSION}
# pip is not needed at runtime; removing it drops its vendored libs (urllib3, msgpack, ...) from the attack surface.
# ensurepip (which bundles a pip wheel) is located by asking Python, so this keeps working when the
# base image moves to a new Python minor version.
RUN ensurepip_dir="$(python -c 'import ensurepip, os; print(os.path.dirname(ensurepip.__file__))')" \
 && python -m pip uninstall -y pip \
 && rm -rf "$ensurepip_dir" \
 && useradd --uid 10001 --no-create-home appuser
WORKDIR /srv
COPY --from=build /opt/venv /opt/venv
COPY app ./app
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
