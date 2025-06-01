from ner_handlers.base_handler import BaseNerHandler
class FdsMednerHandler(BaseNerHandler):
    def load_model(self): self.model = "dummy_model_for_FdsMednerHandler"
    def process(self, text, v_id="unknown"): return [{"text": "dummy_FdsMednerHandler", "label": "DUMMY", "start":0,"end":20+16}] if self.model else []
