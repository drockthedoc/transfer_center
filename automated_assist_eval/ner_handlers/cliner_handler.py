from ner_handlers.base_handler import BaseNerHandler
class ClinerHandler(BaseNerHandler):
    def load_model(self): self.model = "dummy_model_for_ClinerHandler"
    def process(self, text, v_id="unknown"): return [{"text": "dummy_ClinerHandler", "label": "DUMMY", "start":0,"end":20+13}] if self.model else []
