import argparse
import json
import s3fs
import xarray as xr

import operations

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", help="Název funkce z operations.py (např. multiply)")
    parser.add_argument("--input-json", required=True, help="Vstupní manifest s S3 údaji")
    parser.add_argument("--output-json", required=True, help="Kam zapsat výstupní manifest")
    args, unknown = parser.parse_known_args()

    kwargs = {}
    for i in range(0, len(unknown), 2):
        key = unknown[i].lstrip("-")
        val = unknown[i + 1]
        try:
            val = float(val) if "." in val else int(val)
        except ValueError:
            pass
        kwargs[key] = val

    with open(args.input_json, "r") as f:
        manifest = json.load(f)

    s3_conf = manifest["s3"]
    fs = s3fs.S3FileSystem(
        key=s3_conf["access_key"],
        secret=s3_conf["secret_key"],
        client_kwargs={"endpoint_url": s3_conf["endpoint_url"]}
    )

    in_store = s3fs.S3Map(root=manifest["s3_path"], s3=fs, check=False)
    ds = xr.open_zarr(in_store, consolidated=True)

    func = getattr(operations, args.operation)
    print(f"Spouštím operaci '{args.operation}' s parametry: {kwargs}")
    out_ds = func(ds, **kwargs)

    new_path = manifest["s3_path"].replace(".zarr", f"_{args.operation}.zarr")
    out_store = s3fs.S3Map(root=new_path, s3=fs, check=False)
    out_ds.to_zarr(out_store, mode="w", consolidated=True)

    with open(args.output_json, "w") as f:
        json.dump({"s3": s3_conf, "s3_path": new_path}, f, indent=4)

    print(f"Výsledek uložen na S3: {new_path}")

if __name__ == "__main__":
    main()
