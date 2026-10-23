FROM quay.io/bgruening/galaxy:latest

RUN sed -i 's/listen 80;/listen 8080;/g' /etc/nginx/sites-available/galaxy && \
    sed -i 's/listen \[::\]:80;/listen [::]:8080;/g' /etc/nginx/sites-available/galaxy && \
    sed -i 's/listen 80 default_server;/listen 8080 default_server;/g' /etc/nginx/sites-available/galaxy

RUN chown -R 1450:1450 /var/log/nginx /var/lib/nginx /run /tmp /var/log/supervisor

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

USER 1450
