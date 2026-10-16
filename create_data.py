import numpy as np
import xarray as xr
import dask
import pandas as pd

time = np.arange(100)
lat = np.arange(50)
lon = np.arange(50)

temperature = np.random.rand(100, 50, 50) * 30

ds = xr.Dataset(
    {
        "temperature": (
            ["time", "lat", "lon"],
            temperature,
        )
    },
    coords={
        "time": time,
        "lat": lat,
        "lon": lon,
    },
)

print(ds)

ds.to_zarr("input.zarr", mode="w")
