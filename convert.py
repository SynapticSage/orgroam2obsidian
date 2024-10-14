#!/usr/bin/env python3

import os
import re
import shlex
import shutil
import subprocess
import sys
import argparse

class Note:
    def __init__(self, id, title, content, level, attachments=None):
        self.id = id
        self.title = title
        self.content = content
        self.level = level  # Heading level in the Org file
        self.attachments = attachments if attachments is not None else []

def extract_notes_from_file(filename: str):
    """
    Extract notes (nodes) from an Org file, including subheadings with their own IDs.
    """
    notes = []
    with open(filename, 'r') as fd:
        lines = fd.readlines()

    # Initialize variables
    note = None
    collecting = False
    content_lines = []
    attachments = []
    current_level = 0
    title = None
    id = None

    for i, line in enumerate(lines):
        # Detect headings
        heading_match = re.match(r'^(?P<stars>\*+)\s+(?P<title>.+)', line)
        if heading_match:
            # If we were collecting a note, save it
            if note:
                note.content = ''.join(content_lines)
                note.attachments = attachments
                notes.append(note)
                # Reset for the next note
                content_lines = []
                attachments = []
                note = None
                collecting = False

            stars = heading_match.group('stars')
            current_level = len(stars)
            title = heading_match.group('title')

            # Check for ID in property drawer below heading
            # Look ahead in lines to find :ID: property
            id = None
            j = i + 1
            in_properties = False
            while j < len(lines):
                prop_line = lines[j].strip()
                if prop_line == ':PROPERTIES:':
                    in_properties = True
                elif prop_line == ':END:':
                    in_properties = False
                elif in_properties:
                    id_match = re.match(r':ID:\s+([a-f0-9\-]+)', prop_line)
                    if id_match:
                        id = id_match.group(1)
                else:
                    break  # Stop if we're past the property drawer
                j += 1

            if id:
                # Start collecting this note
                note = Note(id=id, title=title, content='', level=current_level)
                collecting = True
            else:
                collecting = False  # Skip headings without ID
        else:
            if collecting:
                # Collect content lines
                content_lines.append(line)
                # Find attachment links
                attachment_link_pattern = r'\[\[attachment:([^\]]+)\]\]'
                file_link_pattern = r'\[\[file:([^\]]+)\]\]'
                attachment_matches = re.findall(attachment_link_pattern, line)
                attachments.extend(attachment_matches)
                file_matches = re.findall(file_link_pattern, line)
                for file_link in file_matches:
                    if file_link.startswith('attachments/') or file_link.startswith('./'):
                        attachments.append(file_link)

    # Handle the last note in the file
    if note:
        note.content = ''.join(content_lines)
        note.attachments = attachments
        notes.append(note)

    return notes

def sanitize_filename(filename):
    """
    Sanitize filenames to remove or replace characters that are invalid in file paths.
    """
    sanitized_filename = re.sub(r'[\'<>:"/\\|?*\x00-\x1F]', '-', filename)
    return sanitized_filename

def replace_links(second_brain, match, current_note):
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
        new_attachment_path = f"{ATTACHMENTS_FOLDER}/{current_note.id}/{attachment_filename}"
        return f"![[{new_attachment_path}]]"
    else:
        return f"[{link_text}]({link_target})"

def replace_links(second_brain, match, current_note):
    # ... [Same as previous implementation] ...
    pass

def copy_attachments(note, original_org_file, attachments_folder, output_folder):
    # Logic to copy attachments
    attachment_dir = os.path.dirname(original_org_file)
    for attachment in note.attachments:
        # Compute attachment path
        attachment_subdir = note.id
        # Extract first two characters for the directory (e.g., '87f4a3...' -> '87')
        attachment_prefix = attachment_subdir[:2]
        source_attachment_path = os.path.join(
            attachments_folder,
            attachment_prefix,
            attachment_subdir,
            attachment
        )
        if os.path.exists(source_attachment_path):
            dest_dir = os.path.join(output_folder, 'attachments', note.id)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, attachment)
            shutil.copy2(source_attachment_path, dest_path)
        else:
            print(f"Attachment not found: {source_attachment_path}")

def main(input_folder='input', output_folder='output', attachments_folder='attachments'):
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
        # Create a temporary Org file for each note
        temp_org_filename = os.path.join(output_folder, f"{note_id}.org")
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
        # Find the original Org file this note came from
        original_org_file = None
        for file in os.listdir(input_folder):
            if file.endswith('.org'):
                filepath = os.path.join(input_folder, file)
                with open(filepath, 'r') as fd:
                    content = fd.read()
                    if note.id in content:
                        original_org_file = filepath
                        break
        if original_org_file:
            copy_attachments(note, original_org_file, attachments_folder, output_folder)
        else:
            print(f"Original Org file not found for note {note.title}")

    # Step 3: Update links in the Markdown files
    print("Updating links in Markdown files...")
    link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    for note_id, note in second_brain.items():
        output_filename = os.path.join(output_folder, f"{sanitize_filename(note.title)}.md")
        print(f"Processing file: {output_filename}")
        with open(output_filename, 'r') as fd:
            content = fd.read()
            # Replace links using the replace_links function
            new_content = re.sub(link_pattern, lambda m: replace_links(second_brain, m, note), content)
        with open(output_filename, 'w') as fd:
            fd.write(new_content)

    print("Conversion complete!")
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Org-roam notes to Obsidian format")
    parser.add_argument("--input", dest="input_folder", default="input", help="Folder containing Org-roam notes")
    parser.add_argument("--output", dest="output_folder", default="output", help="Destination folder for Obsidian notes")
    parser.add_argument("--attachments", dest="attachments_folder", default="attachments", help="Subfolder in OUTPUT_FOLDER for attachments")
    args = parser.parse_args()

    main(output_folder=args.output_folder, input_folder=args.input_folder,
         attachments_folder=args.attachments_folder)
