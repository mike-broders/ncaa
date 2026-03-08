import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import os
import datetime
import pytz

# --- PATH SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
seeds_file = os.path.join(script_dir, "team_seeds.csv")
rosters_file = os.path.join(script_dir, "team_rosters.xlsx")

st.set_page_config(page_title="2026 NCAA Men's Player Pool", page_icon="🏀", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- DATA LOADING ---
@st.cache_data(ttl=120)
def load_all_app_data():
    seeds_df = pd.read_csv(seeds_file)
    seeds_df['Seed'] = seeds_df['Seed'].astype(int)
    rosters_df = pd.read_excel(rosters_file)
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    try:
        # Load Picks
        picks_df = conn.read(worksheet="Sheet1", ttl=0)
        picks_df.columns = picks_df.columns.str.strip()
        
        # Load Leaderboard
        leaderboard_df = conn.read(worksheet="Leaderboard", ttl=0)
        leaderboard_df.columns = leaderboard_df.columns.str.strip()

        # Load Player Stats
        player_stats_df = conn.read(worksheet="PlayerStats", ttl=0)
        player_stats_df.columns = player_stats_df.columns.str.strip()
        
    except Exception as e:
        st.error(f"Error reading Google Sheets: {e}")
        picks_df = pd.DataFrame()
        leaderboard_df = pd.DataFrame()
        player_stats_df = pd.DataFrame()

    return seeds_df, rosters_df, picks_df, leaderboard_df, player_stats_df

# Execute the load
seeds_df, rosters_df, picks_df, leaderboard_df, player_stats_df = load_all_app_data()

# --- APP TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📝 Enter Player Picks", "🏆 Leaderboard", "📊 Player Stats", "📊 View Submissions & Stats"])

# 1. Set your deadline (Year, Month, Day, Hour, Minute)
# Example: March 19, 2026, at 11:00 AM Central
deadline = datetime.datetime(2026, 3, 1, 11, 0, 0)

# 2. Define Timezones (Ensures the server time matches your time)
central = pytz.timezone('US/Central')
deadline = central.localize(deadline)
now = datetime.datetime.now(central)

with tab1:
    if now > deadline:
        # --- THE LOCKDOWN MESSAGE ---
        st.error("🔒 Player selection is now CLOSED.")
        st.subheader("The tournament has tipped off!")
        st.write("Submissions are no longer being accepted. Head over to the **Leaderboard** tab to track the scores!")
        
    else:
        # --- THE ORIGINAL SELECTION FORM ---
        # (Put your current selection loop and submit button code here)
        st.info(f"⏳ Player selection is OPEN! Submissions close at {deadline.strftime('%I:%M %p on %m/%d/%Y')}")
        col_header, col_reset = st.columns([5, 1])
        with col_header:
            st.title("🏀 2026 NCAA Men's Tournament Player Pool")
        with col_reset:
            if st.button("🔄 Reset Form"):
                st.rerun()

        st.markdown("""
        ### RULES:
        * **Select 8 players** to maximize your point total.
        * Each selected player must come from a **unique seed (1-16)**.
        * You may select a player from teams participating in the First Four round, but points scored in the First Four games **will not count** toward your total.
        * The person with the highest point total at the conclusion of the tournament wins.
        """)

        st.link_button("Go to Women's Tournament Pool 🏀", "https://teletraan1.com/ncaawbbplayerpool/")

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
        st.sidebar.header("Selection Status")
        
        # Check for Duplicate Seeds
        duplicate_seeds = [seed for seed in set(chosen_seeds) if chosen_seeds.count(seed) > 1]
        is_valid = True

        if not user_name:
            st.sidebar.warning("⚠️ Enter a Name to Submit")
            is_valid = False

        if duplicate_seeds:
            st.sidebar.error(f"❌ Duplicate Seeds detected")
            st.sidebar.info("Each of your 8 players must come from a different seed.")
            is_valid = False
        else:
            st.sidebar.success("✅ Seeds are unique!")

        # THE SUBMIT BUTTON (Connected to Google Sheets)
        if st.button("Submit My Player Picks", disabled=not is_valid, use_container_width=True, type="primary"):
            with st.spinner("Submitting to Google Sheets..."):
                try:
                    # 1. Prepare the data row
                    new_entry = {"Contestant": user_name}
                    for p in user_selections:
                        new_entry[f"Slot_{p['Slot']}_Player"] = p['Player']
                        new_entry[f"Slot_{p['Slot']}_Team"] = p['Team']
                        new_entry[f"Slot_{p['Slot']}_Seed"] = p['Seed']
                    
                    # 2. Read existing data (ttl=0 ensures no caching issues)
                    existing_data = conn.read(worksheet="Sheet1", ttl=0)
                    existing_data = existing_data.dropna(how="all")
                    
                    # 3. Combine and Update
                    updated_df = pd.concat([existing_data, pd.DataFrame([new_entry])], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=updated_df)
                    
                    st.success(f"🎉 Successfully submitted! Good luck, {user_name}!")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"Error submitting to Google Sheets: {e}")
                
