import sys
from ner_handlers.base_handler import BaseNerHandler
class SpacyHandler(BaseNerHandler):
    def load_model(self):
        try: import spacy; self.model = spacy.load(self.model_path_or_name); print(f"Spacy model '{self.model_path_or_name}' loaded successfully.")
        except ImportError: print(f"Error: spaCy library not found. pip install spacy."); self.model = None
        except OSError as e: print(f"Error loading spaCy model '{self.model_path_or_name}': {e}\nTry: python -m spacy download {self.model_path_or_name}"); self.model = None
        except Exception as e: print(f"Unexpected error loading spaCy model '{self.model_path_or_name}': {e}"); self.model = None
    def process(self, text, vignette_id="unknown"):
        if not self.model: return []
        doc = self.model(text); entities = []
        for ent in doc.ents: entities.append({"text": ent.text, "label": ent.label_, "start_char": ent.start_char, "end_char": ent.end_char})
        return entities
    def get_tool_name(self): return "spacy"
