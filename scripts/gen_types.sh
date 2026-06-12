#!/bin/bash

# Exit on error
set -e

SCHEMA_PATH="schemas/chart.json"
OUTPUT_DIR="frontend/src/types"
OUTPUT_FILE="$OUTPUT_DIR/chart.ts"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

echo "Generating types from $SCHEMA_PATH to $OUTPUT_FILE..."
# Use npx to run json-schema-to-typescript
npx -y json-schema-to-typescript@13.1.2 "$SCHEMA_PATH" > "${OUTPUT_FILE}.tmp"

# Prepend the required header
cat << 'EOF' > "$OUTPUT_FILE"
/**
 * DO NOT EDIT — GENERATED
 * Generated from schemas/chart.json
 */

EOF

cat "${OUTPUT_FILE}.tmp" >> "$OUTPUT_FILE"
rm "${OUTPUT_FILE}.tmp"

echo "Type generation complete."
