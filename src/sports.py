from typing import Any
from mcp.server.fastmcp import FastMCP
import httpx
import asyncio
from enum import Enum
from os import environ

CRICKET_API_HOST = "cricbuzz-cricket.p.rapidapi.com"
CRICKET_API_BASE = f'https://{CRICKET_API_HOST}'

mcp = FastMCP("cricket")

async def make_api_request(url: str) -> dict[str, Any] | None:
    headers = {
        'x-rapidapi-key': environ.get("CRICKET_API_KEY", ""),
        'x-rapidapi-host': CRICKET_API_HOST
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
        
def format_match_summary(matchDetails: dict | str) -> str:
    if isinstance(matchDetails, str):
        return matchDetails

    return f"""
    Series name: {matchDetails.get('seriesName', 'unknown')}
    Match description: {matchDetails.get('matchDesc', 'unknown')}
    Format: {matchDetails.get('matchFormat', 'unknown')}
    Status: {matchDetails.get('status', 'unknown')}
    Scores: {'No scores available' if matchDetails.get('score', None) is None else matchDetails.get('score')}
    """

class MatchTime(Enum):
    Live = "live"
    Recent = "recent"
    Upcoming = "upcoming"

class MatchGeo(Enum):
    Domestic = "domestic"
    International = "international"
    League = "league"
    Women = "women"

def findTeamMatches(matchData: dict, team1: str, team2: str) -> list[dict]:
    if not matchData or "typeMatches" not in matchData:
        return []

    if not isinstance(matchData["typeMatches"], list):
        return []

    parsedMatches: list[dict] = []

    for matchTypeObj in matchData["typeMatches"]:
        seriesMatches = matchTypeObj.get("seriesMatches", None)
        if not seriesMatches or not isinstance(seriesMatches, list):
            continue

        for seriesObj in seriesMatches:
            seriesData = seriesObj.get("seriesAdWrapper", None)
            if not seriesData:
                continue

            matches = seriesData.get("matches", None)
            if not matches or not isinstance(matches, list):
                continue

            for matchObj in matches:
                matchInfo = matchObj.get("matchInfo", {})
                matchScore = matchObj.get("matchScore", {})

                seriesName = matchInfo.get("seriesName", "")
                matchStatus = matchInfo.get("status", "")
                team1Name = matchInfo.get("team1", {}).get("teamName", "")
                team2Name = matchInfo.get("team2", {}).get("teamName", "")

                isMatch: bool = False

                team1Id = ""
                team2Id = ""

                isConditionA = (team1.lower() in team1Name.lower() and team2.lower() in team2Name.lower())
                isConditionB = (team2.lower() in team1Name.lower() and team1.lower() in team2Name.lower())

                if (isConditionA or isConditionB):
                    isMatch = True
                    if isConditionA:
                        team1Id, team2Id = team1Name, team2Name
                    else:
                        team1Id, team2Id = team2Name, team1Name

                if not isMatch: continue

                team1Score = matchScore.get("team1Score", None)
                team2Score = matchScore.get("team2Score", None)

                scoreStr: str | None = None
                if team1Score and team2Score:
                    scoreStr = f"""
                    {team1Id}'s score: {team1Score}
                    {team2Id}'s score: {team2Score}
                    """

                parsedMatches.append({
                    "seriesName": seriesName,
                    "matchFormat": matchInfo.get("matchFormat", ""),
                    "matchDesc": matchInfo.get("matchDesc", ""),
                    "status": matchStatus,
                    "score": scoreStr
                })

    return parsedMatches

@mcp.tool()
async def get_matches(numMatches: str | None, matchTime: str | None, matchGeo: str | None) -> str | None:
    """
    Get the top numMatches matches of match timing matchTime and match regionality matchGeo.

    Args:
        numMatches: the number of live matches to display
        matchTime: the timing of matches to display (live/ recent/ upcoming). All is not supported. If you call this function with matchTime=All or none, then
        call this API for live, upcoming and recent matches separately.
        matchGeo: the regionality of matches to display (Domestic/International/League/Women). If this is not passed or is null, then replace
        this argument with "All".

        if any of these arguments is not passed or are None, then assume that all matches across that particular dimension are to be
        shown.
    """
    request_url = f'{CRICKET_API_BASE}/matches/v1/{str(matchTime)}'
    data = await make_api_request(request_url)

    if not data or "typeMatches" not in data:
        return "Failed to fetch list of active matches."

    if not isinstance(data["typeMatches"], list):
        return "Invalid list of active matches."

    if numMatches == None: numMatches = 10
    else: numMatches = int(numMatches)

    output: list[dict] = []

    if matchGeo == None or str(matchGeo) == "null": matchGeo = "All"

    for matchTypeObj in data["typeMatches"]:
        if len(output) == numMatches: break

        if not(matchGeo == "All" or matchGeo == matchTypeObj["matchType"]):
            continue
        
        seriesMatches = matchTypeObj["seriesMatches"]
        if seriesMatches == None or not isinstance(seriesMatches, list):
            continue

        for seriesObj in seriesMatches:
            seriesData = seriesObj.get("seriesAdWrapper", None)

            if not seriesData: continue

            seriesName = seriesData["seriesName"]

            matchObj = seriesData["matches"][0]
            matchInfo = matchObj["matchInfo"]
            matchDesc = matchInfo["matchDesc"]
            matchFormat = matchInfo["matchFormat"]
            status = matchInfo["status"]

            output.append({
                "seriesName" : seriesName,
                "matchDesc": matchDesc,
                "matchFormat": matchFormat,
                "status": status
            })

    match_statuses = [format_match_summary(match_summary) for match_summary in output]
    return "\n---\n".join(match_statuses)

@mcp.tool()
async def get_live_match_details(team1: str, team2: str | None) -> str:
    """
    Get the details on the active match between team1 and team2.
    team1 is not an optional parameter. If team2 is not provided, then return all the live matches involving team1.

    Args:
    team1: The name of the first team
    team2: The name of the second team
    """

    recentMatchesData = await make_api_request(f'{CRICKET_API_BASE}/matches/v1/recent')
    parsedRecentMatches = findTeamMatches(recentMatchesData, team1, team2)

    liveMatchesData = await make_api_request(f'{CRICKET_API_BASE}/matches/v1/live')
    parsedLiveMatches = findTeamMatches(liveMatchesData, team1, team2)

    upcomingMatchesData = await make_api_request(f'{CRICKET_API_BASE}/matches/v1/upcoming')
    parsedUpcomingMatches = findTeamMatches(upcomingMatchesData, team1, team2)

    parsedMatchData = {
        "recent": parsedRecentMatches if len(parsedRecentMatches) else ["No recent matches found."],
        "live": parsedLiveMatches if len(parsedLiveMatches) else ["No live matches found."],
        "upcoming": parsedUpcomingMatches if len(parsedUpcomingMatches) else ["No upcoming matches found."]
    }

    delimiter = "\n---\n"

    return delimiter.join([
        f"Upcoming matches: {delimiter.join([format_match_summary(match) for match in parsedMatchData['upcoming']])}",
        f"Live matches: {delimiter.join([format_match_summary(match) for match in parsedMatchData['live']])}",
        f"Recent matches: {delimiter.join([format_match_summary(match) for match in parsedMatchData['recent']])}"
    ])

async def test():
    data = await get_live_match_details("India", "England")
    print(data)

if __name__ == "__main__":
    mcp.run(transport="stdio")
    # asyncio.run(test())
