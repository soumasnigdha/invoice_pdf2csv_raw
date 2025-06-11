import numpy as np
import pandas as pd
import pdfplumber
import camelot


flipkart_bboxes = {
    "invoice_number": (413, 80, 570, 100),
    "seller_details": (4, 22, 413, 100),
    "order_details": (4, 110, 143, 225),
    "billing_address": (144, 110, 279, 225),
    "shipping_address": (280, 110, 420, 225),
    "product_details": (4, 282, 100, 430),
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


def extract_tables(pdf_path):
  stream_tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream', suppress_stdout=False)
  list_of_dfs = []
  for i, table in enumerate(stream_tables):
    df = table.df.copy()
    list_of_dfs.append(df)
  
  df = list_of_dfs[1]

  return df

def split_dataframe(columns_to_split, df):
  for target_column_name in columns_to_split:
        if target_column_name in df.columns:
            # 1. Split the target column by '\n'.
            split_parts = df[target_column_name].astype(str).str.split('\n', n=1, expand=True)

            # Check if split_parts has only one column (meaning no '\n' was found in any row)
            if split_parts.shape[1] == 1:
                # If only one column, it means all original values go to the 'right' column.
                new_col_left_values = np.full(len(df), np.nan)
                new_col_right_values = split_parts[0] 
            else:
                # If two columns, proceed as before (splitting occurred)
                # Identify rows where no newline was found (split_parts[1] will be NaN).
                no_split_mask = split_parts[1].isna()

                # 3. Prepare the new values for the 'left' (original column) and 'right' (new column).
                new_col_left_values = np.where(no_split_mask, np.nan, split_parts[0])
                new_col_right_values = np.where(no_split_mask, split_parts[0], split_parts[1])


            # Get the current list of column names and find the index of the target column.
            cols = df.columns.tolist()
            try:
                target_col_index = cols.index(target_column_name)
            except ValueError:
                print(f"Error: Column '{target_column_name}' not found in the DataFrame.")

            # Insert the new column at the correct position.
            df.insert(loc=target_col_index + 1, column='TEMP_NEW_COL', value=new_col_right_values)

            # Assign the prepared 'left' values back to the original target column.
            df[target_column_name] = new_col_left_values

            # Rename the newly inserted column.
            renaming_map = {'TEMP_NEW_COL': target_column_name+1}

            for col_idx in range(target_col_index + 1, len(cols)):
                original_shifted_col_name = cols[col_idx]
                try:
                    new_shifted_col_name = int(original_shifted_col_name) + 1
                    renaming_map[original_shifted_col_name] = new_shifted_col_name
                except ValueError:
                    pass # Keeping non-numeric column names as they are

            df = df.rename(columns=renaming_map)

        else:
            print(f"Column '{target_column_name}' not found in the DataFrame. No transformation applied.")
  return df


def index_finder(string_to_find, df):
    found_occurrences = []
    for column_name in df.columns:
        contains_string_mask = df[column_name].astype(str).str.contains(string_to_find, case=False, na=False)

        matching_row_indices_in_this_column = df.index[contains_string_mask].tolist()

        for row_idx in matching_row_indices_in_this_column:
            found_occurrences.append([row_idx, column_name])

    return found_occurrences


def product_name_extractor(df):
    # Looking for the colomn that contains "Title"
    # if index_finder("Title", df):
    match_indices = index_finder("Title", df)
    # elif index_finder("Shipping And Packaging Charges", df):
    #     match_indices = index_finder("Shipping And Packaging Charges", df)
    # Checking for the first occurance of ":" and removing everything below it including ":" row.
    title = df.iloc[4:, match_indices[0][1]]
    if title.astype(str).str.contains(":").any():
        column_match_found = title.astype(str).str.contains(":")
    elif title.astype(str).str.contains("%").any():
        column_match_found = title.astype(str).str.contains("%")
    index_to_start_removal = title[column_match_found].index[0]
    indices_to_keep = title.index[title.index < index_to_start_removal]
    product_name = " ".join(title.loc[indices_to_keep]).strip(" ")
    return product_name


def process_flipkart_invoice(pdf_path):
  
  invoice = {}

  extracted_text_output = {}
  for name, bbox in flipkart_bboxes.items():
    text = extract_text_from_bbox(pdf_path, bbox)
    # Store the extracted text using the same name (key) as the bbox
    extracted_text_output[name] = text.split("\n")
    # Dataframe for rest of extraction (camelot stream table)
    df = extract_tables(pdf_path)
    df = split_dataframe([5, 2, 1, 0], df)

  invoice["invoice_number"] = extracted_text_output['invoice_number'][0][len("Invoice Number #"):].strip()
  invoice["seller_name"] = extracted_text_output['seller_details'][1][len("Sold By: "):-2]
  invoice["seller_address"] = " ".join(extracted_text_output['seller_details'][2:-1])[len("Ship-from Address: "):-1].strip()
  invoice["gst_number"] = extracted_text_output['seller_details'][-1][len("GSTIN - "):]
  invoice["order_id"] = extracted_text_output['order_details'][1].strip()
  invoice["order_date"] = extracted_text_output['order_details'][2][len("Order Date: "):].strip()
  invoice["invoice_date"] = extracted_text_output['order_details'][3][len("Invoice Date: "):].strip()
  invoice["pan_number"] = extracted_text_output['order_details'][4][len("PAN: "):].strip()
  # invoice["corporate_identification_number"] = extracted_text_output['order_details'][5][len("CIN: "):].strip()
  invoice["bill_to_name"] = extracted_text_output["billing_address"][1].strip()
  invoice["bill_to_address"] = " ".join(extracted_text_output["billing_address"][2:-1]).strip()
  # invoice["bill_to_phone_number"] = extracted_text_output["billing_address"][-1][len("Phone: "):].strip()
  invoice["ship_to_name"] = extracted_text_output["shipping_address"][1].strip()
  invoice["ship_to_address"] = " ".join(extracted_text_output["shipping_address"][2:-1]).strip()
  # invoice["ship_to_phone_number"] = extracted_text_output["shipping_address"][-1][len("Phone: "):].strip()
  invoice["product_category"] = extracted_text_output["product_details"][0].strip()
  invoice["product_name"] = product_name_extractor(df)

  # Checking for null or ''
  if df[index_finder("Qty", df)[0][1]].isnull().any():
    rows_to_add = int(df[df[index_finder("Qty", df)[0][1]].notnull()].index.to_list()[1]) - (int(index_finder("Qty", df)[0][0]))
  if (df[index_finder("Qty", df)[0][1]].astype(str).str.strip() == '').any():
    rows_to_add = int(df[df[index_finder("Qty", df)[0][1]].astype(str).str.strip() != ''].index.to_list()[1]) - int(index_finder("Qty", df)[0][0])

  invoice["product_quantity"] = df.iloc[index_finder("Qty", df)[0][0]+ rows_to_add, index_finder("Qty", df)[0][1]]
  # invoice["product_discount_coupons"] = df.iloc[index_finder("Discounts", df)[0][0] + rows_to_add, index_finder("Discounts", df)[0][1]]
  # invoice["shipping_discount_coupons"] = df.iloc[-1, index_finder("Discounts", df)[0][1]]
  invoice["product_taxable_value"] = df.iloc[index_finder("Taxable", df)[0][0] + rows_to_add, index_finder("Taxable", df)[0][1]]
  # invoice["shipping_taxable_value"] = df.iloc[-1, index_finder("Taxable", df)[0][1]]
  invoice["product_total"] = df.iloc[index_finder("Total ₹", df)[0][0] + rows_to_add, index_finder("Total ₹", df)[0][1]]
  # invoice["shipping_total"] = df.iloc[-1, index_finder("Total ₹", df)[0][1]]

  # Checking for different kinds of GST
  if index_finder("SGST", df):
    invoice["GST"] = str(float(df.iloc[index_finder("SGST", df)[1][0] + rows_to_add, index_finder("SGST", df)[1][1]]) + float(df.iloc[index_finder("CGST", df)[1][0]+3, index_finder("CGST", df)[1][1]]))
  if index_finder("IGST", df):
    invoice["GST"] = df.iloc[index_finder("IGST", df)[1][0] + rows_to_add, index_finder("IGST", df)[1][1]]
  if index_finder("UGST", df):
    invoice["GST"] = df.iloc[index_finder("UGST", df)[1][0] + rows_to_add, index_finder("UGST", df)[1][1]]
  # invoice["grand_total"] = str(float(invoice["product_total"]) + float(invoice["shipping_total"]))

  return invoice
  

