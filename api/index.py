# -*- coding: UTF-8 -*-
try:
    import json
    import os
    from http.server import BaseHTTPRequestHandler

    # 延迟导入，方便定位问题
    json_lib = json
    os_lib = os
    HandlerBase = BaseHTTPRequestHandler
    init_ok = True
except Exception as e:
    init_ok = False
    init_error = str(e)


class handler(HandlerBase if init_ok else object):
    def do_GET(self):
        if not init_ok:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json_lib.dumps({"error": f"init failed: {init_error}"}).encode("utf-8"))
            return

        try:
            # 解析用户名
            path = self.path
            user = path.split("?")[1] if "?" in path else ""

            if not user:
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json_lib.dumps({"status": "ok", "message": "API is running"}).encode("utf-8"))
                return

            # 尝试导入 requests 并调用 GitHub API
            import requests

            token = os_lib.environ.get("GITHUB_TOKEN", "")
            if not token:
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json_lib.dumps({"status": "ok", "message": "No GITHUB_TOKEN set", "user": user}).encode("utf-8"))
                return

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
                json={"query": query, "variables": {"login": user}},
                headers={
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/json",
                },
                timeout=15,
            )

            if resp.status_code != 200:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json_lib.dumps({
                    "error": "GitHub API error",
                    "status": resp.status_code,
                    "body": resp.text[:500]
                }).encode("utf-8"))
                return

            result = resp.json()

            if "errors" in result:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json_lib.dumps({"error": str(result["errors"])}).encode("utf-8"))
                return

            calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
            total = calendar["totalContributions"]
            weeks = calendar["weeks"]

            # 展平 + 排序
            all_days = []
            for week in weeks:
                for day in week["contributionDays"]:
                    all_days.append({"date": day["date"], "count": day["contributionCount"]})
            all_days.sort(key=lambda x: x["date"])

            # 每 7 天一组
            grouped = [all_days[i:i + 7] for i in range(0, len(all_days), 7)]

            data = {"total": total, "contributions": grouped}

            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json_lib.dumps(data).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json_lib.dumps({"error": str(e)}).encode("utf-8"))
