import streamlit as st
import pytesseract
from PIL import Image
import re

st.set_page_config(page_title="Virtuals Multi-Game Scanner", layout="centered")

st.title("⚽ Virtuals Multi-Game Scanner")
st.caption("Scan full match lists and automatically select up to 4 top picks.")

# Sidebar Settings
st.sidebar.header("Bankroll Settings")
bankroll = st.sidebar.number_input("Total Bankroll (GHS)", min_value=1.0, value=100.0, step=10.0)
kelly_fraction = st.sidebar.slider("Kelly Fractional Safety", 0.05, 1.0, 0.25, 0.05)
max_picks = st.sidebar.slider("Maximum Games to Pick", 1, 4, 4, 1)

# Image Upload
uploaded_file = st.file_uploader("Upload SportyBet Screenshot", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Screenshot", use_column_width=True)
    
    games_found = []
    
    try:
        with st.spinner("Scanning image for match rows..."):
            extracted_text = pytesseract.image_to_string(image)
        
        # Split line by line to keep each match row separate
        lines = extracted_text.split('\n')
        
        for line in lines:
            # Find decimal odds (e.g., 1.72, 4.11, 4.44)
            odds_in_line = re.findall(r'\b\d+\.\d{2}\b', line)
            
            # Valid match row must have at least 3 odds (1, X, 2)
            if len(odds_in_line) >= 3:
                try:
                    o1 = float(odds_in_line[0])
                    ox = float(odds_in_line[1])
                    o2 = float(odds_in_line[2])
                    
                    # Filter out unrealistic values/GUI noise
                    if all(1.01 <= o <= 30.0 for o in [o1, ox, o2]):
                        games_found.append({"game_id": len(games_found) + 1, "o1": o1, "ox": ox, "o2": o2})
                except ValueError:
                    continue
                    
    except Exception:
        st.error("Error processing OCR scan.")

    st.subheader(f"1. Detected Games ({len(games_found)})")
    
    if not games_found:
        st.warning("No valid match rows detected automatically. Try uploading a clearer screenshot.")
    else:
        analyzed_picks = []
        
        for game in games_found:
            o1, ox, o2 = game["o1"], game["ox"], game["o2"]
            
            # Calculate implied probabilities and margin
            imp1, impX, imp2 = (1 / o1) * 100, (1 / ox) * 100, (1 / o2) * 100
            total_margin = (imp1 + impX + imp2) - 100
            
            prob1 = imp1 / (100 + total_margin)
            probX = impX / (100 + total_margin)
            prob2 = imp2 / (100 + total_margin)

            options = [
                {"name": "Home Win (1)", "odd": o1, "prob": prob1},
                {"name": "Draw (X)", "odd": ox, "prob": probX},
                {"name": "Away Win (2)", "odd": o2, "prob": prob2}
            ]

            best_opt = None
            max_k = -1.0

            for opt in options:
                b = opt["odd"] - 1
                p = opt["prob"]
                q = 1 - p
                k_perc = ((b * p) - q) / b
                opt["kelly_perc"] = k_perc
                
                if k_perc > max_k:
                    max_k = k_perc
                    best_opt = opt

            analyzed_picks.append({
                "game_id": game["game_id"],
                "odds_str": f"1: {o1} | X: {ox} | 2: {o2}",
                "best_pick": best_opt["name"],
                "pick_odd": best_opt["odd"],
                "margin": total_margin,
                "kelly_perc": max_k,
                "fair_prob": best_opt["prob"]
            })

        # Display raw scanned games table
        table_data = [
            {"Game #": g["game_id"], "Odds Row (1 - X - 2)": g["odds_str"], "Margin": f"{g['margin']:.2f}%"}
            for g in analyzed_picks
        ]
        st.dataframe(table_data, use_container_width=True)

        st.divider()
        st.subheader(f"2. Top Recommended Picks (Max {max_picks})")

        # Sort games by safest/highest expected value margin score
        sorted_picks = sorted(analyzed_picks, key=lambda x: x["margin"])[:max_picks]

        total_acc_odd = 1.0
        for rank, pick in enumerate(sorted_picks, start=1):
            total_acc_odd *= pick["pick_odd"]
            st.success(
                f"**Pick #{rank} (Match {pick['game_id']}):** {pick['best_pick']} @ **{pick['pick_odd']:.2f}** "
                f"*(Margin: {pick['margin']:.2f}% | Fair Prob: {pick['fair_prob']*100:.1f}%)*"
