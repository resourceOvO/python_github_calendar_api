# -*- coding: UTF-8 -*-
import json
import os
from http.server import BaseHTTPRequestHandler

import requests

DEFAULT_USER = os.environ.get("DEFAULT_USER", "resourceOvO")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
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


def getdata(name):
    """通过 GitHub GraphQL API 获取用户贡献日历数据"""
    if not GITHUB_TOKEN:
        raise Exception("GITHUB_TOKEN not set")

    resp = requests.post(
        GITHUB_GRAPHQL_URL,
        json={"query": QUERY, "variables": {"login": name}},
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
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

    # API 已按周分组且有序，直接映射字段名即可
    contributions = [
        [{"date": d["date"], "count": d["contributionCount"]} for d in week["contributionDays"]]
        for week in calendar["weeks"]
    ]

    return {"total": total, "contributions": contributions}


class handler(BaseHTTPRequestHandler):
    def _json_response(self, status, body):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def do_GET(self):
        try:
            parts = self.path.split("?", 1)
            user = parts[1] if len(parts) > 1 else DEFAULT_USER
            self._json_response(200, getdata(user))
        except Exception as e:
            self._json_response(500, {"error": str(e)})
