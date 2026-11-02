# Low-Stock Report — `products.py low`

Custom feature of the `products.py` inventory CLI: a **low-stock report** that
finds every product whose quantity has fallen to or below a threshold you
choose.

## Who it helps

Anyone who runs a small inventory and needs to know **what to reorder**:

- A shop owner checking each morning which items are running out
- A stockroom clerk preparing a restock list before the weekend
- A team lead watching consumables (office supplies, lab stock, parts bins)
  without a full inventory system

Instead of scrolling through the whole product list, one command returns only
the items at or below the level where you need to act.

## Command syntax

```
py products.py [--file PATH] low --threshold N
```

| Piece         | Required? | Meaning                                                            |
| ------------- | --------- | ------------------------------------------------------------------ |
| `--file PATH` | no        | JSON data file to use (default: `products.json` next to the script) |
| `low`         | yes       | The low-stock report subcommand                                    |
| `--threshold N` | yes     | Non-negative integer; report every product with `quantity <= N`    |

## Inputs

- `--threshold` must be a **non-negative integer** (`0`, `5`, `10`, ...).
  Anything else — negative numbers, decimals (`2.5`), or non-numeric text —
  is rejected with exit code `2` before the data file is even read.
- The data file is only **read**, never created or modified, by this command.
  A missing data file is treated as an empty store.

## Expected output

- **Success (exit `0`):** a JSON array on standard output of all matching
  products, sorted by numeric ID ascending. Each product is an object with
  `id` (integer), `name` (string), `price` (number), and `quantity` (integer).
  If no product qualifies, the output is `[]` — still exit `0`.
- **Invalid threshold (exit `2`):** a concise `{"error": "..."}` on standard
  error and nothing on standard output.
- **Data file problems (exit `1`):** the same error style if the file is
  empty, malformed, or fails schema validation. The file is left unchanged.

## Runnable example

Build a small store, then ask for everything with 5 or fewer units in stock:

```console
> py products.py --file shop.json add --name Notebook --price 4.50 --quantity 12
> py products.py --file shop.json add --name Pen --price 1.25 --quantity 3
> py products.py --file shop.json add --name Stapler --price 12.00 --quantity 40
> py products.py --file shop.json add --name Eraser --price 0.99 --quantity 5

> py products.py --file shop.json low --threshold 5
[
  {
    "id": 2,
    "name": "Pen",
    "price": 1.25,
    "quantity": 3
  },
  {
    "id": 4,
    "name": "Eraser",
    "price": 0.99,
    "quantity": 5
  }
]
```

Note that **Eraser (exactly 5)** is included — the threshold means *at or
below* — while Notebook (12) and Stapler (40) are not.

Tightening the threshold to `0` reports only fully out-of-stock items:

```console
> py products.py --file shop.json low --threshold 0
[]
```

and an invalid threshold fails cleanly without touching the data file:

```console
> py products.py --file shop.json low --threshold 2.5
{"error": "quantity must be a non-negative integer"}   (exit code 2)
```
