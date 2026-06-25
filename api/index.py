# -*- coding: UTF-8 -*-
import json
import os
import requests
from http.server import BaseHTTPRequestHandler

DEFAULT_USER = "resourceOvO"


def getdata(name):
    """通过 GitHub GraphQL API 获取用户贡献日历数据"""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise Exception("GITHUB_TOKEN not set")

    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"login": name}},
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
        timeout=15,
    )

    if resp.status_code != 200:
        raise Exception(f"GitHub API returned {resp.status_code}: {resp.text[:300]}")

    result = resp.json()

    if "errors" in result:
        raise Exception(str(result["errors"]))

    calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    total = calendar["totalContributions"]
    weeks = calendar["weeks"]

    all_days = []
    for week in weeks:
        for day in week["contributionDays"]:
            all_days.append({"date": day["date"], "count": day["contributionCount"]})
    all_days.sort(key=lambda x: x["date"])

    grouped = [all_days[i:i + 7] for i in range(0, len(all_days), 7)]

    return {"total": total, "contributions": grouped}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            path = self.path
            user = path.split("?")[1] if "?" in path else DEFAULT_USER

            data = getdata(user)

            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
