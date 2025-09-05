#!/usr/bin/env bash
set -euo pipefail

# Initialize a flag to track if any files were modified
modified=0

# Process each file passed to the script
for file in "$@"; do
    if [[ -f "$file" ]]; then
        # Create a temporary file
        temp_file=$(mktemp)

        # Format the file and redirect to temp file
        if ! shfmt -i 4 -bn -ci -sr "$file" > "$temp_file"; then
            echo "Error: shfmt failed on $file"
            rm "$temp_file"
            exit 1
        fi

        # Compare original and formatted files
        if ! cmp -s "$file" "$temp_file"; then
            # Files are different, replace original with formatted version
            mv "$temp_file" "$file"
            echo "Formatted $file"
            modified=1
        else
            rm "$temp_file"
        fi
    fi
done

# Exit with status 1 if any files were modified
# This ensures pre-commit knows changes were made
if [ "$modified" -eq 1 ]; then
    exit 1
fi

exit 0
