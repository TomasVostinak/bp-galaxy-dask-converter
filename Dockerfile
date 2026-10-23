FROM quay.io/bgruening/galaxy:latest

RUN printf '#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n' > /usr/local/bin/check_database.py && \
    chmod +x /usr/local/bin/check_database.py && \
    printf '#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n' > /usr/local/bin/create_galaxy_user.py && \
    chmod +x /usr/local/bin/create_galaxy_user.py

# doinstalování Python knihoven
RUN /galaxy_venv/bin/pip install --no-cache-dir \
    xarray \
    zarr \
    s3fs \
    dask \
    distributed

# nakopírování toolů do Galaxy
RUN mkdir -p /galaxy/tools/mytools
COPY mytools/ /galaxy/tools/mytools/

# zaregistrování do konfigurace
COPY local_tool_conf.xml /export/galaxy/config/tool_conf.xml.local
ENV GALAXY_CONFIG_TOOL_CONFIG_FILE=/export/galaxy/config/tool_conf.xml.sample,/export/galaxy/config/tool_conf.xml.local
