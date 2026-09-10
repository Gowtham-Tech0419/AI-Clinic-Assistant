import fitz  # PyMuPDF

def create_insurance_pdf():
    doc = fitz.open()

    # Page 1: Header and overview
    page1 = doc.new_page()
    page1.insert_text((50, 50), "ABC Multi-Specialty Clinic - Insurance Policy")
    page1.insert_text((50, 80), "Effective Date: January 1, 2025")
    page1.insert_text((50, 110), "Policy Number: INS-2025-001")
    page1.insert_text((50, 150), "We accept all major insurance providers. Please present your insurance card at each visit.")
    page1.insert_text((50, 180), "Covered Services:")
    page1.insert_text((50, 210), "  - General consultations (Office visits)")
    page1.insert_text((50, 230), "  - Specialist consultations (Cardiology, Neurology, etc.)")
    page1.insert_text((50, 250), "  - Diagnostic tests (X-ray, blood work, ECG)")
    page1.insert_text((50, 270), "  - Preventive care (annual checkups)")
    page1.insert_text((50, 300), "Co-pay: $20 for general visit, $40 for specialist (subject to insurance plan).")

    # Page 2: Exclusions and claims
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Exclusions:")
    page2.insert_text((50, 80), "  - Cosmetic procedures")
    page2.insert_text((50, 100), "  - Experimental treatments")
    page2.insert_text((50, 120), "  - Prescriptions not on the approved drug list")
    page2.insert_text((50, 150), "  - Services not pre-authorized (where required)")
    page2.insert_text((50, 190), "Claims:")
    page2.insert_text((50, 220), "  - We file claims on your behalf.")
    page2.insert_text((50, 240), "  - You are responsible for co-pays and deductibles.")
    page2.insert_text((50, 260), "  - For out-of-network providers, coverage may be limited.")

    # Page 3: Contact and additional info
    page3 = doc.new_page()
    page3.insert_text((50, 50), "For insurance questions, contact our billing department:")
    page3.insert_text((50, 80), "  Phone: 1-800-555-0199")
    page3.insert_text((50, 100), "  Email: billing@abcclinic.com")
    page3.insert_text((50, 120), "  Hours: Mon-Fri 9am-5pm")
    page3.insert_text((50, 160), "We also accept cash and credit card payments.")
    page3.insert_text((50, 190), "Please check with your insurance provider for specific coverage details.")

    # Save the PDF
    doc.save("data/insurance_policies.pdf")
    doc.close()
    print("✅ Created data/insurance_policies.pdf")

if __name__ == "__main__":
    create_insurance_pdf()