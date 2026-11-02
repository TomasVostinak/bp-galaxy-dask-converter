FROM quay.io/galaxyproject/galaxy-min:26.1.1

USER root

# doinstalování Python knihoven
RUN /galaxy/server/.venv/bin/pip install --no-cache-dir \
    xarray zarr s3fs dask distributed

COPY mytools/ /galaxy/tools/mytools/
COPY local_tool_conf.xml /export/galaxy/config/local_tool_conf.xml

RUN chown -R 10001:10001 /galaxy/tools/mytools /export/galaxy/config/local_tool_conf.xml || true
USER 10001
