import os
import shutil
import pytest
from orgroam2obsidian.convert import *

# Constants for test directories
TEST_DIR = os.path.dirname(__file__)
INPUT_FOLDER = os.path.join(TEST_DIR, 'fakedata', 'data')
OUTPUT_FOLDER = os.path.join(TEST_DIR, 'fakedata', 'output')
ATTACHMENTS_FOLDER = os.path.join(TEST_DIR, 'fakedata', 'attachments')

@pytest.fixture
def setup_test_environment():
    # Ensure the output directory is clean before each test
    if os.path.exists(OUTPUT_FOLDER):
        shutil.rmtree(OUTPUT_FOLDER)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def test_extract_notes_from_file():
    # Test the extraction of notes from an Org file
    filepath = os.path.join(INPUT_FOLDER, 'note1.org')
    notes = extract_notes_from_file(filepath)
    assert len(notes) == 2
    note_titles = [note.title for note in notes]
    assert 'Note One' in note_titles
    assert 'Heading One' in note_titles

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

def test_links_replaced(setup_test_environment):
    # Run the conversion first
    main(input_folder=INPUT_FOLDER, output_folder=OUTPUT_FOLDER, attachments_folder=ATTACHMENTS_FOLDER)
    # Test that links are correctly replaced in the Markdown files
    note_one_md_path = os.path.join(OUTPUT_FOLDER, 'Note One.md')
    with open(note_one_md_path, 'r') as f:
        content = f.read()
        # Check that the link to Note Two is correctly replaced
        assert '[[Note Two]]' in content
        # Check that the attachment link is correctly replaced
        assert '![[attachments/87f4a3-a24c-4a96-938f-f00ef1f67ef3/attachment1.png]]' in content
