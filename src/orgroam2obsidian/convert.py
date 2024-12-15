#!/usr/bin/env python
"""
Notes conversion script for Org-roam to Obsidian.

This script converts Org-roam notes to Obsidian format, including converting Org files to Markdown and updating links.

TODO:
-----
- Clean up the `extract_notes_from_file` function
- Create an `evaluate_conversion` function that works via LLM
- Note naming is busted -- downstream code fails to appreciate/expect the would-be names of notes after conversion.
    - Place this metadata into the Note object, and utilize it, rather than recompute or hardcode it.

"""

# TODO: 2024/10/17
# 1. Move utility functions to utils.py
# 2. Create more utils:
#   - get_note_path(...)
#   - get_attachment_path(...)

import os
import re
import shlex
import shutil
import subprocess
import argparse
from .notecapture import extract_notes_from_file

ATTACHMENTS_FOLDER = 'attachments'  # Default value; can be overridden

def get_attachment_prefix(note_id):
    # Use the first two characters of the note ID as the attachment prefix
    return note_id[:2]


def sanitize_filename(filename):
    """
    Sanitize filenames to remove or replace characters that are invalid in file paths.
    """
    sanitized_filename = re.sub(r'[\'<>:"/\\|?*\x00-\x1F]', '-', filename)
    return sanitized_filename

def replace_links(second_brain, match, current_note):
    """
    Replace links in Markdown files with Obsidian-compatible links.
    """
    is_image = match.group(1) == '!'
    link_text = match.group(2)
    link_target = match.group(3)
    if link_target.startswith("id:"):
        target_note_id = link_target.removeprefix('id:')
        target_note = second_brain.get(target_note_id)
        if target_note:
            return f"[[{sanitize_filename(target_note.title)}]]"
        else:
            return f"[Note not found: {link_text}]({link_target})"
    elif link_target.startswith("attachment:"):
        attachment_path = link_target.removeprefix('attachment:')
        attachment_filename = os.path.basename(attachment_path)
        # Construct the new path to the attachment in the output folder
        new_attachment_path = f"{ATTACHMENTS_FOLDER}/{current_note.id}/{attachment_filename}"
        if is_image:
            return f"![[{new_attachment_path}]]"
        else:
            return f"[[{new_attachment_path}]]"
    else:
        if is_image:
            return f"![]({link_target})"
        else:
            return f"[{link_text}]({link_target})"

def copy_attachments(note, attachments_folder, output_folder, use_title=False):
    """Copy attachments for a note to the output folder."""
    attachment_prefix = get_attachment_prefix(note.id)
    for attachment in note.attachments:
        source_attachment_path = os.path.join(
            attachments_folder,
            attachment_prefix,
            note.id,
            attachment
        )
        if os.path.exists(source_attachment_path):
            # Use basename of ATTACHMENTS_FOLDER
            attachments_basename = os.path.basename(ATTACHMENTS_FOLDER)
            # Use note title or ID based on the use_title flag
            folder_name = sanitize_filename(note.title) if use_title else note.id
            dest_dir = os.path.join(output_folder, attachments_basename, folder_name)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, attachment)
            if os.path.isdir(source_attachment_path):
                shutil.copytree(source_attachment_path, dest_path) # in case its a folder
            else:
                shutil.copy2(source_attachment_path, dest_path)
        else:
            print(f"Attachment not found: {source_attachment_path}")

def main(input_folder='input', output_folder='output', attachments_folder='attachments', use_title=False):

    print("Converting Org-roam notes to Obsidian format...")
    print("Input folder:", input_folder)
    print("Attachments folder:", attachments_folder)
    print("Output folder:", output_folder)
    print("Use title for attachment folders:", use_title)

    global ATTACHMENTS_FOLDER
    ATTACHMENTS_FOLDER = attachments_folder  # Update if overridden

    second_brain = {}

    # Step 1: Process Org-roam files to extract IDs, titles, and attachments
    print("Processing files...")
    for file in (f for f in os.listdir(input_folder) if f.endswith('.org')):
        filepath = os.path.join(input_folder, file)
        notes = extract_notes_from_file(filepath)
        for note in notes:
            second_brain[note.id] = note

    # Step 2: Convert notes to Markdown and copy attachments
    print("Transforming notes and copying attachments...")
    os.makedirs(output_folder, exist_ok=True)
    for note_id, note in second_brain.items():
        print(f"Converting note: {note.title}, ID: {note_id}")
        # Create a temporary Org file for each note
        temp_org_filename = os.path.join(output_folder, f"{note_id}.org")
        print(f"Creating temporary Org file: {temp_org_filename}")
        with open(temp_org_filename, 'w') as fd:
            fd.write('*' * note.level + ' ' + note.title + '\n')
            fd.write(note.content)

        # Convert the temporary Org file to Markdown using Pandoc
        output_filename = os.path.join(output_folder, f"{sanitize_filename(note.title)}.md")
        cmd = f"pandoc -f org -t markdown --wrap=none '{temp_org_filename}' -o '{output_filename}'"
        subprocess.run(shlex.split(cmd))

        # Remove the temporary Org file
        os.remove(temp_org_filename)

        # Copy attachments
        copy_attachments(note, attachments_folder, output_folder, use_title)

    # Step 3: Update links in the Markdown files
    print("Updating links in Markdown files...")
    # Update regex pattern to match both standard and image links
    link_pattern = r'(!?)\[(.*?)\]\((.*?)\)'
    for note_id, note in second_brain.items():
        output_filename = os.path.join(output_folder, f"{sanitize_filename(note.title)}.md")
        print(f"Processing file: {output_filename}")
        with open(output_filename, 'r') as fd:
            content = fd.read()
            # Replace links using the replace_links function
            new_content = re.sub(
                link_pattern,
                lambda m: replace_links(second_brain, m, note),
                content
            )
        with open(output_filename, 'w') as fd:
            fd.write(new_content)

    print("Conversion complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Org-roam notes to Obsidian format")
    parser.add_argument("--input", dest="input_folder", default="input", help="Folder containing Org-roam notes")
    parser.add_argument("--output", dest="output_folder", default="output", help="Destination folder for Obsidian notes")
    parser.add_argument("--attachments", dest="attachments_folder", default="attachments", help="Folder containing attachments")
    parser.add_argument("--use-title", dest="use_title", action="store_true", help="Use note title for attachment folders instead of ID")
    args = parser.parse_args()

    main(
        output_folder=args.output_folder,
        input_folder=args.input_folder,
        attachments_folder=args.attachments_folder,
        use_title=args.use_title
    )