with tab2:
    st.title("🏆 Current Standings")
    try:
        # 1. Read the sheet (ttl=0 ensures we see updates immediately on refresh)
        df_leaderboard = conn.read(worksheet="Leaderboard", ttl=0)
        
        if not df_leaderboard.empty:
            # 2. Extract timestamp from the very first header
            timestamp_str = str(df_leaderboard.columns[0])
            st.info(f"🕒 {timestamp_str}")
            
            # 3. Fix Headers: Row 0 actually contains our "real" headers (Contestant, Total, etc.)
            actual_data = df_leaderboard.copy()
            actual_data.columns = actual_data.iloc[0]
            actual_data = actual_data[1:].reset_index(drop=True)
            
            # 4. Clean Column Names (Force to string to avoid JSON errors)
            actual_data.columns = [str(c).strip() for c in actual_data.columns]
            
            # 5. Data Type Cleanup (Convert numbers, then to object for Streamlit safety)
            actual_data = actual_data.apply(pd.to_numeric, errors='ignore')
            
            # 6. Sorting (Optional: ensures leader is at the top)
            if 'Total' in actual_data.columns:
                actual_data = actual_data.sort_values(by='Total', ascending=False)
            
            # 7. Final Display
            st.dataframe(
                actual_data.astype(object), 
                use_container_width=True, 
                hide_index=True
            )
            
    except Exception as e:
        st.error(f"Leaderboard Error: {e}")

with tab3:
    st.title("📊 Individual Player Points")
    try:
        df_stats = conn.read(worksheet="PlayerStats", ttl=0)
        
        if not df_stats.empty:
            st.info(f"🕒 {str(df_stats.columns[0])}")
            
            actual_stats = df_stats.copy()
            actual_stats.columns = actual_stats.iloc[0]
            actual_stats = actual_stats[1:].reset_index(drop=True)
            
            # --- THE FIX: FORCE COLUMN NAMES & DATA TO WEB-SAFE TYPES ---
            actual_stats.columns = [str(c) for c in actual_stats.columns]
            
            actual_stats = actual_stats.apply(pd.to_numeric, errors='ignore')
            
            if "Total" in actual_stats.columns:
                actual_stats = actual_stats.sort_values(by="Total", ascending=False)
            
            # Final conversion to standard objects for JSON safety
            actual_stats = actual_stats.astype(object)

            st.dataframe(actual_stats, use_container_width=True, hide_index=True)
            
    except Exception as e:
        st.error(f"Stats Error: {e}")

