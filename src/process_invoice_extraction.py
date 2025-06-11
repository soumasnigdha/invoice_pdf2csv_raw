import os
import pandas as pd
from src.flipkart_invoice_extraction import process_flipkart_invoice
from src.amazon_invoice_extraction import process_amazon_invoice

def process_invoices(input_dir, output_dir, csv_file_name):
    pdf_files_flipkart = []
    pdf_files_amazon = []

    invoices = []
    for filename in os.listdir(input_dir):
            # Check if a file contains "flipkart"
            if 'flipkart' in filename.lower():
                full_file_path = os.path.join(input_dir, filename)
                pdf_files_flipkart.append(full_file_path)

    for pdf_path in pdf_files_flipkart:
        invoices.append(process_flipkart_invoice(pdf_path))

    for filename in os.listdir(input_dir):
        # Check if a file contains "amazon"
        if 'amazon' in filename.lower():
            full_file_path = os.path.join(input_dir, filename)
            pdf_files_amazon.append(full_file_path)

    for pdf_path in pdf_files_amazon:
        invoices.append(process_amazon_invoice(pdf_path))

    invoice_df = pd.DataFrame(invoices)

    # Writing the invoice dataframe to csv
    os.makedirs(output_dir, exist_ok=True)
    invoice_df.to_csv(os.path.join(output_dir, csv_file_name), index=False, encoding='utf-8')
    if invoices:
        return True
    else:
            print("\n--- No data extracted to write to CSV ---")
            return False
