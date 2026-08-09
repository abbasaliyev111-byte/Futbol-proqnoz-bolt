"""
football-data.org API-dən komanda statistikası və günün matçlarını çəkir.
Pulsuz API açarı: https://www.football-data.org/client/register
"""

import requests
from predictor import TeamStats

BASE_URL = "https://api.football-data.org/v4"

# Populyar liqaların kodları (football-data.org-da)
LEAGUE_CODES = {
    "premier_league": "PL",
    "la_liga": "PD",
    "bundesliga": "BL1",
    "serie_a": "SA",
    "ligue_1": "FL1",
    "champions_league": "CL",
}


class FootballDataClient:
    def __init__(self, api_key: str):
        self.headers = {"X-Auth-Token": api_key}

    def get_todays_matches(self, league_code: str) -> list:
        """Verilmiş liqada bugünkü (SCHEDULED statuslu) matçları qaytarır"""
        url = f"{BASE_URL}/competitions/{league_code}/matches"
        params = {"status": "SCHEDULED"}
        resp = requests.get(url, headers=self.headers, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("matches", [])

    def get_team_last_matches(self, team_id: int, limit: int = 5) -> list:
        """Komandanın son N matçının nəticələrini qaytarır"""
        url = f"{BASE_URL}/teams/{team_id}/matches"
        params = {"status": "FINISHED", "limit": limit}
        resp = requests.get(url, headers=self.headers, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("matches", [])

    def build_team_stats(self, team_id: int, team_name: str, limit: int = 5) -> TeamStats:
        """Son N matçdan TeamStats obyekti qurur (ev/qonaq fərqi qoymadan, ümumi)"""
        matches = self.get_team_last_matches(team_id, limit)
        scored, conceded = [], []

        for m in matches:
            is_home = m["homeTeam"]["id"] == team_id
            home_goals = m["score"]["fullTime"]["home"]
            away_goals = m["score"]["fullTime"]["away"]

            if home_goals is None or away_goals is None:
                continue  # natamam data

            if is_home:
                scored.append(home_goals)
                conceded.append(away_goals)
            else:
                scored.append(away_goals)
                conceded.append(home_goals)

        if not scored:
            # ehtiyat: heç bir matç tapılmasa, liqa ortalaması ilə doldur
            scored, conceded = [1], [1]

        return TeamStats(name=team_name, goals_scored=scored, goals_conceded=conceded)
