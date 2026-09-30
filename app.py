import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from euroleague_api.standings import Standings
from euroleague_api.team_stats import TeamStats
from euroleague_api.player_stats import PlayerStats
from euroleague_api.schedule import Schedule

st.set_page_config(page_title="Euroleague Real-Time Hub", layout="wide")

st.title("🏀 Basketball Real-Time Hub")
st.markdown("Your ultimate companion for radio show prep: Real-time standings, stats, schedules, and news.")

COMPETITION_CODE = "E"
SEASON = 2024 # Current season

@st.cache_data(ttl=3600)
def get_standings():
    st_obj = Standings(COMPETITION_CODE)
    for r in range(34, 0, -1):
        try:
            df = st_obj.get_standings(season=SEASON, round_number=r)
            if not df.empty:
                return df
        except Exception:
            pass
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_team_stats():
    try:
        ts_obj = TeamStats(COMPETITION_CODE)
        df = ts_obj.get_team_stats(endpoint="traditional", params={"seasoncode": f"E{SEASON}"})
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_player_stats():
    try:
        ps_obj = PlayerStats(COMPETITION_CODE)
        df = ps_obj.get_player_stats(endpoint="traditional", params={"seasoncode": f"E{SEASON}"})
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_schedule():
    try:
        sch_obj = Schedule(COMPETITION_CODE)
        df = sch_obj.get_schedule(season=SEASON)
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

tabs = st.tabs([
    "📊 Euroleague Standings", 
    "📅 Euroleague Schedule",
    "📈 Team Stats", 
    "⭐ Player Stats", 
    "📰 Euroleague News",
    "🇬🇷 Greek League News"
])

with tabs[0]:
    st.header("Euroleague Standings")
    standings_df = get_standings()
    if not standings_df.empty:
        st.dataframe(standings_df, use_container_width=True)
    else:
        st.warning("Could not fetch standings at the moment.")

with tabs[1]:
    st.header("Euroleague Schedule")
    schedule_df = get_schedule()
    if not schedule_df.empty:
        st.dataframe(schedule_df, use_container_width=True)
    else:
        st.warning("Could not fetch schedule at the moment.")

with tabs[2]:
    st.header("Team Performance")
    team_df = get_team_stats()
    if not team_df.empty:
        st.dataframe(team_df, use_container_width=True)
    else:
        st.warning("Could not fetch team stats at the moment.")

with tabs[3]:
    st.header("Player Highlights")
    player_df = get_player_stats()
    if not player_df.empty:
        st.dataframe(player_df, use_container_width=True)
    else:
        st.warning("Could not fetch player stats at the moment.")

with tabs[4]:
    st.header("Latest Euroleague News & Talking Points")
    el_news = get_news("https://www.eurohoops.net/en/euroleague/feed/")
    if el_news:
        for item in el_news:
            with st.expander(item["title"]):
                st.write(f"**Published:** {item['pubDate']}")
                st.write(item["description"])
                st.markdown(f"[Read full article]({item['link']})")
    else:
        st.warning("No Euroleague news available.")

with tabs[5]:
    st.header("Latest Greek Basket League News")
    st.info("Live Greek League standings require a paid data provider. Instead, here is a live feed of the latest Greek League (ESAKE) news and results to fuel your show!")
    gr_news = get_news("https://www.eurohoops.net/en/heba/feed/")
    if gr_news:
        for item in gr_news:
            with st.expander(item["title"]):
                st.write(f"**Published:** {item['pubDate']}")
                st.write(item["description"])
                st.markdown(f"[Read full article]({item['link']})")
    else:
        st.warning("No Greek League news available.")
