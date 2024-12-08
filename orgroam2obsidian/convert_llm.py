import dspy
import json
import os
import argparse
import shlex
import subprocess

def convert_with_dspy(file_source: str, file_path_for_target: str, prompt_path: str):
    """
    Applies the DSPy model to convert an Org-roam file to a Markdown file.

    Inputs
    ------
    file_source : str
        The path to the source Org-roam file.
    file_path_for_target : str
        The path to the directory where the Markdown file will be saved.
    prompt_path : str
        The path to the prompt file that will be used to generate the Markdown
        file.

    Outputs
    -------
    None
    """
    # Check if files and directories exist
    if not os.path.isfile(file_source):
        print(f"Source file does not exist: {file_source}")
        exit(1)
    if not os.path.isfile(prompt_path):
        print(f"Prompt file does not exist: {prompt_path}")
        exit(1)
    if not os.path.isdir(file_path_for_target):
        print(f"Target directory does not exist: {file_path_for_target}")
        exit(1)
    
    # Read the prompt
    with open(prompt_path, 'r') as prompt_file:
        prompt_template = prompt_file.read()
    
    # Read the source Org-roam file
    with open(file_source, 'r') as org_file:
        org_content = org_file.read()
    
    # Prepare the prompt by inserting the Org-roam content
    prompt = f"{prompt_template}\n\n# Input Org-roam File\n```\n{org_content}\n```"
    
    # Initialize the DSPy model (assuming it's configured to use an appropriate language model)
    model = dspy.Model()
    
    # Process the prompt through the model
    response = model.generate(prompt)
    
    # Parse the JSON output from the response
    try:
        output = json.loads(response)
    except json.JSONDecodeError:
        print("Failed to parse the JSON output from the model.")
        return
    
    # Write the Markdown file
    md_file_info = output.get("md-file", {})
    md_file_name = md_file_info.get("path", "output.md")
    md_content = md_file_info.get("content", "")
    md_file_path = os.path.join(file_path_for_target, md_file_name)
    
    os.makedirs(os.path.dirname(md_file_path), exist_ok=True)
    with open(md_file_path, 'w') as md_file:
        md_file.write(md_content)
    
    # Execute attachment file actions safely
    attachment_actions = output.get("attachment-file-actions", [])
    for action in attachment_actions:
        # Parse the command to ensure safety
        args = shlex.split(action)
        if args[0] == 'ln' and '-sf' in args:
            try:
                subprocess.run(args, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Failed to execute command: {action}")
                print(e)
        else:
            print(f"Unsafe or unsupported command skipped: {action}")
    
    print(f"Conversion complete. Markdown file saved to {md_file_path}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Org-roam files to Obsidian-compatible Markdown files using DSPy.")
    parser.add_argument("file_source", help="Path to the source Org-roam file.")
    parser.add_argument("file_path_for_target", help="Path to the directory where the Markdown file will be saved.")
    parser.add_argument("prompt_path", help="Path to the prompt file.")

    args = parser.parse_args()

    convert_with_dspy(args.file_source, args.file_path_for_target, args.prompt_path)
