
import spacy #NER
import random
import string
import uuid
from datetime import datetime, timedelta
import fitz
from PIL import Image
import io
import json
import os

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    OCR_ENABLED = True
except ImportError:
    OCR_ENABLED = False
    print("pytesseract not found. OCR will be disabled for scanned PDFs.")

modelNlp = spacy.load("en_core_web_sm") #Pre-trained NLP model
entities_PII = ["PERSON", "GPE", "ORG", "DATE", "NORP", "EMAIL", "PHONE"] #pii types

def piiDetection(text):  #changed code with append
    pii = []
    doc = modelNlp(text)
    for entity in doc.ents:
        if entity.label_ in entities_PII:
            pii.append({
                "id": str(uuid.uuid4()),    #Detects pii entities and returns a list of them
                "start": entity.start_char,
                "end": entity.end_char,
                "type": entity.label_,
                "original": entity.text,
                "value": entity.text,
                "anonymized": False
            })
    return pii

def randomAnonymize(text, pii_list):
    new_text = text
    updated_pii = []
    offset = 0 #length size of pii are checked to ensure consistency when replacement
    for pii in pii_list:
        replacement = generate_random(pii["type"], pii["original"])
        start = pii["start"] + offset
        end = pii["end"] + offset
        new_text = new_text[:start] + replacement + new_text[end:] #anonymized replacement handled
        offset += len(replacement) - (end - start)
        updated_pii.append({**pii, "start": start, "end": start + len(replacement),
                            "value": replacement, "anonymized": True})
    return new_text, updated_pii

def realisticAnonymize(text, pii_list):
    new_text = text
    updated_pii = []
    offset = 0
    for pii in pii_list:
        replacement = realisticGenerate(pii["type"], pii["original"])
        start = pii["start"] + offset
        end = pii["end"] + offset
        new_text = new_text[:start] + replacement + new_text[end:]
        offset += len(replacement) - (end - start)
        updated_pii.append({**pii, "start": start, "end": start + len(replacement),
                            "value": replacement, "anonymized": True})
    return new_text, updated_pii


keySyllables = ["al","ben","cor","dan","el","fi","mor","nov","ri","tar",
             "sha","li","ka","ro","mi","ver","jo","an","le","ton"]

def combine_Syllables(min_syl=2,max_syl=3):  #to create random yet realistic pii
    num = random.randint(min_syl,max_syl)
    return "".join(random.choice(keySyllables).capitalize() if i==0 else random.choice(keySyllables) for i in range(num))

def realistic_name(): return f"{combine_Syllables()} {combine_Syllables()}"
def realistic_city(): return combine_Syllables()
def realistic_company(): return f"{combine_Syllables()} {combine_Syllables()} {random.choice(['Ltd','Inc','Solutions','Systems'])}"
def realistic_email(): return f"{combine_Syllables(1,2).lower()}.{combine_Syllables(1,2).lower()}@example.com"
def realistic_phone(): return "+44" + "".join(random.choices(string.digits, k=10))

def random_name(): return f"{random_word()} {random_word()}"
def random_city(): return random_word()
def random_company(): return random_word() + random.choice([" Ltd"," Inc"," Systems"," Solutions"])
def random_email(): return f"{random_word().lower()}@mail.com"
def random_phone(): return "+94" + "".join(random.choices(string.digits,k=9))
def random_date():
    start = datetime(1990,1,1)
    end = datetime(2022,12,31)
    return (start + timedelta(days=random.randint(0,(end-start).days))).strftime("%d %B %Y")
def random_word(): return ''.join(random.choices(string.ascii_letters,k=random.randint(5,9))).capitalize()

def generate_random(pii_type,_): #create random pii placeholders
    return {
        "PERSON": random_name,
        "ORG": random_company,
        "GPE": random_city,
        "EMAIL": random_email,
        "PHONE": random_phone,
        "DATE": random_date
    }.get(pii_type, lambda:"REDACTED")()

def realisticGenerate(pii_type,_): #create realistic pii placeholders
    return {
        "PERSON": realistic_name,
        "ORG": realistic_company,
        "GPE": realistic_city,
        "EMAIL": realistic_email,
        "PHONE": realistic_phone,
        "DATE": random_date
    }.get(pii_type, lambda:"REDACTED")()


def ocr_pdf_page(pdf_path, page_number): #used to extract text from scanned pdfs (currently on progress)
    if not OCR_ENABLED:
        return ""
    doc = fitz.open(pdf_path)
    page = doc[page_number]
    pix = page.pixmap(dpi=300)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(img)
    doc.close()
    return text


def restore_original_text(currentText, piiDetection, mapping_file): #retsore original pii through saved mappings
    if not os.path.exists(mapping_file):
        print("Mapping file not found:", mapping_file)
        return currentText

    try:
        with open(mapping_file, "r") as f:
            mapping = json.load(f)
    except Exception as e:
        print("Error reading mapping:", e)
        return currentText

    restore_lookup = {item["value"]: item["original"] for item in mapping}

    restored_text = currentText
    offset = 0
    for pii in piiDetection:
        value = pii["value"]
        if value in restore_lookup:
            replacement = restore_lookup[value]
            start = pii["start"] + offset
            end = pii["end"] + offset
            restored_text = restored_text[:start] + replacement + restored_text[end:]
            offset += len(replacement) - (end - start)

    return restored_text

