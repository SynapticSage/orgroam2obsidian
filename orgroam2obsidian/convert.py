#!/usr/bin/env python

import os
import re
import shlex
import shutil
import subprocess
import sys
import argparse

ATTACHMENTS_FOLDER = 'attachments'  # Default value; can be overridden

class Note:
    def __init__(self, id, title, content, level, attachments=None):
        self.id = id
        self.title = title
        self.content = content
        self.level = level  # Heading level in the Org file
        self.attachments = attachments if attachments is not None else []

def get_attachment_prefix(note_id):
    return note_id[:2]

def extract_notes_from_file(filename: str):
    """
    Extract notes (nodes) from an Org file, including the top-level content and subheadings with their own IDs.
    """
    notes = []
    with open(filename, 'r') as fd:
        lines = fd.readlines()

    # Initialize variables
    note = None
    content_lines = []
    attachments = []
    current_level = 0
    title = None
    in_properties = False
    properties = {}
    line_index = 0

    # First, parse the title and properties at the top of the file
    while line_index < len(lines):
        line = lines[line_index]
        # Check for title
        title_match = re.match(r'^\s*#\+title:\s*(.+)', line, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            line_index += 1
            continue
        # Check for property drawer start
        elif line.strip() == ':PROPERTIES:':
            in_properties = True
            line_index += 1
            continue
        # Check for property drawer end
        elif line.strip() == ':END:':
            in_properties = False
            line_index += 1
            continue
        # Collect properties
        elif in_properties:
            prop_match = re.match(r':([^:]+):\s*(.+)', line.strip())
            if prop_match:
                key, value = prop_match.groups()
                properties[key] = value
            line_index += 1
            continue
        # Detect first heading
        elif re.match(r'^\*+\s+', line):
            break  # Start of first heading
        else:
            # Collect content lines
            content_lines.append(line)
            line_index += 1

    # Create the top-level note if it has an ID
    if properties.get('ID'):
        note = Note(
            id=properties['ID'],
            title=title if title else 'Untitled',
            content='',
            level=0,
        )
        # Collect attachments from the content
        attachments = []
        attachment_link_pattern = r'\[\[attachment:([^\]]+)\]\]'
        file_link_pattern = r'\[\[file:([^\]]+)\]\]'
        for line in content_lines:
            attachment_matches = re.findall(attachment_link_pattern, line)
            attachments.extend(attachment_matches)
            file_matches = re.findall(file_link_pattern, line)
            for file_link in file_matches:
                if file_link.startswith('attachments/') or file_link.startswith('./'):
                    attachments.append(file_link)
        note.attachments = attachments
        note.content = ''.join(content_lines)
        notes.append(note)
        note = None  # Reset for the next note
        content_lines = []
        attachments = []

    # Now process the rest of the file
    while line_index < len(lines):
        line = lines[line_index]
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
            # Start a new note
            stars = heading_match.group('stars')
            current_level = len(stars)
            title = heading_match.group('title')
            properties = {}
            in_properties = False
            line_index += 1
            # Check for properties immediately after heading
            while line_index < len(lines):
                line = lines[line_index]
                if line.strip() == ':PROPERTIES:':
                    in_properties = True
                    line_index += 1
                elif line.strip() == ':END:':
                    in_properties = False
                    line_index += 1
                elif in_properties:
                    prop_match = re.match(r':([^:]+):\s*(.+)', line.strip())
                    if prop_match:
                        key, value = prop_match.groups()
                        properties[key] = value
                    line_index += 1
                else:
                    break  # Done with properties
            # Now check if this heading has an ID
            if properties.get('ID'):
                note = Note(
                    id=properties['ID'],
                    title=title,
                    content='',
                    level=current_level
                )
            else:
                note = None
            continue
        else:
            if note:
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
            line_index += 1

    # Handle the last note
    if note:
        note.content = ''.join(content_lines)
        note.attachments = attachments
        notes.append(note)

    return notes

def sanitize_filename(filename):
    # [Same as previous implementation]
    sanitized_filename = re.sub(r'[\'<>:"/\\|?*\x00-\x1F]', '-', filename)
    return sanitized_filename

def replace_links(second_brain, match, current_note):
    # [Ensure only one definition exists]
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

def copy_attachments(note, attachments_folder, output_folder, use_title=False):
    """ Copy attachments for a note to the output folder """
    attachment_prefix = get_attachment_prefix(note.id)
    if not attachment_prefix:
        print(f"No attachment prefix found for note {note.id}")
        return
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
        copy_attachments(note, attachments_folder, output_folder, use_title)

    # Step 3: Update links in the Markdown files
    print("Updating links in Markdown files...")
    link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
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
