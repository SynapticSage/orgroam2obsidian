"""
notecapture.py

focused on the process of note capture.

# TODO:
- [ ] Refactor the `extract_notes_from_file` function to be more readable and maintainable.
- [ ] Change from `Note` class into a `Node` class: rather than considering only one node
     we can directly support the tree structure of the Org file.
"""

class Note:
    def __init__(self, id, title, content, level,
                 attachments=None, input_filename=None,
                 input_folder=None, input_fullpath=None,
                 output_fullpath=None):

        self.id = id
        self.title = title
        self.content = content
        self.level = level  # Heading level in the Org file
        self.attachments = attachments if attachments is not None else []
        self.input_filename = None  # Path to the input Org file
        self.input_folder = None  # Path to the input Org file
        self.input_fullpath = None  # Path to the input Org file
        self.output_fullpath = None  # Path to the output Markdown file

# NOTE: very messy function
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
    input_filename = os.path.basename(filename)
    input_path = os.path.dirname(filename)
    input_fullpath = os.path.abspath(filename)

    # First, PARSE the _title and properties_ at the top of the file
    while line_index < len(lines):
        line = lines[line_index]
        # Check for title
        # Handle #+title as a special case
        title_match = re.match(r'^\s*#\+title:\s*(.+)', line, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            line_index += 1
            continue
        # Handle other #+ properties
        prop_match = re.match(r'^\s*#\+([^:]+):\s*(.+)', line, re.IGNORECASE)
        if prop_match:
            key, value = prop_match.groups()
            properties[f"#+{key.upper()}"] = value.strip()
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
