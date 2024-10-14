#!/bin/bash

# Navigate to the script's directory (test/)
cd "$(dirname "$0")"

# Create the fakedata directory structure
mkdir -p fakedata/data
mkdir -p fakedata/attachments/00/87f4a3-a24c-4a96-938f-f00ef1f67ef3
mkdir -p fakedata/attachments/00/8AADAE-AB7D-4A7C-9C64-C5DD95D1ACFA
mkdir -p fakedata/attachments/4d/5970E7-4DAD-4E87-9256-B1E63E4C2885

# Create the note1.org file with sample content
cat <<EOT > fakedata/data/note1.org
#+title: Note One
:PROPERTIES:
:ID:      87f4a3-a24c-4a96-938f-f00ef1f67ef3
:END:

This is a test note with an attachment.

[[attachment:attachment1.png]]

* Heading One
:PROPERTIES:
:ID:      8AADAE-AB7D-4A7C-9C64-C5DD95D1ACFA
:END:

Content under heading one with its own attachment.

[[attachment:attachment2.pdf]]

Link to [[id:5970E7-4DAD-4E87-9256-B1E63E4C2885][Note Two]].
EOT

# Create the note2.org file with sample content
cat <<EOT > fakedata/data/note2.org
#+title: Note Two
:PROPERTIES:
:ID:      5970E7-4DAD-4E87-9256-B1E63E4C2885
:END:

This is another test note with an attachment.

[[attachment:attachment3.jpg]]

* Subheading with ID
:PROPERTIES:
:ID:      7ab7a4-c880-4012-865c-4168c1c43aba
:END:

Content under subheading with a link back to [[id:87f4a3-a24c-4a96-938f-f00ef1f67ef3][Note One]].
EOT

# Create empty attachment files (placeholders)
touch fakedata/attachments/00/87f4a3-a24c-4a96-938f-f00ef1f67ef3/attachment1.png
touch fakedata/attachments/00/8AADAE-AB7D-4A7C-9C64-C5DD95D1ACFA/attachment2.pdf
touch fakedata/attachments/4d/5970E7-4DAD-4E87-9256-B1E63E4C2885/attachment3.jpg

echo "Fakedata folder structure created successfully."
