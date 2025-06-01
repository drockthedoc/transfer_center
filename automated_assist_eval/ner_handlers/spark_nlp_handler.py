from ner_handlers.base_handler import BaseNerHandler
class SparkNlpHandler(BaseNerHandler):
    def load_model(self): self.model = "dummy_model_for_SparkNlpHandler"
    def process(self, text, v_id="unknown"): return [{"text": "dummy_SparkNlpHandler", "label": "DUMMY", "start":0,"end":20+15}] if self.model else []
