import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import os

# --- PATH SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
seeds_file = os.path.join(script_dir, "team_seeds.csv")
rosters_file = os.path.join(script_dir, "team_rosters.xlsx")
# This is the file you will upload to GitHub to show standings
results_file = os.path.join(script_dir, "updated_picks_per_round.xlsx")

st.set_page_config(page_title="NCAA Player Pool", page_icon="🏀", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    seeds_df = pd.read_csv(seeds_file)
    seeds_df['Seed'] = seeds_df['Seed'].astype(int)
    rosters_df = pd.read_excel(rosters_file)
    return seeds_df, rosters_df

seeds_df, rosters_df = load_data()

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- APP TABS ---
tab1, tab2 = st.tabs(["📝 Enter Draft Picks", "🏆 Leaderboard"])

with tab1:
    col_header, col_reset = st.columns([5, 1])
    with col_header:
        st.title("Draft Your Team")
    with col_reset:
        if st.button("🔄 Reset Form"):
            st.rerun()

    user_name = st.text_input("Enter Your Name / Team Name")
    
    user_selections = []
    chosen_seeds = []

    # Row-based layout to fix the 1-5-2-6 mobile bug
    for row_range in [range(1, 5), range(5, 9)]:
        cols = st.columns(4)
        for i in row_range:
            with cols[i - (row_range.start)]:
                st.subheader(f"Player {i}")
                selected_seed = st.selectbox(f"Seed", options=sorted(seeds_df['Seed'].unique()), index=i-1, key=f"s{i}")
                chosen_seeds.append(selected_seed)
                
                teams = sorted(seeds_df[seeds_df['Seed'] == selected_seed]['Team'].unique())
                selected_team = st.selectbox(f"Team", options=teams, key=f"t{i}")
                
                players = sorted(rosters_df[rosters_df['Team'] == selected_team]['Player Name'].unique())
                selected_player = st.selectbox(f"Player", options=players, key=f"p{i}")
                
                user_selections.append({"Slot": i, "Seed": selected_seed, "Team": selected_team, "Player": selected_player})
        st.divider()

    # Validation
    duplicate_seeds = [s for s in set(chosen_seeds) if chosen_seeds.count(s) > 1]
    is_valid = True
    if not user_name: is_valid = False
    if duplicate_seeds: is_valid = False

    if st.button("Submit My Draft Picks", disabled=not is_valid, type="primary"):
        # Create a dictionary for the new entry
        new_entry = {"Contestant": user_name}
        for p in user_selections:
            new_entry[f"Slot_{p['Slot']}_Player"] = p['Player']
            new_entry[f"Slot_{p['Slot']}_Team"] = p['Team']
            new_entry[f"Slot_{p['Slot']}_Seed"] = p['Seed']
        
        # --- IMPROVED APPEND LOGIC ---
        try:
            # 1. Read existing data
            # Use ttl=0 to force a fresh read from Google (no caching)
            existing_data = conn.read(worksheet="Sheet1", ttl=0)
            
            # 2. Filter out any completely empty rows that might confuse pandas
            existing_data = existing_data.dropna(how="all")
            
            # 3. Create a DataFrame for the new row
            new_row_df = pd.DataFrame([new_entry])
            
            # 4. Concatenate
            updated_df = pd.concat([existing_data, new_row_df], ignore_index=True)
            
            # 5. Update the sheet
            conn.update(worksheet="Sheet1", data=updated_df)
            
            st.success(f"Successfully submitted! Good luck, {user_name}!")
            st.balloons()
            
        except Exception as e:
            st.error(f"Error submitting to Google Sheets: {e}")

with tab2:
    st.title("🏆 Current Standings")
    
    try:
        # Read the 'Leaderboard' tab from Google Sheets
        # ttl=0 ensures it doesn't show old data to users
        standings_df = conn.read(worksheet="Leaderboard", ttl=0)
        
        if not standings_df.empty:
            # Display a nice gold/silver/bronze highlight for the top 3
            st.dataframe(
                standings_df.sort_values(by="Total", ascending=False), 
                use_container_width=True,
                hide_index=True
            )
            st.caption("Standings update automatically as games are processed.")
        else:
            st.info("Scores will appear here once the tournament begins!")
            
    except Exception as e:
        st.info("The leaderboard is being initialized. Check back shortly!")
