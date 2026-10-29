import xarray as xr
import sys
from galaxy_decorator import galaxy_s3_tool

OPERATIONS = {}

def register_operation(func):
    OPERATIONS[func.__name__] = galaxy_s3_tool(func)
    return func

@galaxy_s3_tool
def multiply(ds: xr.Dataset, factor: float = 2.0) -> xr.Dataset:
    return ds * factor

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in OPERATIONS:
        print(f"Použití: python operations.py <nazev_operace> [argumenty]")
        print(f"Dostupné operace: {list(OPERATIONS.keys())}")
        sys.exit(1)

    operation_name = sys.argv.pop(1)
    OPERATIONS[operation_name]()
