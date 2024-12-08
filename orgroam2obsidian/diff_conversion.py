#!/usr/bin/env python3
import argparse
import os
import re
import difflib
import filecmp
from filecmp import dircmp

def sanitize_filename(filename):
    """
    Sanitize filenames to remove or replace characters that are invalid in file paths.
    Matches the logic used in the conversion scripts.
    """
    return re.sub(r'[\'<>:"/\\|?*\x00-\x1F]', '-', filename)

def map_org_to_md(org_filename, md_folder):
    """
    Given an .org filename and the md_folder, attempts to guess the corresponding .md file.
    Adjust if your mapping logic differs.
    """
    base_name = os.path.splitext(os.path.basename(org_filename))[0]
    candidate_name = sanitize_filename(base_name) + ".md"
    possible_path = os.path.join(md_folder, candidate_name)
    if os.path.exists(possible_path):
        return possible_path
    else:
        return None

def file_diff(org_file, md_file):
    """
    Compute a unified diff between .org and .md file contents.
    Return the diff as a list of lines.
    """
    with open(org_file, 'r') as f_org:
        org_lines = f_org.readlines()

    with open(md_file, 'r') as f_md:
        md_lines = f_md.readlines()

    diff = list(difflib.unified_diff(
        org_lines, md_lines,
        fromfile=org_file,
        tofile=md_file,
        lineterm=''
    ))
    return diff

def print_dir_diff(dcmp, relative_path=''):
    """
    Recursively print directory differences:
    - Files only in left or right side.
    - Files that differ between sides.
    """
    prefix = relative_path + '/' if relative_path else ''
    
    if dcmp.left_only:
        print(f"Only in original attachments ({prefix}): {dcmp.left_only}")
    if dcmp.right_only:
        print(f"Only in new attachments ({prefix}): {dcmp.right_only}")
    if dcmp.diff_files:
        print(f"Files differ in attachments ({prefix}): {dcmp.diff_files}")

    for sub_name, sub_dcmp in dcmp.subdirs.items():
        sub_path = prefix + sub_name
        print_dir_diff(sub_dcmp, relative_path=sub_path)

def compare_attachments(org_attachments_folder, md_attachments_folder):
    """
    Compare attachments directory structures and print differences.
    """
    if not os.path.exists(org_attachments_folder):
        print(f"Warning: Original attachments directory does not exist: {org_attachments_folder}")
        return
    if not os.path.exists(md_attachments_folder):
        print(f"Warning: New attachments directory does not exist: {md_attachments_folder}")
        return

    dcmp = dircmp(org_attachments_folder, md_attachments_folder)
    print_dir_diff(dcmp)

def main():
    parser = argparse.ArgumentParser(description="Diff the results of Org-roam to Obsidian conversion.")
    parser.add_argument("--org-folder", required=True, help="Path to folder containing the original Org-roam .org files")
    parser.add_argument("--md-folder", required=True, help="Path to folder containing the converted Obsidian .md files")
    parser.add_argument("--org-attachments-folder", default=None, help="Path to original Org-roam attachments folder (default: <org-folder>/attachments)")
    parser.add_argument("--md-attachments-folder", default=None, help="Path to converted attachments folder (default: <md-folder>/attachments)")

    args = parser.parse_args()

    org_folder = os.path.abspath(args.org_folder)
    md_folder = os.path.abspath(args.md_folder)

    # Guess defaults if not provided
    org_attachments_folder = args.org_attachments_folder if args.org_attachments_folder else os.path.join(org_folder, 'attachments')
    md_attachments_folder = args.md_attachments_folder if args.md_attachments_folder else os.path.join(md_folder, 'attachments')

    print("### Configuration ###")
    print(f"Org folder: {org_folder}")
    print(f"MD folder: {md_folder}")
    print(f"Org attachments folder: {org_attachments_folder}")
    print(f"MD attachments folder: {md_attachments_folder}")
    print("#####################\n")

    # Compare note files
    print("### Comparing Org to Markdown Files ###")
    if not os.path.exists(org_folder):
        print(f"Org folder does not exist: {org_folder}")
    if not os.path.exists(md_folder):
        print(f"MD folder does not exist: {md_folder}")

    if os.path.exists(org_folder) and os.path.exists(md_folder):
        org_files = [f for f in os.listdir(org_folder) if f.endswith(".org")]
        for filename in org_files:
            org_path = os.path.join(org_folder, filename)
            md_path = map_org_to_md(org_path, md_folder)
            if md_path and os.path.exists(md_path):
                diff = file_diff(org_path, md_path)
                if diff:
                    print(f"\nDifferences found for {filename} -> {os.path.basename(md_path)}:")
                    for line in diff:
                        print(line)
                else:
                    print(f"No differences found for {filename}.")
            else:
                print(f"No corresponding .md file found for {filename}")

    # Compare attachments directories
    print("\n### Comparing Attachments Directories ###")
    compare_attachments(org_attachments_folder, md_attachments_folder)

if __name__ == "__main__":
    main()
