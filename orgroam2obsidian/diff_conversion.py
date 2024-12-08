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
    This should match the sanitization logic used in the conversion scripts.

    The characters traded include:
    ['] -> [-]
    [<>,:"/\\|?*] -> [-]
    Control characters -> [-]

    explanation of regex:
    [\'<>:"/\\|?*\x00-\x1F] -> matches any of the characters in the square
    brackets -- regular expression breakdown:
    \' -> matches single quote
    <> -> matches angle brackets
    : -> matches colon
    " -> matches double quote
    / -> matches forward slash
    \\ -> matches backslash
    | -> matches pipe
    ? -> matches question mark
    * -> matches asterisk
    \x00-\x1F -> matches control characters (ASCII 0-31)
    """
    return re.sub(r'[\'<>:"/\\|?*\x00-\x1F]', '-', filename)

def map_org_to_md(org_filename, md_folder):
    """
    Given an .org filename and the md_folder, attempt to guess the corresponding .md file.
    This might need customization based on how the script maps .org titles to .md filenames.
    For now, we assume the .org filename (without extension) maps directly to a sanitized .md filename.

    E.g.: "Note One.org" -> "Note One.md" or sanitized filename.
    """
    base_name = os.path.splitext(os.path.basename(org_filename))[0]
    candidate_name = sanitize_filename(base_name) + ".md"
    possible_path = os.path.join(md_folder, candidate_name)
    if os.path.exists(possible_path):
        return possible_path
    else:
        # If direct mapping fails, you may need to add extra logic here.
        return None

def file_diff(org_file, md_file):
    """
    Compute a unified diff between the content of an .org file and its .md counterpart.
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
    Recursively print differences between directories.
    This shows files only in left (original) or only in right (converted), and those that differ.
    """
    # relative_path helps keep track of where we are in recursion
    prefix = relative_path + '/' if relative_path else ''
    
    if dcmp.left_only:
        print(f"Only in original attachments ({prefix}): {dcmp.left_only}")
    if dcmp.right_only:
        print(f"Only in new attachments ({prefix}): {dcmp.right_only}")
    if dcmp.diff_files:
        print(f"Files differ in attachments ({prefix}): {dcmp.diff_files}")

    for sub_dcmp in dcmp.subdirs.values():
        sub_path = prefix + os.path.basename(sub_dcmp.left)
        print_dir_diff(sub_dcmp, relative_path=sub_path)

def compare_attachments(org_attachments_folder, md_attachments_folder):
    """
    Compare the directory structures of the original and new attachments folder trees.
    """
    if not (os.path.exists(org_attachments_folder) and os.path.exists(md_attachments_folder)):
        print("Warning: One or both attachments directories do not exist.")
        return
    dcmp = dircmp(org_attachments_folder, md_attachments_folder)
    print_dir_diff(dcmp)

def main():
    parser = argparse.ArgumentParser(description="Diff the results of Org-roam to Obsidian conversion.")
    parser.add_argument("--org-folder", required=True, help="Path to the folder containing the original Org-roam .org files")
    parser.add_argument("--md-folder", required=True, help="Path to the folder containing the converted Obsidian .md files")
    parser.add_argument("--org-attachments-folder", required=True, help="Path to the original Org-roam attachments folder")
    parser.add_argument("--md-attachments-folder", required=True, help="Path to the converted attachments folder in Obsidian")

    args = parser.parse_args()

    org_folder = args.org_folder
    md_folder = args.md_folder
    org_attachments_folder = args.org_attachments_folder
    md_attachments_folder = args.md_attachments_folder

    # Compare the converted note files
    print("### Comparing Org to Markdown Files ###")
    for filename in os.listdir(org_folder):
        if filename.endswith(".org"):
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

    # Compare the attachments directories
    print("\n### Comparing Attachments Directories ###")
    compare_attachments(org_attachments_folder, md_attachments_folder)

if __name__ == "__main__":
    main()
