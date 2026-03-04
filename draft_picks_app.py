import streamlit as st
import pandas as pd
import os

# --- PATH SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
seeds_file = os.path.join(script_dir, "team_seeds.csv")
rosters_file = os.path.join(script_dir, "team_rosters.xlsx")
picks_file = os.path.join(script_dir, "picks.xlsx")

# --- APP LAYOUT ---
st.set_page_config(page_title="NCAA Player Pool", page_icon="🏀", layout="wide")

# Top Header with Reset Button
col_header, col_reset = st.columns([5, 1])
with col_header:
    st.title("🏀 2026 NCAA Tournament Player Pool")
with col_reset:
    # Adding the Reset Button
    if st.button("🔄 Reset Form", use_container_width=True):
        st.rerun()

st.markdown("### Rules: Select 8 players total. Each player must come from a unique Seed (1-16).")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    if not os.path.exists(seeds_file) or not os.path.exists(rosters_file):
        return None, None
    
    seeds_df = pd.read_csv(seeds_file)
    seeds_df['Seed'] = seeds_df['Seed'].astype(int)
    rosters_df = pd.read_excel(rosters_file)
    return seeds_df, rosters_df

seeds_df, rosters_df = load_data()

if seeds_df is None or rosters_df is None:
    st.error("Missing data files! Ensure 'team_seeds.csv' and 'team_rosters.xlsx' are in the script folder.")
    st.stop()

# --- USER INFO ---
user_name = st.text_input("Enter Your Name / Team Name", placeholder="e.g., Mike's Mavs")
st.divider()

# --- SELECTION SLOTS ---
user_selections = []
chosen_seeds = []

# Create a grid layout
cols = st.columns(4) 
for i in range(1, 9):
    col_idx = (i-1) % 4
    with cols[col_idx]:
        st.subheader(f"Player {i}")
        
        seed_options = sorted(seeds_df['Seed'].unique())
        selected_seed = st.selectbox(
            f"Select Seed for Slot {i}", 
            options=seed_options, 
            index=min(i-1, len(seed_options)-1), 
            key=f"seed_slot_{i}"
        )
        chosen_seeds.append(selected_seed)
        
        teams_in_seed = sorted(seeds_df[seeds_df['Seed'] == selected_seed]['Team'].unique())
        selected_team = st.selectbox(
            f"Select Team (Seed {selected_seed})", 
            options=teams_in_seed,
            key=f"team_slot_{i}"
        )
        
        players_in_team = sorted(rosters_df[rosters_df['Team'] == selected_team]['Player Name'].unique())
        selected_player = st.selectbox(
            f"Select Player from {selected_team}", 
            options=players_in_team,
            key=f"player_slot_{i}"
        )
        
        user_selections.append({
            "Slot": i,
            "Seed": selected_seed,
            "Team": selected_team,
            "Player": selected_player
        })
        st.write("---")

# --- SIDEBAR STATUS & VALIDATION ---
st.sidebar.header("Draft Status")

# 1. Cleaner Duplicate Check
duplicate_seeds = [seed for seed in set(chosen_seeds) if chosen_seeds.count(seed) > 1]
is_valid = True

if not user_name:
    st.sidebar.warning("⚠️ Enter a Name to Submit")
    is_valid = False

if duplicate_seeds:
    # Updated message to be cleaner per your request
    st.sidebar.error("❌ Duplicate Seeds detected") 
    st.sidebar.info("Please ensure each player is from a different seed number.")
    is_valid = False
else:
    st.sidebar.success("✅ Seeds are unique!")

# 2. Submit Button Logic
if st.button("Submit My Draft Picks", disabled=not is_valid, use_container_width=True, type="primary"):
    submission_data = {"Contestant": user_name}
    for pick in user_selections:
        submission_data[f"Slot_{pick['Slot']}_Player"] = pick['Player']
        submission_data[f"Slot_{pick['Slot']}_Team"] = pick['Team']
        submission_data[f"Slot_{pick['Slot']}_Seed"] = pick['Seed']

    new_picks_df = pd.DataFrame([submission_data])

    if os.path.exists(picks_file):
        existing_picks = pd.read_excel(picks_file)
        final_df = pd.concat([existing_picks, new_picks_df], ignore_index=True)
    else:
        final_df = new_picks_df

    final_df.to_excel(picks_file, index=False)
    
    st.success(f"Successfully submitted! Your team '{user_name}' is saved.")
    st.balloons()

# Sidebar Preview
st.sidebar.markdown("### Your Lineup Preview")
preview_data = [{"Seed": p["Seed"], "Player": p["Player"]} for p in user_selections]
st.sidebar.table(preview_data)
