
import threading
import time
import urllib.request
import json

class KeepAlive:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.running = True
        self.thread = None
    
    def start(self):
        """Start keep-alive service"""
        self.thread = threading.Thread(target=self._keep_alive_loop, daemon=True)
        self.thread.start()
        print("🛡️ Keep-alive сервис запущен")
    
    def stop(self):
        """Stop keep-alive service"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("🛡️ Keep-alive сервис остановлен")
    
    def _keep_alive_loop(self):
        """Keep-alive loop to prevent sleeping"""
        while self.running:
            try:
                # Ping Telegram API every 45 seconds
                time.sleep(45)
                
                if not self.running:
                    break
                    
                # Send getMe request to keep connection alive
                response = urllib.request.urlopen(f"{self.bot.api_url}/getMe", timeout=10)
                data = json.loads(response.read().decode('utf-8'))
                
                if data.get('ok'):
                    print(f"🔄 Keep-alive: Bot активен - {time.strftime('%H:%M:%S')}")
                else:
                    print("⚠️ Keep-alive: Проблемы с подключением к Telegram")
                    
            except Exception as e:
                print(f"❌ Keep-alive error: {e}")
                # Continue loop even on errors
                continue
