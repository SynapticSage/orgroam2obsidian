#!/usr/bin/env python3

import os
import re
import shlex
import shutil
import subprocess

# Configuration
INPUT_FOLDER = 'input'           # Folder containing Org-roam notes
OUTPUT_FOLDER = 'output'         # Destination folder for Obsidian notes
ATTACHMENTS_FOLDER = 'attachments'  # Subfolder in OUTPUT_FOLDER for attachments

class Note:
    def __init__(self, id, title, filename, attachments=None):
        self.id = id
        self.title = title
        self.filename = filename
        self.attachments = attachments if attachments is not None else []

def process_file(filename: str):
    """
    Process an Org file to extract the note's ID, title, and any attachment links.
    """
    id_pattern = r':ID:\s+([a-f0-9\-]+)'
    title_pattern = r'\#\+title:\s+(.+)'
    attachment_link_pattern = r'\[\[attachment:([^\]]+)\]\]'
    file_link_pattern = r'\[\[file:([^\]]+)\]\]'
    regexes = [id_pattern, title_pattern]
    results = []
    attachments = []
    with open(filename, 'r') as fd:
        lines = fd.readlines()
        current_pattern = regexes.pop(0)
        for line in lines:
            match = re.search(current_pattern, line)
            if match:
                results.append(match.group(1))
                if not regexes:
                    break
                current_pattern = regexes.pop(0)
        if len(results) != 2:
            return None
        # Parse for attachment and file links
        for line in lines:
            # Find attachment links
            attachment_matches = re.findall(attachment_link_pattern, line)
            attachments.extend(attachment_matches)
            # Find file links pointing to attachments
            file_matches = re.findall(file_link_pattern, line)
            for file_link in file_matches:
                if file_link.startswith('attachments/') or file_link.startswith('./'):
                    attachments.append(file_link)
        return Note(results[0], results[1], filename, attachments)

def sanitize_filename(filename):
    """
    Sanitize filenames to remove or replace characters that are invalid in file paths.
    """
    sanitized_filename = re.sub(r'[\'<>:"/\\|?*\x00-\x1F]', '-', filename)
    return sanitized_filename

def replace_links(second_brain, match, note):
    """
    Replace Org-roam links with Obsidian-compatible Markdown links.
    """
    link_text = match.group(1)
    link_target = match.group(2)
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
        new_attachment_path = f"{ATTACHMENTS_FOLDER}/{note.id}/{attachment_filename}"
        return f"![[{new_attachment_path}]]"
    else:
        return f"[{link_text}]({link_target})"

if __name__ == "__main__":
    second_brain = {}

    # Step 1: Process Org-roam files to extract IDs, titles, and attachments
    print("Processing files...")
    for file in (f for f in os.listdir(INPUT_FOLDER) if f.endswith('.org')):
        note = process_file(f"{INPUT_FOLDER}/{file}")
        if note:
            second_brain[note.id] = note

    # Step 2: Convert Org files to Markdown and copy attachments
    print("Transforming files and copying attachments...")
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    for _, note in second_brain.items():
        output_filename = f"{OUTPUT_FOLDER}/{sanitize_filename(note.title)}.md"
        # Convert Org file to Markdown using Pandoc
        cmd = f"pandoc -f org -t markdown --wrap=none '{note.filename}' -o '{output_filename}'"
        subprocess.run(shlex.split(cmd))
        # Copy attachments
        if note.attachments:
            for attachment in note.attachments:
                # Determine the path to the attachment
                attachment_dir = os.path.dirname(note.filename)
                # Handle absolute and relative paths
                if attachment.startswith("./") or attachment.startswith("../"):
                    attachment_path = os.path.normpath(os.path.join(attachment_dir, attachment))
                else:
                    # Assuming attachments are stored in 'attachments/ID/' directory
                    attachment_path = os.path.join(attachment_dir, 'attachments', note.id, attachment)
                if not os.path.exists(attachment_path):
                    # Try relative to the note file
                    attachment_path = os.path.join(attachment_dir, attachment)
                if os.path.exists(attachment_path):
                    # Copy the attachment to OUTPUT_FOLDER/ATTACHMENTS_FOLDER/ID/
                    dest_dir = f"{OUTPUT_FOLDER}/{ATTACHMENTS_FOLDER}/{note.id}"
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_path = os.path.join(dest_dir, os.path.basename(attachment))
                    shutil.copy2(attachment_path, dest_path)
                else:
                    print(f"Attachment not found: {attachment_path}")

    # Step 3: Update links in the Markdown files to point to the new attachment locations
    print("Updating links in Markdown files...")
    link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    for _, note in second_brain.items():
        output_filename = f"{OUTPUT_FOLDER}/{sanitize_filename(note.title)}.md"
        print(f"Processing file: {output_filename}")
        with open(output_filename, 'r') as fd:
            content = fd.read()
            # Replace links using the replace_links function
            new_content = re.sub(link_pattern, lambda m: replace_links(second_brain, m, note), content)
        with open(output_filename, 'w') as fd:
            fd.write(new_content)

    print("Conversion complete!")