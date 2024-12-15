#!/bin/bash

# test_pandoc_behavior.sh
# A script to test how Pandoc handles Org-mode files with various link types.

# Create a temporary directory for the test
TEST_DIR=$(mktemp -d)
echo "Using temporary directory: $TEST_DIR"

# Define the test Org file
ORG_FILE="$TEST_DIR/test.org"
MD_OUTPUT="$TEST_DIR/output.md"

# Create the Org file with various link types
cat <<EOL > "$ORG_FILE"
#+title: Pandoc Link Handling Test
#+author: Test User

This is a test note.

Link to another note using id: [[id:12345][Note with ID]].

Attachment link: [[attachment:attachment1.png]].

File link: [[file:./attachments/attachment2.jpg]].

Regular URL: [[https://example.com][Example Site]].

* Note with ID
:PROPERTIES:
:ID:      12345
:END:

This is the target note with ID 12345.
EOL

# Create fake attachments
mkdir -p "$TEST_DIR/attachments"
touch "$TEST_DIR/attachments/attachment1.png"
touch "$TEST_DIR/attachments/attachment2.jpg"

# Function to run Pandoc with given options and show output
run_pandoc_test() {
    local OPTIONS="$1"
    local OUTPUT_FILE="$2"

	echo "Input Org file:"
	cat "$ORG_FILE"

    echo "Running Pandoc with options
run_pandoc_test "-f org -t markdown" "$MD_OUTPUT"

# Test 2: With reference links
run_pandoc_test "-f org -t markdown --reference-links" "$MD_OUTPUT"

# Test 3: With raw HTML enabled
run_pandoc_test "-f org -t markdown -f org+raw_html" "$MD_OUTPUT"

# Test 4: With Pandoc Lua filter (if you have any)
# Uncomment and modify if you have a Lua filter to test
# run_pandoc_test "-f org -t markdown --lua-filter=your_filter.lua" "$MD_OUTPUT"

# Clean up temporary directory (comment out if you want to inspect files)
rm -rf "$TEST_DIR"
echo "Temporary directory removed."
