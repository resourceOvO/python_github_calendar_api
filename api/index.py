# -*- coding: UTF-8 -*-
import requests
import json
import os
from http.server import BaseHTTPRequestHandler

# 从环境变量读取 Token（不要在代码中硬编码！）
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def list_split(items, n):
    """将列表按每 n 个一组拆分"""
    return [items[i:i + n] for i in range(0, len(items), n)]


def getdata(name):
    """通过 GitHub GraphQL API 获取用户贡献日历数据"""
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

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"login": name}},
        headers=headers,
        timeout=15,
    )

    if resp.status_code != 200:
        raise Exception(f"GitHub API returned {resp.status_code}: {resp.text}")

    result = resp.json()

    if "errors" in result:
        raise Exception(f"GitHub API error: {result['errors']}")

    calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    total = calendar["totalContributions"]
    weeks = calendar["weeks"]

    # 将所有天的数据展平
    all_days = []
    for week in weeks:
        for day in week["contributionDays"]:
            all_days.append({
                "date": day["date"],
                "count": day["contributionCount"]
            })

    # 按日期排序
    all_days.sort(key=lambda x: x["date"])

    # 每 7 天一组（保持与旧版 API 相同的格式）
    datalistsplit = list_split(all_days, 7)

    return {
        "total": total,
        "contributions": datalistsplit
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        # 从查询参数中提取用户名（例如 /api/?resourceOvO）
        user = path.split("?")[1] if "?" in path else ""

        if not user:
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing username"}).encode("utf-8"))
            return

        try:
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
