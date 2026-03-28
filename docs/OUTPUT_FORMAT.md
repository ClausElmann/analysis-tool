# Output Format

## Detailed per-file markdown

Each analyzed file produces one markdown document under `output-data/files/`. The document contains metadata, summary, key elements, domain signals, dependencies, inputs and outputs, risks, and a raw text extract.

## Aggregated JSON

`output-data/analysis-index.json` contains the complete normalized result set. This is the best machine-readable input for later LLM or script-based processing.

## Meaning of the main sections

- `key_elements`: structural findings such as classes, methods, routes, tables, or job names.
- `domain_signals`: repeated domain hints such as keywords, forms, column names, or role labels.
- `dependencies`: namespaces, URLs, object references, or other outward connections.
- `inputs_outputs`: likely API operations or externally visible interaction patterns.

## How an LLM can consume the data

A later analysis agent can read the JSON first, group findings by project, then correlate backend signals, SQL signals, and frontend signals into business capabilities.

## Example interpretation

If the output contains:
- Angular route `orders`
- C# endpoint attributes in an `OrdersController`
- SQL table `Orders`

then the combined signals strongly suggest an order-management capability.
