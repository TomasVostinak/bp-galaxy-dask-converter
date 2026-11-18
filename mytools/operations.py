from typing import List
import xarray as xr
from meta import galaxy_op

@galaxy_op(description="Multiplies the dataset by a given factor")
def multiply(ds: xr.Dataset, factor: float = 2.0) -> xr.Dataset:
    return ds * factor

@galaxy_op(description="Computes the difference between two datasets")
def subtract(ds1: xr.Dataset, ds2: xr.Dataset) -> xr.Dataset:
    return ds1 - ds2

@galaxy_op(description="Concatenates multiple datasets into one")
def concatenate(datasets: List[xr.Dataset], dim: str = "time") -> xr.Dataset:
    return xr.concat(datasets, dim=dim)