modelNlp = spacy.load("en_core_web_sm") #Pre-trained NLP model
entities_PII = ["PERSON", "GPE", "ORG", "DATE", "NORP", "EMAIL", "PHONE"] #pii types

def piiDetection(text):  #changed code with append
    pii = []
    doc = modelNlp(text)
    for entity in doc.ents:
        if entity.label_ in entities_PII:
            pii.append({
                "id": str(uuid.uuid4()),    #Detects pii entities and returns a list of them
                "start": entity.start_char,
                "end": entity.end_char,
                "type": entity.label_,
                "original": entity.text,
                "value": entity.text,
                "anonymized": False
            })
    return pii

def randomAnonymize(text, pii_list):
    new_text = text
    updated_pii = []
    offset = 0 #length size of pii are checked to ensure consistency when replacement
    for pii in pii_list:
        replacement = generate_random(pii["type"], pii["original"])
        start = pii["start"] + offset
        end = pii["end"] + offset
        new_text = new_text[:start] + replacement + new_text[end:] #anonymized replacement handled
        offset += len(replacement) - (end - start)
        updated_pii.append({**pii, "start": start, "end": start + len(replacement),
                            "value": replacement, "anonymized": True})
    return new_text, updated_pii

def realisticAnonymize(text, pii_list):
    new_text = text
    updated_pii = []
    offset = 0
    for pii in pii_list:
        replacement = realisticGenerate(pii["type"], pii["original"])
        start = pii["start"] + offset
        end = pii["end"] + offset
        new_text = new_text[:start] + replacement + new_text[end:]
        offset += len(replacement) - (end - start)
        updated_pii.append({**pii, "start": start, "end": start + len(replacement),
                            "value": replacement, "anonymized": True})
    return new_text, updated_pii


keySyllables = ["al","ben","cor","dan","el","fi","mor","nov","ri","tar",
             "sha","li","ka","ro","mi","ver","jo","an","le","ton"]

def combine_Syllables(min_syl=2,max_syl=3):  #to create random yet realistic pii
    num = random.randint(min_syl,max_syl)
    return "".join(random.choice(keySyllables).capitalize() if i==0 else random.choice(keySyllables) for i in range(num))

def realistic_name(): return f"{combine_Syllables()} {combine_Syllables()}"
def realistic_city(): return combine_Syllables()
def realistic_company(): return f"{combine_Syllables()} {combine_Syllables()} {random.choice(['Ltd','Inc','Solutions','Systems'])}"
def realistic_email(): return f"{combine_Syllables(1,2).lower()}.{combine_Syllables(1,2).lower()}@example.com"
def realistic_phone(): return "+44" + "".join(random.choices(string.digits, k=10))

def random_name(): return f"{random_word()} {random_word()}"
def random_city(): return random_word()
def random_company(): return random_word() + random.choice([" Ltd"," Inc"," Systems"," Solutions"])
def random_email(): return f"{random_word().lower()}@mail.com"
def random_phone(): return "+94" + "".join(random.choices(string.digits,k=9))
def random_date():
    start = datetime(1990,1,1)
    end = datetime(2022,12,31)
    return (start + timedelta(days=random.randint(0,(end-start).days))).strftime("%d %B %Y")
def random_word(): return ''.join(random.choices(string.ascii_letters,k=random.randint(5,9))).capitalize()

def generate_random(pii_type,_): #create random pii placeholders
    return {
        "PERSON": random_name,
        "ORG": random_company,
        "GPE": random_city,
        "EMAIL": random_email,
        "PHONE": random_phone,
        "DATE": random_date
    }.get(pii_type, lambda:"REDACTED")()

def realisticGenerate(pii_type,_): #create realistic pii placeholders
    return {
        "PERSON": realistic_name,
        "ORG": realistic_company,
        "GPE": realistic_city,
        "EMAIL": realistic_email,
        "PHONE": realistic_phone,
        "DATE": random_date
    }.get(pii_type, lambda:"REDACTED")()


def ocr_pdf_page(pdf_path, page_number): #used to extract text from scanned pdfs (currently on progress)
    if not OCR_ENABLED:
        return ""
    doc = fitz.open(pdf_path)
    page = doc[page_number]
    pix = page.pixmap(dpi=300)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(img)
    doc.close()
    return text


def restore_original_text(currentText, piiDetection, mapping_file): #retsore original pii through saved mappings
    if not os.path.exists(mapping_file):
        print("Mapping file not found:", mapping_file)
        return currentText

    try:
        with open(mapping_file, "r") as f:
            mapping = json.load(f)
    except Exception as e:
        print("Error reading mapping:", e)
        return currentText

    restore_lookup = {item["value"]: item["original"] for item in mapping}

    restored_text = currentText
    offset = 0
    for pii in piiDetection:
        value = pii["value"]
        if value in restore_lookup:
            replacement = restore_lookup[value]
            start = pii["start"] + offset
            end = pii["end"] + offset
            restored_text = restored_text[:start] + replacement + restored_text[end:]
            offset += len(replacement) - (end - start)

    return restored_text

