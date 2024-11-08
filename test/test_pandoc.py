import os
import subprocess
import shlex
import pytest

@pytest.fixture
def setup_test_files(tmp_path):
    """
    Fixture to set up temporary Org and output files.
    """
    test_file_org = tmp_path / "test_id_links.org"
    output_md_no_preprocess = tmp_path / "output_no_preprocess.md"

    # Create a simple Org file with id: links
    org_content = """#+title: Test ID Links

This is a test note.

Link to another note: [[id:12345][Another Note]].

* Another Note
:PROPERTIES:
:ID:      12345
:END:

This is the target note.
"""

    test_file_org.write_text(org_content)

    return {
        "test_file_org": str(test_file_org),
        "output_md_no_preprocess": str(output_md_no_preprocess)
    }

def test_pandoc_without_preprocessing(setup_test_files):
    """
    Test Pandoc's behavior on Org files with id: links without preprocessing.
    """
    test_files = setup_test_files

    # Convert without preprocessing
    cmd = f"pandoc -f org -t markdown '{test_files['test_file_org']}' -o '{test_files['output_md_no_preprocess']}'"
    subprocess.run(shlex.split(cmd))

    # Read the output
    with open(test_files['output_md_no_preprocess'], 'r') as f:
        output_no_preprocess = f.read()

    print("Output without preprocessing:")
    print(output_no_preprocess)

    # Assertion: Pandoc should convert id: links to standard Markdown links
    assert '[Another Note](id:12345)' in output_no_preprocess, "id: link not converted correctly by Pandoc"
