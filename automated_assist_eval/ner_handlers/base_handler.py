from abc import ABC, abstractmethod
class BaseNerHandler(ABC):
    def __init__(self, model_path_or_name): self.model_path_or_name = model_path_or_name; self.model = None
    @abstractmethod
    def load_model(self): pass
    @abstractmethod
    def process(self, text, vignette_id="unknown"): pass
    def get_tool_name(self): return self.__class__.__name__.replace("Handler", "").lower()
