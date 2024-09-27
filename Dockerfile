FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy the project into the image
ADD . /app

# Sync the project into a new environment, using the frozen lockfile
WORKDIR /app
RUN uv sync --frozen
RUN --mount=type=secret,id=DUNE_API_KEY echo "$DUNE_API_KEY" > .env
RUN cat .env
SHELL ["/bin/bash", "-c"]
RUN source .env
# ENV DUNE_API_KEY=$DUNE_API_KEY
# RUN --mount=type=secret,id=dune-api-key echo "$DUNE_API_KEY"
CMD ["uv", "run", "flask", "run", "--host", "0.0.0.0", "--port", "8000"]