# test/test.py

import os
import shutil
import pytest
import re
from orgroam2obsidian.convert import (
    extract_notes_from_file,
    sanitize_filename,
    replace_links,
    copy_attachments,
    Note,
    main,
)

# Set up paths for test data
TEST_DIR = os.path.dirname(__file__)
FAKEDATA_DIR = os.path.join(TEST_DIR, 'fakedata')
INPUT_FOLDER = os.path.join(FAKEDATA_DIR, 'data')
ATTACHMENTS_FOLDER = os.path.join(FAKEDATA_DIR, 'attachments')
OUTPUT_FOLDER = os.path.join(FAKEDATA_DIR, 'output')

@pytest.fixture(scope='module')
def setup_test_environment():
    # Prepare the output directory
    if os.path.exists(OUTPUT_FOLDER):
        shutil.rmtree(OUTPUT_FOLDER)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    yield
    # Clean up after tests
    shutil.rmtree(OUTPUT_FOLDER)

def test_extract_notes_from_file():
    # Test that notes are correctly extracted from an Org file
    note1_path = os.path.join(INPUT_FOLDER, 'note1.org')
    notes = extract_notes_from_file(note1_path)
    assert len(notes) == 2
    note_ids = [note.id for note in notes]
    assert '87f4a3-a24c-4a96-938f-f00ef1f67ef3' in note_ids
    assert '8AADAE-AB7D-4A7C-9C64-C5DD95D1ACFA' in note_ids

def test_sanitize_filename():
    # Test filename sanitization
    filename = 'Invalid/File:Name?.org'
    sanitized = sanitize_filename(filename)
    assert sanitized == 'Invalid-File-Name-.org'

def test_replace_links():
    # Test link replacement in notes
    second_brain = {
        '87f4a3-a24c-4a96-938f-f00ef1f67ef3': Note(
            id='87f4a3-a24c-4a96-938f-f00ef1f67ef3',
            title='Note One',
            content='',
            level=1
        ),
        '5970E7-4DAD-4E87-9256-B1E63E4C2885': Note(
            id='5970E7-4DAD-4E87-9256-B1E63E4C2885',
            title='Note Two',
            content='',
            level=1
        ),
    }
    current_note = second_brain['87f4a3-a24c-4a96-938f-f00ef1f67ef3']
    link_text = 'Link to Note Two'
    link_target = 'id:5970E7-4DAD-4E87-9256-B1E63E4C2885'
    match = re.match(r'(.*)', '')
    match = re.match(r'.*', '')
    class MockMatch:
        def group(self, index):
            if index == 1:
                return link_text
            elif index == 2:
                return link_target
    replaced_link = replace_links(second_brain, MockMatch(), current_note)
    assert replaced_link == '[[Note Two]]'

def test_copy_attachments(setup_test_environment):
    # Test that attachments are copied correctly
    note = Note(
        id='87f4a3-a24c-4a96-938f-f00ef1f67ef3',
        title='Note One',
        content='',
        level=1,
        attachments=['attachment1.png']
    )
    copy_attachments(note, ATTACHMENTS_FOLDER, OUTPUT_FOLDER)
    # Check that the attachment exists in the output directory
    attachment_output_path = os.path.join(
        OUTPUT_FOLDER,
        'attachments',
        note.id,
        'attachment1.png'
    )
    assert os.path.exists(attachment_output_path)

def test_full_conversion(setup_test_environment):
    # Test the full conversion process
    main(input_folder=INPUT_FOLDER, output_folder=OUTPUT_FOLDER, attachments_folder=ATTACHMENTS_FOLDER)
    # Check that output files are created
    output_files = os.listdir(OUTPUT_FOLDER)
    output_files = [f for f in output_files if f.endswith('.md')]
    expected_files = [
        'Note One.md',
        'Heading One.md',
        'Note Two.md',
        'Subheading with ID.md'
    ]
    for filename in expected_files:
        assert filename in output_files
    # Check that attachments are copied
    attachment_paths = [
        os.path.join(OUTPUT_FOLDER, 'attachments', '87f4a3-a24c-4a96-938f-f00ef1f67ef3', 'attachment1.png'),
        os.path.join(OUTPUT_FOLDER, 'attachments', '8AADAE-AB7D-4A7C-9C64-C5DD95D1ACFA', 'attachment2.pdf'),
        os.path.join(OUTPUT_FOLDER, 'attachments', '5970E7-4DAD-4E87-9256-B1E63E4C2885', 'attachment3.jpg'),
    ]
    for path in attachment_paths:
        assert os.path.exists(path)
    # Check that links are correctly replaced in the Markdown files
    note_one_md_path = os.path.join(OUTPUT_FOLDER, 'Note One.md')
    with open(note_one_md_path, 'r') as f:
        content = f.read()
        assert '[[Note Two]]' in content
        assert '![[attachments/87f4a3-a24c-4a96-938f-f00ef1f67ef3/attachment1.png]]' in content
