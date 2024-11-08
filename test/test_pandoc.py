import os
import subprocess
import shlex
import pytest
import re

def test_pandoc_id_link_handling():
    """
    Test how Pandoc handles Org-mode id: links and validate the best approach.
    """
    # Setup test files
    test_dir = os.path.dirname(__file__)
    test_file_org = os.path.join(test_dir, 'test_id_links.org')
    test_file_preprocessed_org = os.path.join(test_dir, 'test_id_links_preprocessed.org')
    output_md_no_preprocess = os.path.join(test_dir, 'output_no_preprocess.md')
    output_md_preprocessed = os.path.join(test_dir, 'output_preprocessed.md')

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

    with open(test_file_org, 'w') as f:
        f.write(org_content)

    # Test 1: Convert without preprocessing
    cmd = f"pandoc -f org -t markdown '{test_file_org}' -o '{output_md_no_preprocess}'"
    subprocess.run(shlex.split(cmd))

    # Read the output
    with open(output_md_no_preprocess, 'r') as f:
        output_no_preprocess = f.read()

    # Test 2: Preprocess the Org file to transform id: links
    def preprocess_org_content(content):
        pattern = r'\[\[id:([^\]]+)\]\[([^\]]+)\]\]'
        new_content = re.sub(pattern, r'[[\2]](id:\1)', content)
        return new_content

    with open(test_file_org, 'r') as f:
        content = f.read()

    preprocessed_content = preprocess_org_content(content)

    with open(test_file_preprocessed_org, 'w') as f:
        f.write(preprocessed_content)

    # Convert the preprocessed Org file
    cmd = f"pandoc -f org -t markdown '{test_file_preprocessed_org}' -o '{output_md_preprocessed}'"
    subprocess.run(shlex.split(cmd))

    # Read the output
    with open(output_md_preprocessed, 'r') as f:
        output_preprocessed = f.read()

    # Cleanup test files
    os.remove(test_file_org)
    os.remove(test_file_preprocessed_org)
    os.remove(output_md_no_preprocess)
    os.remove(output_md_preprocessed)

    # Validate the outputs
    print("Output without preprocessing:")
    print(output_no_preprocess)
    print("\nOutput with preprocessing:")
    print(output_preprocessed)

    # Assertions
    # Check if the link is present in the outputs
    assert '[[id:12345][Another Note]]' not in output_no_preprocess, "id: link not processed by Pandoc"
    assert '[Another Note](id:12345)' in output_preprocessed, "Preprocessed id: link not converted correctly"

    # Decide the best approach
    assert '[Another Note](id:12345)' in output_preprocessed, "Preprocessing allows Pandoc to handle id: links"

    # The test passes if preprocessing works better
