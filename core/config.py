import yaml
import os
from typing import Dict, Any, List

class ConfigValidator:
    
    DEFAULT_CONFIG = {
        "account": {
            "cookie_file": "cookies.json"
        },
        "search": {
            "keywords": [],
            "max_videos_per_keyword": 5,
            "filter": {
                "sort": "totalrank",
                "duration": 0
            },
            "strategy": {
                "selection": "order",
                "random_pool_size": 20
            }
        },
        "comment": {
            "texts": [],
            "images": []
        },
        "behavior": {
            "min_delay": 5,
            "max_delay": 15,
            "headless": False,
            "timeout": 30000
        }
    }
    
    @staticmethod
    def load_config(path: str = "config.yaml") -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file {path} not found!")
        
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        return ConfigValidator.validate_and_fill_defaults(config)
    
    @staticmethod
    def validate_and_fill_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
        validated = ConfigValidator.DEFAULT_CONFIG.copy()
        
        if not config:
            return validated
        
        if "account" in config:
            validated["account"].update(config["account"])
        
        if "search" in config:
            if "keywords" in config["search"]:
                validated["search"]["keywords"] = config["search"]["keywords"]
            if "max_videos_per_keyword" in config["search"]:
                validated["search"]["max_videos_per_keyword"] = max(1, int(config["search"]["max_videos_per_keyword"]))
            
            if "filter" in config["search"]:
                validated["search"]["filter"].update(config["search"]["filter"])
                if validated["search"]["filter"]["sort"] not in ["totalrank", "pubdate", "click", "dm", "stow"]:
                    validated["search"]["filter"]["sort"] = "totalrank"
                if validated["search"]["filter"]["duration"] not in [0, 1, 2, 3, 4]:
                    validated["search"]["filter"]["duration"] = 0
            
            if "strategy" in config["search"]:
                validated["search"]["strategy"].update(config["search"]["strategy"])
                if validated["search"]["strategy"]["selection"] not in ["order", "random"]:
                    validated["search"]["strategy"]["selection"] = "order"
                validated["search"]["strategy"]["random_pool_size"] = max(1, int(validated["search"]["strategy"]["random_pool_size"]))
        
        if "comment" in config:
            if "texts" in config["comment"]:
                validated["comment"]["texts"] = config["comment"]["texts"]
            if "images" in config["comment"]:
                validated["comment"]["images"] = config["comment"]["images"]
        
        if "behavior" in config:
            if "min_delay" in config["behavior"]:
                validated["behavior"]["min_delay"] = max(0, float(config["behavior"]["min_delay"]))
            if "max_delay" in config["behavior"]:
                validated["behavior"]["max_delay"] = max(validated["behavior"]["min_delay"], float(config["behavior"]["max_delay"]))
            if "headless" in config["behavior"]:
                validated["behavior"]["headless"] = bool(config["behavior"]["headless"])
            if "timeout" in config["behavior"]:
                validated["behavior"]["timeout"] = max(1000, int(config["behavior"]["timeout"]))
        
        ConfigValidator._validate_required_fields(validated)
        
        return validated
    
    @staticmethod
    def _validate_required_fields(config: Dict[str, Any]) -> None:
        if not config["search"]["keywords"]:
            raise ValueError("At least one search keyword is required!")
        
        if not config["comment"]["texts"]:
            raise ValueError("At least one comment text is required!")
    
    @staticmethod
    def save_config(config: Dict[str, Any], path: str = "config.yaml") -> None:
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)
