import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from euroleague_api.standings import Standings
from euroleague_api.team_stats import TeamStats
from euroleague_api.player_stats import PlayerStats
from euroleague_api.schedule import Schedule
from euroleague_api.game_metadata import GameMetadata

st.set_page_config(page_title="Euroleague Real-Time Hub", layout="wide")

st.title("🏀 Basketball Real-Time Hub")
st.markdown("Your ultimate companion for radio show prep: Real-time standings, stats, schedules, and news.")

COMPETITION_CODE = "E"
SEASON = 2026 # 2026-2027 season
CACHE_TTL = 120 # Cache data for 2 minutes for near real-time updates

with st.sidebar:
    st.header("Controls")
    if st.button("🔄 Force Live Refresh"):
        st.cache_data.clear()
        st.rerun()
    st.info("Data auto-refreshes every 2 minutes. Click the button to force an immediate live sync.")

@st.cache_data(ttl=CACHE_TTL)
def get_game_score(season, gamecode):
    try:
        # gamecode in schedule is like 'E2025_406', we need the integer 406
        int_gamecode = int(str(gamecode).split('_')[-1])
        
        gm = GameMetadata(COMPETITION_CODE)
        df = gm.get_game_metadata(season=season, gamecode=int_gamecode)
        if not df.empty:
            row = df.iloc[0]
            # Figure out who is home and away based on CodeTeamA
            return {
                row.get('CodeTeamA', ''): row.get('ScoreA', ''),
                row.get('CodeTeamB', ''): row.get('ScoreB', '')
            }
    except Exception:
        pass
        
    try:
        # gamecode in schedule is like 'E2025_406', we need the integer 406
        int_gamecode = int(str(gamecode).split('_')[-1])
        
        gm = GameMetadata(COMPETITION_CODE)
        df = gm.get_game_metadata(season=season-1, gamecode=int_gamecode)
        if not df.empty:
            row = df.iloc[0]
            return {
                row.get('CodeTeamA', ''): row.get('ScoreA', ''),
                row.get('CodeTeamB', ''): row.get('ScoreB', '')
            }
    except Exception:
        pass
    return {}

@st.cache_data(ttl=CACHE_TTL)
def get_standings(season):
    st_obj = Standings(COMPETITION_CODE)
    # Try current season rounds
    for r in range(34, 0, -1):
        try:
            df = st_obj.get_standings(season=season, round_number=r)
            if not df.empty:
                return df
        except Exception:
            pass
    # Fallback to previous season if current is empty
    for r in range(34, 0, -1):
        try:
            df = st_obj.get_standings(season=season-1, round_number=r)
            if not df.empty:
                return df
        except Exception:
            pass
    return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL)
def get_team_stats(season):
    try:
        ts_obj = TeamStats(COMPETITION_CODE)
        df = ts_obj.get_team_stats(endpoint="traditional", params={"seasoncode": f"E{season}"})
        if df.empty:
            df = ts_obj.get_team_stats(endpoint="traditional", params={"seasoncode": f"E{season-1}"})
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL)
def get_player_stats(season):
    try:
        ps_obj = PlayerStats(COMPETITION_CODE)
        df = ps_obj.get_player_stats(endpoint="traditional", params={"seasoncode": f"E{season}"})
        if df.empty:
            df = ps_obj.get_player_stats(endpoint="traditional", params={"seasoncode": f"E{season-1}"})
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL)
def get_schedule(season):
    try:
        sch_obj = Schedule(COMPETITION_CODE)
        df = sch_obj.get_schedule(season=season)
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def get_news(url):
    news_items = []
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall('./channel/item')[:10]:
                title = item.find('title').text
                link = item.find('link').text
                pubDate = item.find('pubDate').text
                desc_html = item.find('description').text
                desc_text = BeautifulSoup(desc_html, "html.parser").text if desc_html else ""
                news_items.append({
                    "title": title,
                    "link": link,
                    "pubDate": pubDate,
                    "description": desc_text
                })
    except Exception as e:
        st.error(f"Error fetching news: {e}")
    return news_items

# Main Layout
tabs = st.tabs(["🎯 Team Dashboard", "📰 League News"])

