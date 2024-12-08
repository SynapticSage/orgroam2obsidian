import dspy
import json
import os

def check_conversion(org_file_path: str, md_file_path: str, prompt_path: str):
    """
    Uses the DSPy model to check if the conversion from an Org-roam file to a Markdown file
    was successful according to the specified prompt.

    Inputs
    ------
    org_file_path : str
        The path to the original Org-roam file.
    md_file_path : str
        The path to the converted Markdown file.
    prompt_path : str
        The path to the prompt file (`check.md`) that will be used to verify the conversion.

    Outputs
    -------
    dict : The output of the model, which contains the verification report.
    """
    # Read the prompt
    with open(prompt_path, 'r') as prompt_file:
        prompt_template = prompt_file.read()
    
    # Read the Org-roam file
    with open(org_file_path, 'r') as org_file:
        org_content = org_file.read()
    
    # Read the converted Markdown file
    with open(md_file_path, 'r') as md_file:
        md_content = md_file.read()
    
    # Prepare the prompt by inserting the Org-roam and Markdown contents
    prompt = f"{prompt_template}\n\n# Input Data\n\n**Original Org-roam File (`org_content`):**\n\n```org\n{org_content}\n```\n\n**Converted Markdown File (`md_content`):**\n\n```markdown\n{md_content}\n```"
    
    # Initialize the DSPy model (ensure it's properly configured)
    model = dspy.Model()
    
    # Process the prompt through the model
    response = model.generate(prompt)
    
    # Parse the JSON output from the response
    try:
        output = json.loads(response)
    except json.JSONDecodeError:
        print("Failed to parse the JSON output from the model.")
        return
    
    # Print the verification report
    print("Verification Report:")
    print(json.dumps(output, indent=4))

    return output

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check the conversion of Org-roam notes to Obsidian format")
    parser.add_argument("--org-file", dest="org_file_path", required=True, help="Path to the original Org-roam file")
    parser.add_argument("--md-file", dest="md_file_path", required=True, help="Path to the converted Markdown file")
    parser.add_argument("--prompt", dest="prompt_path", required=True, help="Path to the prompt file (check.md)")

    args = parser.parse_args()

    check_conversion(
        org_file_path=args.org_file_path,
        md_file_path=args.md_file_path,
        prompt_path=args.prompt_path
    )

