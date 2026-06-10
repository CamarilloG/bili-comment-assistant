from playwright.sync_api import Page
from typing import Optional
import threading

class GlobalContext:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(GlobalContext, cls).__new__(cls)
                    # Initialize attributes on the instance directly
                    cls._instance._page: Optional[Page] = None
                    cls._instance.running = False
        return cls._instance

    @property
    def page(self) -> Optional[Page]:
        return self._instance._page

    @page.setter
    def page(self, page: Page):
        self._instance._page = page

    def set_page(self, page: Page):
        self.page = page

    def get_page(self) -> Optional[Page]:
        return self.page

    def clear_page(self):
        self.page = None

# Global instance
context = GlobalContext()