with tabs[0]:
    standings_df = get_standings(SEASON)
    schedule_df = get_schedule(SEASON)
    team_df = get_team_stats(SEASON)
    player_df = get_player_stats(SEASON)
    
    if not standings_df.empty:
        # Create a dictionary of Team Name -> Team Code
        teams_dict = dict(zip(standings_df['club.name'], standings_df['club.code']))
        selected_team = st.selectbox("Select a Team to View", sorted(teams_dict.keys()))
        team_code = teams_dict[selected_team]
        
        st.header(f"{selected_team} Dashboard")
        
        col1, col2 = st.columns(2)
        
        # Current Standing
        with col1:
            st.subheader("Current Standing")
            team_standing = standings_df[standings_df['club.code'] == team_code]
            if not team_standing.empty:
                row = team_standing.iloc[0]
                st.metric("Position", row.get('position', '-'))
                st.write(f"**Record:** {row.get('gamesWon', 0)} W - {row.get('gamesLost', 0)} L")
                st.write(f"**Points Difference:** {row.get('pointsDifference', 0)}")
        
        # Team Stats
        with col2:
            st.subheader("Team Stats (Avg Per Game)")
            t_stats = team_df[team_df['team.code'] == team_code]
            if not t_stats.empty:
                row = t_stats.iloc[0]
                st.write(f"**Points:** {row.get('pointsScored', 0)}")
                st.write(f"**Rebounds:** {row.get('totalRebounds', 0)}")
                st.write(f"**Assists:** {row.get('assists', 0)}")
                st.write(f"**PIR:** {row.get('pir', 0)}")
                
        st.divider()
        
        # Schedule Section
        st.subheader("Match Schedule")
        colA, colB = st.columns(2)
        
        if not schedule_df.empty:
            # Filter for this team
            team_schedule = schedule_df[(schedule_df.get('homecode') == team_code) | (schedule_df.get('awaycode') == team_code)]
            
            with colA:
                st.markdown("**Previous Matches**")
                if 'played' in team_schedule.columns:
                    past = team_schedule[team_schedule['played'] == 'true']
                    if not past.empty:
                        # Show last 3 games
                        for _, row in past.tail(3).iterrows():
                            home_code = row.get('homecode', '')
                            away_code = row.get('awaycode', '')
                            gamecode = row.get('gamecode')
                            
                            score_dict = get_game_score(SEASON, gamecode)
                            
                            home_score = score_dict.get(home_code, '-')
                            away_score = score_dict.get(away_code, '-')
                            
                            with st.container():
                                st.markdown(f"*{row.get('date', '')}*<br/>**{row.get('hometeam', '')}** {home_score} - {away_score} **{row.get('awayteam', '')}**", unsafe_allow_html=True)
                                st.divider()
                    else:
                        st.info("No past matches found.")
                else:
                    st.info("No past matches found.")
                    
            with colB:
                st.markdown("**Upcoming Matches**")
                if 'played' in team_schedule.columns:
                    upcoming = team_schedule[team_schedule['played'] == 'false']
                else:
                    upcoming = team_schedule
                    
                if not upcoming.empty:
                    # Show next 3 games
                    for _, row in upcoming.head(3).iterrows():
                        with st.container():
                            st.markdown(f"*{row.get('date', '')} {row.get('startime', '')}*<br/>**{row.get('hometeam', '')}** vs **{row.get('awayteam', '')}**", unsafe_allow_html=True)
                            st.divider()
                else:
                    st.info("No upcoming matches found.")
        else:
            st.warning("Could not load schedule.")
                
        st.subheader("Team Players")
        if not player_df.empty:
            p_stats = player_df[player_df['player.team.code'] == team_code]
            if not p_stats.empty:
                # Sort by PIR
                p_stats = p_stats.sort_values(by='pir', ascending=False)
                cols = ['player.name', 'gamesPlayed', 'pointsScored', 'totalRebounds', 'assists', 'steals', 'blocks', 'turnovers', 'pir']
                cols = [c for c in cols if c in p_stats.columns]
                st.dataframe(p_stats[cols], use_container_width=True)
            else:
                st.info("No player stats found.")
                
    else:
        st.warning("Data is currently loading or unavailable. Please wait.")

with tabs[1]:
    colA, colB = st.columns(2)
    with colA:
        st.header("Latest Euroleague News")
        el_news = get_news("https://www.eurohoops.net/en/euroleague/feed/")
        if el_news:
            for item in el_news:
                with st.expander(item["title"]):
                    st.write(f"**Published:** {item['pubDate']}")
                    st.write(item["description"])
                    st.markdown(f"[Read full article]({item['link']})")
        else:
            st.warning("No Euroleague news available.")

    with colB:
        st.header("Latest Greek Basket League News")
        gr_news = get_news("https://www.eurohoops.net/en/heba/feed/")
        if gr_news:
            for item in gr_news:
                with st.expander(item["title"]):
                    st.write(f"**Published:** {item['pubDate']}")
                    st.write(item["description"])
                    st.markdown(f"[Read full article]({item['link']})")
        else:
            st.warning("No Greek League news available.")
