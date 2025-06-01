from ner_handlers.base_handler import BaseNerHandler
class CustomBertFlairHandler(BaseNerHandler):
    def load_model(self): self.model = "dummy_model_for_CustomBertFlairHandler"
    def process(self, text, v_id="unknown"): return [{"text": "dummy_CustomBertFlairHandler", "label": "DUMMY", "start":0,"end":20+22}] if self.model else []
