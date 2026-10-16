import s3fs
import argparse
import xarray as xr
import json

def get_s3_store(endpoint, public, secret):
    fs = s3fs.S3FileSystem(key=public, secret=secret, client_kwargs={"endpoint_url": endpoint})
    return fs

def main():
    parser = argparse.ArgumentParser(description="Galaxy S3 Transformation Tool")
    parser.add_argument("--endpoint", required=True, help="S3 Endpoint URL")
    parser.add_argument("--public-key", required=True, help="S3 Public Key")
    parser.add_argument("--private-key", required=True, help="S3 Private Key")
    parser.add_argument("--input-json", required=True, help="Path to input Zarr dataset")
    parser.add_argument("--factor", type=float, default=2.0, help="Factor to multiply the dataset by")
    parser.add_argument("--output-json", required=True, help="S3 path to output Zarr dataset")
    args = parser.parse_args()

    with open(args.input_json, 'r') as file:
        json_data = json.load(file)

    fs = get_s3_store(args.endpoint, args.public_key, args.private_key)
    zarr_store = s3fs.S3Map(root=json_data["s3_path"], s3=fs, check=False)

    ds = xr.open_zarr(zarr_store, consolidated=True)
    ds_transformed = ds * args.factor
    output_path = json_data["s3_path"].replace(".zarr", f"_transformed_{args.factor}.zarr")
    output_store = s3fs.S3Map(root=output_path, s3=fs, check=False)

    ds_transformed.to_zarr(output_store, mode="w", consolidated=True)

    output_data = {
        "s3_endpoint": args.endpoint,
        "s3_path": output_path,
        "history": json_data.get("history", []) + [f"Multiplied by {args.factor}"]
    }

    with open(args.output_json, 'w') as f:
        json.dump(output_data, f, indent=4)

    print(f"Transformed dataset saved to {output_path} and metadata saved to {args.output_json}")

if __name__ == "__main__":
    main()
