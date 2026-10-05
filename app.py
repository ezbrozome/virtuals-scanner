import streamlit as st
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import re

st.set_page_config(page_title="Virtuals Value Scanner", layout="centered")

st.title("⚽ Virtuals Strict Value Scanner")
st.caption("Scans virtual match rows and highlights only high-probability, low-margin picks.")

# Sidebar Settings
st.sidebar.header("Bankroll Settings")
bankroll = st.sidebar.number_input("Total Bankroll (GHS)", min_value=1.0, value=100.0, step=10.0)
min_prob = st.sidebar.slider("Minimum Win Probability (%)", 50, 85, 60, 5)
max_picks = st.sidebar.slider("Max Accumulator Games", 1, 4, 2, 1)

uploaded_file = st.file_uploader("Upload SportyBet Screenshot", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    raw_image = Image.open(uploaded_file)
    st.image(raw_image, caption="Uploaded Screenshot", use_container_width=True)
    
    # Image contrast boost for Tesseract OCR
    processed_image = ImageOps.grayscale(raw_image)
    enhancer = ImageEnhance.Contrast(processed_image)
    processed_image = enhancer.enhance(2.0)
    
    games_found = []
    
    try:
        with st.spinner("Scanning for match odds..."):
            extracted_text = pytesseract.image_to_string(processed_image, config='--psm 6')
        
        lines = extracted_text.split('\n')
        for line in lines:
            odds_in_line = re.findall(r'\b\d+\.\d{2}\b', line)
            if len(odds_in_line) >= 3:
                try:
                    o1, ox, o2 = float(odds_in_line[0]), float(odds_in_line[1]), float(odds_in_line[2])
                    if all(1.01 <= o <= 30.0 for o in [o1, ox, o2]):
                        games_found.append({"game_id": len(games_found) + 1, "o1": o1, "ox": ox, "o2": o2})
                except ValueError:
                    continue
    except Exception:
        st.error("Error running OCR scan.")

    st.subheader(f"1. Matches Detected: {len(games_found)}")
    
    if not games_found:
        st.warning("No clear odds rows detected. Check image quality.")
    else:
        qualified_picks = []
        
        for game in games_found:
            o1, ox, o2 = game["o1"], game["ox"], game["o2"]
            imp1, impX, imp2 = (1 / o1) * 100, (1 / ox) * 100, (1 / o2) * 100
            margin = (imp1 + impX + imp2) - 100
            
            p1 = (imp1 / (100 + margin)) * 100
            pX = (impX / (100 + margin)) * 100
            p2 = (imp2 / (100 + margin)) * 100

            options = [
                {"selection": "Home Win (1)", "odd": o1, "prob": p1},
                {"selection": "Draw (X)", "odd": ox, "prob": pX},
                {"selection": "Away Win (2)", "odd": o2, "prob": p2}
            ]

            # Find safest choice above probability threshold
            best = max(options, key=lambda x: x["prob"])
            
            if best["prob"] >= min_prob:
                qualified_picks.append({
                    "game_id": game["game_id"],
                    "selection": best["selection"],
                    "odd": best["odd"],
                    "prob": best["prob"],
                    "margin": margin
                })

        st.divider()
        st.subheader("2. High-Probability Selections")

        if not qualified_picks:
            st.error("⚠️ No games in this round meet your minimum safety threshold. Recommended action: SKIP THIS ROUND.")
        else:
            sorted_picks = sorted(qualified_picks, key=lambda x: x["prob"], reverse=True)[:max_picks]
            
            total_odd = 1.0
            for rank, pick in enumerate(sorted_picks, start=1):
                total_odd *= pick["odd"]
                st.success(
                    f"Pick #{rank} (Match {pick['game_id']}): {pick['selection']} @ {pick['odd']:.2f} "
                    f"| Calculated Probability: {pick['prob']:.1f}%"
                )

            st.info(f"📊 Combined Odds: {total_odd:.2f}")
            stake = bankroll * 0.02
            st.write(f"💰 Safe Stake (2% Bankroll): GHS {stake:.2f}")