with tab4:
    st.title("📝 Contestant Rosters & Live Stats")
    
    # Men's Tournament Tip-off for 2026
    # MENS_DEADLINE = datetime.datetime(2026, 3, 19, 12, 0)
    # now = datetime.datetime.now()

    if now < deadline:
        st.info(f"🔒 Roster stats are hidden until the tournament begins ({deadline.strftime('%I:%M %p on %m/%d')}).")
    else:
        # Match your header: 'Contestant'
        if not picks_df.empty and 'Contestant' in picks_df.columns:
            contestants = [c for c in picks_df['Contestant'].unique() if str(c).strip() != ""]
            selected_user = st.selectbox("Select a Contestant:", ["All"] + contestants, key="mens_roster_select")
            display_list = contestants if selected_user == "All" else [selected_user]

            stat_columns = ['1st Round', '2nd Round', 'Sweet 16', 'Elite 8', 'Final Four', "Nat'l Champ", 'Total']

            for user in display_list:
                with st.expander(f"👤 {user}'s Live Roster", expanded=(selected_user != "All")):
                    user_row = picks_df[picks_df['Contestant'] == user].iloc[0]
                    user_players = []
                    
                    for i in range(1, 9):
                        p_name = user_row.get(f"Slot_{i}_Player")
                        
                        if p_name and str(p_name).strip() != "":
                            # 1. Clean the name for the table display
                            display_name = str(p_name).strip()
                            
                            # 2. Fix the Seed (Clean integer)
                            try:
                                clean_seed = int(float(user_row.get(f"Slot_{i}_Seed", 0)))
                            except:
                                clean_seed = "-"

                            player_entry = {
                                "Player": display_name,
                                "Team": user_row.get(f"Slot_{i}_Team", "N/A"),
                                "Seed": clean_seed
                            }

                            if not player_stats_df.empty and 'Player Name' in player_stats_df.columns:
                                # 3. THE HEAVY DUTY LOOKUP
                                # We lowercase both sides and strip them to ensure "walter clayton jr." == "Walter Clayton Jr."
                                search_name = display_name.lower().strip()
                                
                                # Create a temporary series for matching
                                match_mask = player_stats_df['Player Name'].astype(str).str.lower().str.strip() == search_name
                                p_stats = player_stats_df[match_mask]
                                
                                if not p_stats.empty:
                                    for col in stat_columns:
                                        if col in p_stats.columns:
                                            # Ensure we handle empty strings or weird characters in the stats
                                            val = p_stats.iloc[0][col]
                                            player_entry[col] = pd.to_numeric(val, errors='coerce') or 0
                                        else:
                                            player_entry[col] = 0
                                else:
                                    # DEBUG: If no match is found, we'll mark the points as 0
                                    for col in stat_columns:
                                        player_entry[col] = 0
                            else:
                                for col in stat_columns:
                                    player_entry[col] = 0
                            
                            user_players.append(player_entry)
                    
                    if user_players:
                        df_display = pd.DataFrame(user_players)
                        
                        # Summary Row
                        summary_data = {"Player": "**ROSTER TOTALS**", "Team": "", "Seed": ""}
                        for col in stat_columns:
                            summary_data[col] = df_display[col].sum()
                        
                        df_with_total = pd.concat([df_display, pd.DataFrame([summary_data])], ignore_index=True)

                        # Styling
                        def style_roster(styler):
                            if 'Total' in df_with_total.columns:
                                styler.background_gradient(subset=['Total'], cmap='YlGn')
                            styler.apply(lambda x: ['font-weight: bold' if x.name == len(df_with_total)-1 else '' for i in x], axis=1)
                            return styler

                        active_stats = [c for c in stat_columns if c in df_with_total.columns]
                        final_cols = ["Player", "Team", "Seed"] + active_stats
                        
                        st.dataframe(
                            df_with_total[final_cols].style.pipe(style_roster), 
                            use_container_width=True, 
                            hide_index=True
                        )
                    else:
                        st.write("No picks recorded.")
        else:
            st.warning("Could not find the 'Contestant' column. Please check the headers.")
