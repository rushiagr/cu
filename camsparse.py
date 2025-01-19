# history of things i tried
import pdfplumber
with pdfplumber.open("test.pdf") as pdf:
    first_page = pdf.pages[0]
    print(first_page.chars[0])
with pdfplumber.open("document.pdf") as pdf:
    text = ""
    for page in pdf.pages:
        text += page.extract_text()
with pdfplumber.open("test.pdf") as pdf:
    text = ""
    for page in pdf.pages:
        text += page.extract_text()
text
print(text)
