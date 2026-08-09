"""
Futbol Proqnoz Modeli — Poisson Distribution əsaslı
=====================================================
Bu modul komanda statistikalarına əsasən (son matçlardakı hücum/müdafiə
gücü) hər matçın 1X2, Over/Under 2.5 və BTTS ehtimallarını hesablayır.

QEYD: Heç bir statistik model 100% (və ya 90%) dəqiqlik verə bilməz.
Bu model dürüst, elmi əsaslı ehtimallar (adətən 1X2-də ~50-55% "hit rate")
verir — bu, uzunmüddətli dəqiq analiz üçündür, "zəmanətli qazanc" üçün deyil.
"""

import math
from dataclasses import dataclass


@dataclass
class TeamStats:
    """Bir komandanın son N matçdakı hücum/müdafiə statistikası"""
    name: str
    goals_scored: list       # son matçlarda vurduğu qollar, məs [2,1,3,0,1]
    goals_conceded: list     # son matçlarda buraxdığı qollar

    @property
    def avg_scored(self) -> float:
        return sum(self.goals_scored) / len(self.goals_scored)

    @property
    def avg_conceded(self) -> float:
        return sum(self.goals_conceded) / len(self.goals_conceded)


def poisson_prob(k: int, lam: float) -> float:
    """Poisson ehtimalı: verilmiş lambda (gözlənilən qol) üçün tam olaraq k qol ehtimalı"""
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def expected_goals(
    home: TeamStats,
    away: TeamStats,
    league_avg_home_goals: float = 1.5,
    league_avg_away_goals: float = 1.2,
    home_advantage: float = 1.15,
) -> tuple[float, float]:
    """
    Ev sahibi və qonaq komandanın gözlənilən qol sayını (lambda) hesablayır.

    Düstur (Dixon-Coles sadələşdirilmiş forması):
    home_attack_strength = home.avg_scored / league_avg_home_goals
    away_defense_strength = away.avg_conceded / league_avg_away_goals
    lambda_home = home_attack_strength * away_defense_strength * league_avg_home_goals * home_advantage
    (əksinə də eyni məntiqlə away üçün)
    """
    home_attack = home.avg_scored / league_avg_home_goals
    home_defense = home.avg_conceded / league_avg_away_goals
    away_attack = away.avg_scored / league_avg_away_goals
    away_defense = away.avg_conceded / league_avg_home_goals

    lambda_home = home_attack * away_defense * league_avg_home_goals * home_advantage
    lambda_away = away_attack * home_defense * league_avg_away_goals

    return lambda_home, lambda_away


def match_probabilities(lambda_home: float, lambda_away: float, max_goals: int = 6) -> dict:
    """
    Verilmiş lambda dəyərlərindən 1X2, Over/Under 2.5, BTTS ehtimallarını çıxarır.
    Hər mümkün skor kombinasiyasının (0-0-dan max_goals-max_goals-a qədər) ehtimalını
    toplayaraq hesablanır.
    """
    home_win = draw = away_win = 0.0
    over_2_5 = under_2_5 = 0.0
    btts_yes = btts_no = 0.0

    score_matrix = {}

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson_prob(h, lambda_home) * poisson_prob(a, lambda_away)
            score_matrix[(h, a)] = p

            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p

            if h + a > 2.5:
                over_2_5 += p
            else:
                under_2_5 += p

            if h > 0 and a > 0:
                btts_yes += p
            else:
                btts_no += p

    # normallaşdırma (max_goals limitindən qaynaqlanan kiçik xətanı düzəldir)
    total = home_win + draw + away_win
    home_win, draw, away_win = home_win / total, draw / total, away_win / total

    most_likely_score = max(score_matrix, key=score_matrix.get)

    return {
        "1x2": {
            "home_win": round(home_win * 100, 1),
            "draw": round(draw * 100, 1),
            "away_win": round(away_win * 100, 1),
        },
        "over_under_2_5": {
            "over": round(over_2_5 * 100, 1),
            "under": round(under_2_5 * 100, 1),
        },
        "btts": {
            "yes": round(btts_yes * 100, 1),
            "no": round(btts_no * 100, 1),
        },
        "most_likely_score": f"{most_likely_score[0]}-{most_likely_score[1]}",
        "expected_goals": {
            "home": round(lambda_home, 2),
            "away": round(lambda_away, 2),
        },
    }


def predict_match(home: TeamStats, away: TeamStats, **league_params) -> dict:
    """Tam proqnoz: TeamStats obyektlərindən birbaşa nəticə çıxarır"""
    lam_h, lam_a = expected_goals(home, away, **league_params)
    result = match_probabilities(lam_h, lam_a)
    result["match"] = f"{home.name} vs {away.name}"
    return result


if __name__ == "__main__":
    # Nümunə: son 5 matçın qol statistikası ilə sınaq
    home = TeamStats(name="Team A", goals_scored=[2, 1, 3, 1, 2], goals_conceded=[1, 0, 1, 2, 1])
    away = TeamStats(name="Team B", goals_scored=[1, 1, 0, 2, 1], goals_conceded=[2, 1, 2, 1, 3])

    prediction = predict_match(home, away)

    print(f"\n⚽ {prediction['match']}")
    print(f"Gözlənilən qol: {prediction['expected_goals']['home']} - {prediction['expected_goals']['away']}")
    print(f"Ən ehtimallı skor: {prediction['most_likely_score']}")
    print(f"\n1X2:")
    print(f"  Ev sahibi qalib: {prediction['1x2']['home_win']}%")
    print(f"  Heç-heçə:        {prediction['1x2']['draw']}%")
    print(f"  Qonaq qalib:     {prediction['1x2']['away_win']}%")
    print(f"\nOver/Under 2.5: Over {prediction['over_under_2_5']['over']}% / Under {prediction['over_under_2_5']['under']}%")
    print(f"BTTS: Bəli {prediction['btts']['yes']}% / Xeyr {prediction['btts']['no']}%")
