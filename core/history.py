import os
import json

class HistoryManager:
    def __init__(self, file_path="history.json"):
        self.file_path = file_path
        self.visited = self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def add(self, video_id: str):
        self.visited.add(video_id)
        self._save()

    def has(self, video_id: str):
        return video_id in self.visited

    def _save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(list(self.visited), f)

    @staticmethod
    def extract_bvid(url: str):
        # Extract BVxxx from url
        # https://www.bilibili.com/video/BV1xx411c7mD/
        # or https://www.bilibili.com/video/BV1xx411c7mD
        if "BV" in url:
            parts = url.split("/")
            for p in parts:
                if p.startswith("BV"):
                    # Remove any query params or trailing chars if split by / didn't catch it
                    return p.split("?")[0]
        return url
