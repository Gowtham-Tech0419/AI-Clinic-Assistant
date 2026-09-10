import fitz

doc = fitz.open("data/insurance_policies.pdf")
for page_num in range(len(doc)):
    page = doc[page_num]
    text = page.get_text()
    print(f"Page {page_num+1}: {text[:100]}...")
doc.close()