import pdfplumber

with pdfplumber.open(r"uploads\17e99050-5790-48ff-9786-974aedc80b3e.pdf") as pdf:
    text = pdf.pages[0].extract_text(x_tolerance=1)
    print(text)