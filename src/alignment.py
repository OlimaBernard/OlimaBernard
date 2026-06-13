from __future__ import annotations


def alignment_score(daily_bias: str, weekly_bias: str) -> str:
    d, w = daily_bias, weekly_bias
    if d == "Bullish" and w == "Bullish":
        return "Strong Bullish Alignment"
    if d == "Bearish" and w == "Bearish":
        return "Strong Bearish Alignment"
    if d == "Bullish" and w == "Neutral":
        return "Moderate Bullish Alignment"
    if d == "Bearish" and w == "Neutral":
        return "Moderate Bearish Alignment"
    if d == "Neutral" and w == "Bullish":
        return "Weekly Bullish Only"
    if d == "Neutral" and w == "Bearish":
        return "Weekly Bearish Only"
    if (d == "Bullish" and w == "Bearish") or (d == "Bearish" and w == "Bullish"):
        return "Mixed / Conflict"
    if d == "No Model" or w == "No Model":
        return "Model Missing"
    return "Neutral / No Clear Alignment"
