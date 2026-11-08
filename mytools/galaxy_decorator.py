import s3fs
import argparse
import xarray as xr
import json
import inspect
import functools
import os

def get_s3_store(endpoint, public, secret):
    fs = s3fs.S3FileSystem(key=public, secret=secret, client_kwargs={"endpoint_url": endpoint})
    return fs

def galaxy_s3_tool(func):
    @functools.wrap(func)
    def wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        custom_params = params[:1]

        parser = argparse.ArgumentParser(description=f"Galaxy wrapper for {func.__name__}")
        parser.add_argument("--endpoint", required=True, help="S3 Endpoint URL")
        parser.add_argument("--public-key", required=True, help="S3 Public Key")
        parser.add_argument("--private-key", required=True, help="S3 Private Key")
        parser.add_argument("--input-json", required=True, help="Input JSON with Zarr dataset")
        parser.add_argument("--output-json", required=True, help="Output JSON with Zarr dataset")

        for param in custom_params:
            arg_name = f"--{param.name.replace("_", "-")}"
            arg_type = param.annotation if param.annotation != inspect.Parameter.empty else str

            if param.default != inspect.Parameter.empty:
                parser.add_argument(arg_name, type=arg_type, default=param.default, help=f"Default: {param.default}")
            else:
                parser.add_argument(arg_name, type=arg_type, required=True)

        parsed_args = parser.parse_args()

        with open(parsed_args.input_json, "r") as file:
            json_data = json.load(file)

        fs = get_s3_store(parsed_args.endpoint, parsed_args.public_key, parsed_args.private_key)
        zarr_store = s3fs.S3Map(root=json_data["s3_path"], s3=fs, check=False)
        ds = xr.open_zarr(zarr_store, consolidated=True)

        func_kwargs = {}
        for param in custom_params:
            func_kwargs[param.name] = getattr(parsed_args, param.name)

        print(f"Running function '{func.__name__}' with parameters: {func_kwargs}")
        ds_result = func(ds, **func_kwargs)

        base_name, ext = os.path.splitext(json_data["s3_path"])
        output_s3_path = f"{base_name}_{func.__name__}{ext}"
        output_store = s3fs.S3Map(root=output_s3_path, s3=fs, check=False)

        ds_result.to_zarr(output_store, mode="w", consolidated=True)

        step_record = f"{func.__name__}({', '.join(f'{k}={v}' for k, v in func_kwargs.items())})"
        output_data = {
            "s3_endpoint": parsed_args.endpoint,
            "s3_path": output_s3_path,
            "history": json_data.get("history", []) + [step_record]
        }

        with open(parsed_args.output_json, 'w') as f:
            json.dump(output_data, f, indent=4)

        print(f"Transformed dataset saved to {output_s3_path}.")

        return ds_result
    
    return wrapper
