import os
import pdfplumber
import pandas as pd
import camelot

amazon_bboxes = {
    
    "bill_to_name": (313, 190, 558, 250)
    
}

def extract_text_from_bbox(pdf_path, bounding_box):
    """
    Extracts text from a specified bounding box within a PDF page.
    """
    extracted_text = None
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]  # Assuming data is on the first page

        # Use the extract_text() method with the bbox parameter
        cropped_page = page.crop(bounding_box)
        extracted_text = cropped_page.extract_text()
            
    return extracted_text

def extract_table(pdf_path):
    stream_tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream', suppress_stdout=False)
    list_of_dfs = []
    for i, table in enumerate(stream_tables):
        df = table.df.copy()
        list_of_dfs.append(df)

    df = list_of_dfs[0]
    return df

def process_amazon_invoice(pdf_path):
    invoice = {}
    df = extract_table(pdf_path)
    seller_details = " ".join(df[0])
    buyer_details = " ".join(df[1])

    invoice["seller_name"], invoice["seller_address"] = [item.strip() for item in seller_details.split("Sold By :", 1)[1].split("PAN No:", 1)[0].strip().split("*")]
    invoice["pan_number"] = seller_details.split("PAN No:", 1)[1].split("GST Registration No:", 1)[0].strip()
    invoice["gst_number"] = seller_details.split("GST Registration No:", 1)[1].split("Order Number:", 1)[0][:15].strip()
    invoice["order_id"] = seller_details.split("Order Number:", 1)[1].split("Order Date:", 1)[0].strip()
    invoice["order_date"] = seller_details.split("Order Date:", 1)[1].strip()
    invoice["bill_to_name"] = df[1][1].strip()
    invoice["bill_to_address"] = buyer_details.split(invoice['bill_to_name'], 1)[1].split("State/UT Code:", 1)[0].strip()
    ship_to_name = extract_text_from_bbox(pdf_path, amazon_bboxes["bill_to_name"]).split("Shipping Address :", 1)[1].split("\n")[1:]
    invoice["ship_to_address"] = [buyer_details.split(string)[1] for string in ship_to_name][1].split("State/UT Code:", 1)[0].strip()
    invoice["ship_to_name"] = ship_to_name[1]
    invoice["invoice_number"] = buyer_details.split("Invoice Details :", 1)[1].split("Invoice Date :", 1)[0].strip()
    invoice["invoice_date"] = buyer_details.split("Invoice Date :", 1)[1].strip()

    all_extracted_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        tables = page.extract_tables()
    if tables:
        for i, table_data in enumerate(tables):
                df = pd.DataFrame(table_data[1:], columns=table_data[0])
                all_extracted_tables.append(df)
    
    invoice["product_name"] = " ".join(all_extracted_tables[0]["Description"][0].split("HSN:", 1)[0].split("\n")).strip()
    invoice["product_category"] = None
    invoice["product_taxable_value"] = all_extracted_tables[0]["Net\nAmount"][0].strip("₹")
    invoice["product_taxable_value"]
    invoice["GST"] = str(pd.to_numeric(all_extracted_tables[0]["Tax\nAmount"].astype(str).str.strip("₹"), errors='coerce').sum())
    invoice["product_quantity"] = all_extracted_tables[0]["Qty"][0]
    invoice["product_total"] = all_extracted_tables[0]["Total\nAmount"][0].strip("₹")

    return invoice

