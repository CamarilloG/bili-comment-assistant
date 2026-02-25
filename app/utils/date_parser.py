from datetime import datetime, timedelta
import re

def parse_bilibili_date(date_str: str) -> datetime:
    """
    Parse Bilibili date string to datetime object.
    Formats:
    - "2023-10-25"
    - "10-25" (current year)
    - "昨天" (Yesterday)
    - "5小时前" (5 hours ago)
    - "刚刚" (Just now)
    """
    now = datetime.now()
    # Clean up artifacts like "· " prefix often found in Bilibili dates
    date_str = date_str.replace("·", "").strip()
    
    try:
        if "分钟前" in date_str:
            minutes = int(re.search(r'(\d+)', date_str).group(1))
            return now - timedelta(minutes=minutes)
        elif "小时前" in date_str:
            hours = int(re.search(r'(\d+)', date_str).group(1))
            return now - timedelta(hours=hours)
        elif "天前" in date_str:
            days = int(re.search(r'(\d+)', date_str).group(1))
            return now - timedelta(days=days)
        elif "昨天" in date_str:
            return now - timedelta(days=1)
        elif "刚刚" in date_str:
            return now
        elif "-" in date_str:
            parts = date_str.split("-")
            if len(parts) == 3: # YYYY-MM-DD
                return datetime.strptime(date_str, "%Y-%m-%d")
            elif len(parts) == 2: # MM-DD (Current Year)
                return datetime.strptime(f"{now.year}-{date_str}", "%Y-%m-%d")
        
        # Fallback for unknown formats or exact dates
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        # Return a very old date if parsing fails so it might be filtered out if strict
        # or kept if we want to be safe. Let's return None to indicate failure.
        return None
