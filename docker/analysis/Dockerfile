FROM rocker/r-ver:4.1.2

ENV R_ANALYSIS_LIBRARY=/opt/renv/library \
    R_LIBS=/opt/renv/library \
    RENV_PATHS_CACHE=/opt/renv/cache

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        curl \
        pandoc \
        libcurl4-openssl-dev \
        libfontconfig1-dev \
        libfreetype6-dev \
        libfribidi-dev \
        libharfbuzz-dev \
        libicu-dev \
        libjpeg-dev \
        libpng-dev \
        libssl-dev \
        libtiff5-dev \
        libuv1-dev \
        libxml2-dev

WORKDIR /workspace
COPY renv.lock /workspace/renv.lock
COPY scripts/analysis/restore_renv.R /workspace/scripts/analysis/restore_renv.R
RUN Rscript /workspace/scripts/analysis/restore_renv.R
