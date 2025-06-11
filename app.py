


from src.process_invoice_extraction import process_invoices
import os
import streamlit as st
import pandas as pd
import atexit

INPUT_DIR = "input"
if not os.path.exists(INPUT_DIR):
    os.makedirs(INPUT_DIR)
OUTPUT_DIR = "output"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
OUTPUT_CSV_FILENAME = "extracted_invoices.csv"
FINAL_CSV_PATH = os.path.join(OUTPUT_DIR, OUTPUT_CSV_FILENAME)
MAX_UPLOADS = 20
MAX_FILE_SIZE_MB = 1


# Cleans the input and output directory
def clean_dirs():
    for filename in os.listdir(OUTPUT_DIR):
        file_path = os.path.join(OUTPUT_DIR, filename)
        os.remove(file_path)
    for filename in os.listdir(INPUT_DIR):
        file_path = os.path.join(INPUT_DIR, filename)
        os.remove(file_path)

clean_dirs()
atexit.register(clean_dirs)

# --- Streamlit UI and Logic ---

st.set_page_config(page_title="Invoice Data Extractor", layout="centered")

st.title("Invoice Data Extractor")

# --- Upload PDFs Section ---
st.markdown("Upload your PDF invoices to extract structured data and download it as a CSV file.")

uploaded_files = st.file_uploader(
    "Upload Invoice PDFs",
    type="pdf",
    accept_multiple_files=True,
    help=f"Select up to {MAX_UPLOADS} PDF files, each not exceeding {MAX_FILE_SIZE_MB}MB."
)
# Save uploaded files to the input directory
if uploaded_files:
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
    if len(uploaded_files) > MAX_UPLOADS: 
            st.error(f"Error: You have uploaded {len(uploaded_files)} files. Please upload a maximum of {MAX_UPLOADS} PDFs.")
    else:
        for file_obj in uploaded_files:
            if file_obj.size / (1024*1024) > MAX_FILE_SIZE_MB:
                st.error(f"Error: File '{file_obj.name}' is too large ({file_obj.size / (1024*1024):.2f} MB). Max allowed size is {MAX_FILE_SIZE_MB} MB. Please upload files within the file size limit")
            else:
                file_path = os.path.join(INPUT_DIR, file_obj.name)
                with open(file_path, "wb") as f:
                    f.write(file_obj.getbuffer())
        st.success(f"Uploaded {len(uploaded_files)} file(s) to '{INPUT_DIR}'.")

# --- Process Invoice Section ---
if st.button("Process Invoices"):
    if not uploaded_files:
        st.error("Please upload at least 1 invoice to process.")
    else:
        with st.spinner("Processing invoices... Please wait, this may take a moment."):
            success = process_invoices(INPUT_DIR, OUTPUT_DIR, OUTPUT_CSV_FILENAME)
            if success:
              st.success("Processing Complete!")
            else:
                st.error("Invoice processing failed")


# --- Download CSV Section ---
st.markdown("---")
st.header("Download Results")

try:
    with open(FINAL_CSV_PATH, "rb") as f:
        csv_data = f.read()

    st.download_button(
        label="Download Extracted Invoices CSV",
        data=csv_data,
        file_name=OUTPUT_CSV_FILENAME,
        mime="text/csv",
        help="Click to download the CSV file containing extracted invoice data."
    )

    # Display a preview of the CSV data
    st.subheader(f"CSV Preview (First 10 Rows from {OUTPUT_CSV_FILENAME})")
    try:
        df = pd.read_csv(FINAL_CSV_PATH)
        st.dataframe(df.head(10))
    except Exception as e:
        st.warning(f"Could not display CSV preview: {e}")

except FileNotFoundError:
    st.error(f"Generated CSV file '{OUTPUT_CSV_FILENAME}' not found at '{OUTPUT_DIR}'. Please process PDFs again.")
except Exception as e:
    st.error(f"Error reading CSV for download: {e}")
