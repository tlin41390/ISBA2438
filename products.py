#!/usr/bin/env python3
"""Inventory CLI for managing products stored in a JSON file."""

import argparse
import json
import math
import os
import sys
import tempfile
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "products.json"
REQUIRED_KEYS = {"id", "name", "price", "quantity"}


def fail(message, code=1):
    print(json.dumps({"error": message}), file=sys.stderr)
    sys.exit(code)


def is_number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float))


def check_schema(data):
    if not isinstance(data, list):
        fail("data file does not match the required schema")
    seen_ids = set()
    for item in data:
        if not isinstance(item, dict) or not REQUIRED_KEYS.issubset(item):
            fail("data file does not match the required schema")
        pid = item["id"]
        if isinstance(pid, bool) or not isinstance(pid, int) or pid < 1:
            fail("data file does not match the required schema")
        if not isinstance(item["name"], str) or not item["name"].strip():
            fail("data file does not match the required schema")
        price = item["price"]
        if not is_number(price) or not math.isfinite(price) or price < 0:
            fail("data file does not match the required schema")
        quantity = item["quantity"]
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
            fail("data file does not match the required schema")
        if pid in seen_ids:
            fail("data file does not match the required schema")
        seen_ids.add(pid)


def normalize_store(data):
    if isinstance(data, list):
        check_schema(data)
        next_id = max((p["id"] for p in data), default=0) + 1
        return {"next_id": next_id, "products": data}
    if (
        isinstance(data, dict)
        and "next_id" in data
        and "products" in data
        and not isinstance(data["next_id"], bool)
        and isinstance(data["next_id"], int)
        and data["next_id"] >= 1
    ):
        check_schema(data["products"])
        return {"next_id": data["next_id"], "products": data["products"]}
    fail("data file does not match the required schema")


def load_store(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return {"next_id": 1, "products": []}
    except (OSError, ValueError) as exc:
        fail(f"cannot read data file: {exc}")
    if not content.strip():
        fail("data file is empty")
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        fail("data file contains malformed JSON")
    return normalize_store(data)


def save_store(path, store):
    payload = json.dumps(
        {"next_id": store["next_id"], "products": store["products"]}, indent=2
    ) + "\n"
    directory = os.path.dirname(os.path.abspath(path))
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=directory, delete=False
        ) as tmp:
            tmp_name = tmp.name
            tmp.write(payload)
        os.replace(tmp_name, path)
    except (OSError, ValueError) as exc:
        if tmp_name is not None:
            try:
                os.remove(tmp_name)
            except OSError:
                pass
        fail(f"cannot write data file: {exc}")


def validate_name(value):
    name = value.strip()
    if not name:
        fail("name must be a non-empty string", 2)
    return name


def validate_price(value):
    try:
        price = float(value)
    except ValueError:
        fail("price must be a number", 2)
    if not math.isfinite(price) or price < 0:
        fail("price must be a non-negative number", 2)
    return round(price, 2)


def validate_quantity(value):
    try:
        quantity = int(value)
    except ValueError:
        fail("quantity must be an integer", 2)
    if quantity < 0:
        fail("quantity must be a non-negative integer", 2)
    return quantity


def find_product(products, product_id):
    for product in products:
        if product["id"] == product_id:
            return product
    return None


def cmd_add(args):
    name = validate_name(args.name)
    price = validate_price(args.price)
    quantity = validate_quantity(args.quantity)

    store = load_store(args.file)
    products = store["products"]
    next_id = max([store["next_id"]] + [p["id"] + 1 for p in products])
    product = {"id": next_id, "name": name, "price": price, "quantity": quantity}
    products.append(product)
    store["next_id"] = next_id + 1
    save_store(args.file, store)
    print(json.dumps(product, indent=2))


def cmd_list(args):
    products = sorted(load_store(args.file)["products"], key=lambda p: p["id"])
    print(json.dumps(products, indent=2))


def cmd_low(args):
    threshold = validate_quantity(args.threshold)
    products = sorted(load_store(args.file)["products"], key=lambda p: p["id"])
    low_stock = [p for p in products if p["quantity"] <= threshold]
    print(json.dumps(low_stock, indent=2))


def cmd_get(args):
    product = find_product(load_store(args.file)["products"], args.id)
    if product is None:
        fail(f"Product with ID {args.id} does not exist")
    print(json.dumps(product, indent=2))


def cmd_update(args):
    if args.name is None and args.price is None and args.quantity is None:
        fail("at least one of --name, --price, --quantity is required", 2)

    name = validate_name(args.name) if args.name is not None else None
    price = validate_price(args.price) if args.price is not None else None
    quantity = validate_quantity(args.quantity) if args.quantity is not None else None

    store = load_store(args.file)
    product = find_product(store["products"], args.id)
    if product is None:
        fail(f"Product with ID {args.id} does not exist")

    if name is not None:
        product["name"] = name
    if price is not None:
        product["price"] = price
    if quantity is not None:
        product["quantity"] = quantity

    save_store(args.file, store)
    print(json.dumps(product, indent=2))


def cmd_delete(args):
    if not args.yes:
        fail("--yes is required to confirm deletion", 2)

    store = load_store(args.file)
    product = find_product(store["products"], args.id)
    if product is None:
        fail(f"Product with ID {args.id} does not exist")

    store["products"].remove(product)
    save_store(args.file, store)
    print(json.dumps({"deleted_id": args.id}))


def build_parser():
    parser = argparse.ArgumentParser(prog="products", description="Inventory CLI")
    parser.add_argument(
        "--file",
        default=str(DATA_FILE),
        help="path to the JSON data file (default: products.json next to this script)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Create a product")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--price", required=True)
    p_add.add_argument("--quantity", required=True)
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List all products")
    p_list.set_defaults(func=cmd_list)

    p_low = sub.add_parser(
        "low", help="List products with quantity at or below a threshold"
    )
    p_low.add_argument("--threshold", required=True)
    p_low.set_defaults(func=cmd_low)

    p_get = sub.add_parser("get", help="Get a product by ID")
    p_get.add_argument("id", type=int)
    p_get.set_defaults(func=cmd_get)

    p_update = sub.add_parser("update", help="Update a product by ID")
    p_update.add_argument("id", type=int)
    p_update.add_argument("--name")
    p_update.add_argument("--price")
    p_update.add_argument("--quantity")
    p_update.set_defaults(func=cmd_update)

    p_delete = sub.add_parser("delete", help="Delete a product by ID")
    p_delete.add_argument("id", type=int)
    p_delete.add_argument("--yes", action="store_true")
    p_delete.set_defaults(func=cmd_delete)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as exc:
        fail(f"command failed: {exc}")


if __name__ == "__main__":
    main()
