import requests
import json
import time

class DiscordNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_message(self, content):
        """
        Gửi tin nhắn dạng text đơn giản.
        """
        if not self.webhook_url:
            print("Chưa cấu hình Webhook URL.")
            return

        data = {
            "content": content
        }
        
        self._send_request(data)

    def send_embed(self, title, description, color=0x00ff00, fields=None):
        """
        Gửi tin nhắn dạng Embed (đẹp hơn) có hỗ trợ fields.
        """
        if not self.webhook_url:
            print("Chưa cấu hình Webhook URL.")
            return

        embed = {
            "title": title,
            "description": description,
            "color": color
        }
        
        if fields:
            embed["fields"] = fields

        data = {
            "embeds": [embed]
        }
        
        self._send_request(data)

    def _send_request(self, data):
        """
        Hàm private để gửi request thực tế.
        """
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(self.webhook_url, json=data, headers=headers)
            if response.status_code == 204:
                print("Đã gửi thông báo Discord thành công.")
            else:
                print(f"Gửi thất bại. Status Code: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"Lỗi khi gửi Discord: {e}")
