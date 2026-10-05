import streamlit as st
import easyocr
from PIL import Image
import numpy as np
import re

st.set_page_config(page_title="Virtuals Screenshot Scanner", layout="centered")

st.title("⚽ Virtuals Screenshot Scanner & Staking Calculator")
st.caption("Upload a SportyBet virtual screenshot to extract odds and compute staking rules.")

# Initialize EasyOCR reader
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

reader = load_ocr()

# Sidebar Staking Settings
st.sidebar.header("Bankroll Settings")
bankroll = st.sidebar.number_input("Total Bankroll (GHS)", min_value=1.0, value=100.0, step=10.0)
kelly_fraction = st.sidebar.slider("Kelly Fractional Safety", 0.05, 1.0, 0.25, 0.05)

# Image Upload
uploaded_file = st.file_uploader("Upload SportyBet Screenshot", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Screenshot", use_column_width=True)
    
    with st.spinner("Extracting text from image..."):
        img_np = np.array(image)
        results = reader.readtext(img_np)
        extracted_text = " ".join([res[1] for res in results])
    
    # Extract decimal numbers (odds)
    found_odds = re.findall(r'\b\d+\.\d{2}\b', extracted_text)
    
    st.subheader("1. Extracted Odds Detected")
    if found_odds:
        st.write(f"Detected odds in image: `{found_odds}`")
        
        # Take first 3 detected odds as Home, Draw, Away if available
        if len(found_odds) >= 3:
            odd_1 = float(found_odds[0])
            odd_x = float(found_odds[1])
            odd_2 = float(found_odds[2])
        else:
            odd_1, odd_x, odd_2 = 1.80, 3.40, 4.20
    else:
        st.warning("Could not automatically detect decimal odds. Enter them manually below.")
        odd_1, odd_x, odd_2 = 1.80, 3.40, 4.20

    st.subheader("2. Confirm Match Odds (1X2)")
    c1, c2, c3 = st.columns(3)
    o1 = c1.number_input("Home (1)", value=odd_1, step=0.01)
    ox = c2.number_input("Draw (X)", value=odd_x, step=0.01)
    o2 = c3.number_input("Away (2)", value=odd_2, step=0.01)

    # Calculations
    imp1 = (1 / o1) * 100
    impX = (1 / ox) * 100
    imp2 = (1 / o2) * 100
    total_margin = (imp1 + impX + imp2) - 100
    
    prob1 = imp1 / (100 + total_margin)
    probX = impX / (100 + total_margin)
    prob2 = imp2 / (100 + total_margin)

    st.divider()
    st.subheader("3. House Margin & Probabilities")
    st.write(f"**House Edge / Margin:** `{total_margin:.2f}%`")

    st.subheader("4. Staking Recommendation")
    pick = st.radio("Selection to Back", ("Home (1)", "Draw (X)", "Away (2)"))

    if pick == "Home (1)":
        b, p = o1 - 1, prob1
    elif pick == "Draw (X)":
        b, p = ox - 1, probX
    else:
        b, p = o2 - 1, prob2

    q = 1 - p
    kelly_perc = ((b * p) - q) / b

    if kelly_perc <= 0:
        st.error("⚠️️ Negative Expected Value (EV): Avoid betting on this pick due to house edge.")
    else:
        stake = bankroll * (kelly_perc * kelly_fraction)
        st.success(f"💡 Recommended Stake: **GHS {stake:.2f}** ({kelly_perc * kelly_fraction * 100:.2f}% of bankroll)")
