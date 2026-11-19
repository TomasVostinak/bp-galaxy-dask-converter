import argparse
import inspect
import json
import s3fs
import xarray as xr

import operations

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", help="Function name from operations.py")
    parser.add_argument("--output-json", required=True, help="Where to write the output manifest JSON file")
    args, unknown = parser.parse_known_args()

    cli_kwargs = {}
    for i in range(0, len(unknown), 2):
        key = unknown[i].lstrip("-")
        val = unknown[i + 1]
        cli_kwargs[key] = val

    func = getattr(operations, args.operation)
    sig = inspect.signature(func)

    s3_conf = None
    last_s3_path = None
    call_kwargs = {}

    for param_name, param in sig.parameters.items():
        if param_name not in cli_kwargs:
            if param.default is not inspect.Parameter.empty:
                call_kwargs[param_name] = param.default
                continue
            else:
                raise ValueError(f"Missing required argument: --{param_name}")

        raw_val = cli_kwargs[param_name]

        if param.annotation == xr.Dataset or param_name in ["ds", "ds1", "ds2"]:
            with open(raw_val, "r") as f:
                manifest = json.load(f)

            s3_conf = manifest["s3"]
            last_s3_path = manifest["s3_path"]

            fs = s3fs.S3FileSystem(
                key=s3_conf["access_key"],
                secret=s3_conf["secret_key"],
                client_kwargs={"endpoint_url": s3_conf["endpoint_url"]},
            )

            in_store = s3fs.S3Map(root=last_s3_path, s3=fs, check=False)
            call_kwargs[param_name] = xr.open_zarr(in_store, consolidated=True)
        else:
            try:
                if "." in raw_val:
                    call_kwargs[param_name] = float(raw_val)
                else:
                    call_kwargs[param_name] = int(raw_val)
            except ValueError:
                if raw_val.lower() == "true":
                    call_kwargs[param_name] = True
                elif raw_val.lower() == "false":
                    call_kwargs[param_name] = False
                else:
                    call_kwargs[param_name] = raw_val

    print(f"Running operation '{args.operation}'...")
    out_ds = func(**call_kwargs)

    if not s3_conf or not last_s3_path:
        raise RuntimeError("No S3 configuration found in the input data.")

    new_path = last_s3_path.replace(".zarr", f"_{args.operation}.zarr")
    fs = s3fs.S3FileSystem(
        key=s3_conf["access_key"],
        secret=s3_conf["secret_key"],
        client_kwargs={"endpoint_url": s3_conf["endpoint_url"]},
    )
    
    out_store = s3fs.S3Map(root=new_path, s3=fs, check=False)
    out_ds.to_zarr(out_store, mode="w", consolidated=True)

    with open(args.output_json, "w") as f:
        json.dump({"s3": s3_conf, "s3_path": new_path}, f, indent=4)

    print(f"Output saved to S3: {new_path}")

if __name__ == "__main__":
    main()
