import streamlit as st
import pytesseract
from PIL import Image
import re

st.set_page_config(page_title="Virtuals Auto-Pick Scanner", layout="centered")

st.title("⚽ Virtuals Auto-Pick Scanner")
st.caption("Upload a screenshot to get automatic match picks and exact staking advice.")

# Sidebar Settings
st.sidebar.header("Bankroll Settings")
bankroll = st.sidebar.number_input("Total Bankroll (GHS)", min_value=1.0, value=100.0, step=10.0)
kelly_fraction = st.sidebar.slider("Kelly Fractional Safety", 0.05, 1.0, 0.25, 0.05)

# Image Upload
uploaded_file = st.file_uploader("Upload SportyBet Screenshot", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Screenshot", use_column_width=True)
    
    try:
        with st.spinner("Scanning image for odds..."):
            extracted_text = pytesseract.image_to_string(image)
        
        found_odds = re.findall(r'\b\d+\.\d{2}\b', extracted_text)
        
        if found_odds and len(found_odds) >= 3:
            odd_1 = float(found_odds[0])
            odd_x = float(found_odds[1])
            odd_2 = float(found_odds[2])
        else:
            st.warning("Could not clearly read 3 odds from image. Using defaults below.")
            odd_1, odd_x, odd_2 = 1.80, 3.40, 4.20
    except Exception:
        st.warning("OCR process failed. Using default odds.")
        odd_1, odd_x, odd_2 = 1.80, 3.40, 4.20

    st.subheader("1. Scanned Match Odds")
    c1, c2, c3 = st.columns(3)
    o1 = c1.number_input("Home (1)", value=odd_1, step=0.01)
    ox = c2.number_input("Draw (X)", value=odd_x, step=0.01)
    o2 = c3.number_input("Away (2)", value=odd_2, step=0.01)

    # Implied Probabilities & Margin
    imp1, impX, imp2 = (1 / o1) * 100, (1 / ox) * 100, (1 / o2) * 100
    total_margin = (imp1 + impX + imp2) - 100
    
    prob1 = imp1 / (100 + total_margin)
    probX = impX / (100 + total_margin)
    prob2 = imp2 / (100 + total_margin)

    # Analyze all selections automatically
    options = [
        {"name": "Home Win (1)", "odd": o1, "prob": prob1},
        {"name": "Draw (X)", "odd": ox, "prob": probX},
        {"name": "Away Win (2)", "odd": o2, "prob": prob2}
    ]

    best_pick = None
    max_kelly = -1.0

    for opt in options:
        b = opt["odd"] - 1
        p = opt["prob"]
        q = 1 - p
        k_perc = ((b * p) - q) / b
        opt["kelly_perc"] = k_perc
        
        # Track the pick with the highest positive expected value/Kelly percentage
        if k_perc > max_kelly:
            max_kelly = k_perc
            best_pick = opt

    st.divider()
    st.subheader("2. Recommended Pick & Stake")

    if best_pick and max_kelly > 0:
        stake = bankroll * (max_kelly * kelly_fraction)
        st.success(f"🎯 **Best Pick:** {best_pick['name']} @ **{best_pick['odd']:.2f}**")
        st.info(f"💰 **Recommended Stake:** GHS {stake:.2f} ({(max_kelly * kelly_fraction * 100):.2f}% of bankroll)")
        st.write(f"**House Edge:** `{total_margin:.2f}%` | **Fair Probability:** `{best_pick['prob']*100:.1f}%`")
    else:
        st.error("⚠️ **No Recommended Stake:** All outcomes carry a negative expected value due to the house margin. Skip this round.")
