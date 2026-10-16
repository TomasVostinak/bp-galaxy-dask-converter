import xarray as xr
import dask
import pandas as pd
import numpy as np

ds = xr.open_zarr("input.zarr", chunks={"time": 100})

temp = ds["temperature"]

print("Original Data:")
print(temp.compute())

tr_ds = xr.open_zarr("input_transformed_2.0.zarr", chunks={"time": 100})

temp_tr = tr_ds["temperature"]

print("Transformed Data:")
print(temp_tr.compute())