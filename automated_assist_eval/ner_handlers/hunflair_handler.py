from ner_handlers.base_handler import BaseNerHandler
class HunflairHandler(BaseNerHandler):
    def load_model(self): self.model = "dummy_model_for_HunflairHandler"
    def process(self, text, v_id="unknown"): return [{"text": "dummy_HunflairHandler", "label": "DUMMY", "start":0,"end":20+15}] if self.model else []
