#!/usr/bin/env python3
import argparse
import os
import re
import difflib
import filecmp
from filecmp import dircmp
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from difflib import SequenceMatcher

console = Console()

def sanitize_filename(filename):
    """
    Sanitize filenames to remove or replace characters that are invalid in file paths.
    """
    return re.sub(r'[\'<>:"/\\|?*\x00-\x1F]', '-', filename)

def map_org_to_md(org_filename, md_folder):
    """
    Given an .org filename and the md_folder, attempts to guess the corresponding .md file.
    """
    base_name = os.path.splitext(os.path.basename(org_filename))[0]
    candidate_name = sanitize_filename(base_name) + ".md"
    possible_path = os.path.join(md_folder, candidate_name)
    return possible_path if os.path.exists(possible_path) else None

def file_diff_unified(org_file, md_file):
    """
    Compute a unified diff between .org and .md files using difflib.unified_diff.
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

def show_diff_colored_unified(diff):
    """
    Print a unified diff with colors using Rich.
    - Lines starting with '+' in green
    - Lines starting with '-' in red
    - Context lines in default (dim)
    """
    for line in diff:
        if line.startswith('+++') or line.startswith('---'):
            # File headers
            print(Text(line, style="bold"))
        elif line.startswith('+') and not line.startswith('+++'):
            print(Text(line, style="green"))
        elif line.startswith('-') and not line.startswith('---'):
            print(Text(line, style="red"))
        else:
            print(Text(line, style="dim"))

def show_all_lines_side_by_side(org_file, md_file):
    """
    Show all lines from both org and md files side-by-side, highlighting differences.
    - If lines match: normal text
    - If differ: highlight org line in red, md line in green

    We'll align lines using SequenceMatcher.
    """
    with open(org_file, 'r') as f_org:
        org_lines = f_org.readlines()

    with open(md_file, 'r') as f_md:
        md_lines = f_md.readlines()

    # We'll compare them line-by-line using SequenceMatcher
    # If lines are identical, print normal. If not, highlight differences.
    # However, lines might be added or removed, so let's use SequenceMatcher to get the best alignment.
    sm = SequenceMatcher(None, org_lines, md_lines)
    # opcodes tell us how to transform the first sequence into the second
    # Each opcode is a tuple (tag, i1, i2, j1, j2)
    # tag can be 'equal', 'replace', 'delete', 'insert'
    # i1,i2 slice for org_lines; j1,j2 slice for md_lines
    # We'll print side by side:
    # ORG_LINE | MD_LINE

    width = max(
        max((len(line) for line in org_lines), default=0),
        30
    )  # minimal width for padding

    print(Panel(f"[bold]Comparing {os.path.basename(org_file)} and {os.path.basename(md_file)} (all lines)[/bold]"))

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            # Lines are identical
            for k in range(i2 - i1):
                left_line = org_lines[i1 + k].rstrip('\n')
                right_line = md_lines[j1 + k].rstrip('\n')
                # print both lines normal color
                console.print(
                    f"{left_line:<{width}} | {right_line}",
                    style=""
                )

        elif tag == 'replace':
            # org_lines[i1:i2] replaced by md_lines[j1:j2]
            # print them line by line
            max_count = max(i2 - i1, j2 - j1)
            for offset in range(max_count):
                left_line = org_lines[i1 + offset].rstrip('\n') if i1 + offset < i2 else ""
                right_line = md_lines[j1 + offset].rstrip('\n') if j1 + offset < j2 else ""
                # highlight as difference
                console.print(
                    f"{left_line:<{width}} | {right_line}",
                    style=""
                )
                # To emphasize difference: left in red, right in green
                # We'll print them again in a second line with highlights or inline highlight
                # For simplicity, just color the lines if they differ:
                left_style = "red" if left_line else "dim"
                right_style = "green" if right_line else "dim"
                console.print(
                    f"{left_line:<{width}} | {right_line}",
                    style=""
                )
                # Move cursor up to overwrite line
                console.clear_live()

                # Print once with styling:
                console.print(
                    f"[{left_style}]{left_line:<{width}}[/] | [{right_style}]{right_line}[/]"
                )

        elif tag == 'delete':
            # org_lines[i1:i2] are deleted
            for k in range(i1, i2):
                left_line = org_lines[k].rstrip('\n')
                console.print(
                    f"[red]{left_line:<{width}}[/] | ",
                )

        elif tag == 'insert':
            # md_lines[j1:j2] are inserted
            for k in range(j1, j2):
                right_line = md_lines[k].rstrip('\n')
                console.print(
                    f"{'':<{width}} | [green]{right_line}[/]",
                )

def print_dir_diff(dcmp, relative_path=''):
    """
    Recursively print differences between directories (attachments).
    """
    prefix = relative_path + '/' if relative_path else ''
    
    if dcmp.left_only:
        print(f"[yellow]Only in original attachments ({prefix}):[/yellow] {dcmp.left_only}")
    if dcmp.right_only:
        print(f"[yellow]Only in new attachments ({prefix}):[/yellow] {dcmp.right_only}")
    if dcmp.diff_files:
        print(f"[red]Files differ in attachments ({prefix}):[/red] {dcmp.diff_files}")

    for sub_name, sub_dcmp in dcmp.subdirs.items():
        sub_path = prefix + sub_name
        print_dir_diff(sub_dcmp, relative_path=sub_path)

def compare_attachments(org_attachments_folder, md_attachments_folder):
    """
    Compare the attachments directory structures and print differences.
    """
    if not os.path.exists(org_attachments_folder):
        print(f"[bold red]Warning:[/bold red] Original attachments directory does not exist: {org_attachments_folder}")
        return
    if not os.path.exists(md_attachments_folder):
        print(f"[bold red]Warning:[/bold red] New attachments directory does not exist: {md_attachments_folder}")
        return

    dcmp = dircmp(org_attachments_folder, md_attachments_folder)
    print_dir_diff(dcmp)

def main():
    parser = argparse.ArgumentParser(description="Diff the results of Org-roam to Obsidian conversion.")
    parser.add_argument("--org-folder", required=True, help="Path to folder containing the original Org-roam .org files")
    parser.add_argument("--md-folder", required=True, help="Path to folder containing the converted Obsidian .md files")
    parser.add_argument("--org-attachments-folder", default=None, help="Path to original Org-roam attachments folder (default: <org-folder>/attachments)")
    parser.add_argument("--md-attachments-folder", default=None, help="Path to converted attachments folder (default: <md-folder>/attachments)")
    parser.add_argument("--show-all-lines", action="store_true", help="Show all lines instead of a unified diff. Differences will be highlighted.")

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
    print("[bold]### Comparing Org to Markdown Files ###[/bold]")
    if not os.path.exists(org_folder):
        print(f"[red]Org folder does not exist:[/red] {org_folder}")
    if not os.path.exists(md_folder):
        print(f"[red]MD folder does not exist:[/red] {md_folder}")

    if os.path.exists(org_folder) and os.path.exists(md_folder):
        org_files = [f for f in os.listdir(org_folder) if f.endswith(".org")]
        if not org_files:
            print("[yellow]No .org files found in org-folder.[/yellow]")
        for filename in org_files:
            org_path = os.path.join(org_folder, filename)
            md_path = map_org_to_md(org_path, md_folder)
            if md_path and os.path.exists(md_path):
                if args.show_all_lines:
                    show_all_lines_side_by_side(org_path, md_path)
                else:
                    diff = file_diff_unified(org_path, md_path)
                    if diff:
                        print(f"\n[bold]Differences found for {filename} -> {os.path.basename(md_path)}:[/bold]")
                        show_diff_colored_unified(diff)
                    else:
                        print(f"[green]No differences found for {filename}.[/green]")
            else:
                print(f"[red]No corresponding .md file found for {filename}[/red]")

    # Compare attachments directories
    print("\n[bold]### Comparing Attachments Directories ###[/bold]")
    compare_attachments(org_attachments_folder, md_attachments_folder)

if __name__ == "__main__":
    main()
