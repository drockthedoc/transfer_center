import json, argparse, os, importlib.util, re, sys
from pathlib import Path

HANDLER_DIR = Path(__file__).parent / "ner_handlers"

def load_vignettes(file_path):
    vignettes = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
        raw_parts = re.split(r"(Patient #\d+\s*(?:\(ID:\s*\w+\))?:\s*)", content)
        if len(raw_parts) > 1:
            current_id_base = None; vignette_text_acc = ""; entry_index = 0
            for i, part in enumerate(raw_parts):
                if part.startswith("Patient #"):
                    if current_id_base and vignette_text_acc.strip(): vignettes[f"{current_id_base}_v{entry_index}"] = vignette_text_acc.strip(); entry_index +=1
                    current_id_base = part.strip().rstrip(':').replace("Patient #", "Pt").replace(" ", "_").replace("(", "").replace(")", "").replace(":", ""); vignette_text_acc = ""
                elif part.strip(): vignette_text_acc += part
            if current_id_base and vignette_text_acc.strip(): vignettes[f"{current_id_base}_v{entry_index}"] = vignette_text_acc.strip()
        if not vignettes and content.strip():
             print("Primary 'Patient #' delimiter not effective, trying double newline split."); valid_parts = [p.strip() for p in content.split('\n\n') if p.strip()]
             if len(valid_parts) > 0:
                 for i, part_text in enumerate(valid_parts): vignettes[f"Vignette_{i+1}"] = part_text
             elif content.strip(): vignettes["Vignette_1"] = content.strip()
        if not vignettes: print(f"Warning: No vignettes loaded from {file_path}.")
    except FileNotFoundError: print(f"Error: Vignettes file {file_path} not found."); return None
    except Exception as e: print(f"Error loading vignettes from {file_path}: {e}"); return None
    print(f"Loaded {len(vignettes)} vignettes from {file_path}.")
    return vignettes

def get_handler_class(tool_type):
    handler_module_name = f"{tool_type}_handler"; words = tool_type.split('_'); handler_class_name = "".join(word.capitalize() for word in words)
    if not handler_class_name.endswith("Handler"): handler_class_name += "Handler"
    try:
        module_path = HANDLER_DIR / f"{handler_module_name}.py"; module_full_name = f"ner_handlers.{handler_module_name}"
        spec = importlib.util.spec_from_file_location(module_full_name, str(module_path))
        if spec is None: print(f"Error: Module spec for {module_full_name} not found at {module_path}."); return None
        handler_module = importlib.util.module_from_spec(spec)
        if module_full_name in sys.modules: pass # print(f"Warning: {module_full_name} already in sys.modules. Overwriting.")
        sys.modules[module_full_name] = handler_module
        spec.loader.exec_module(handler_module)
        return getattr(handler_module, handler_class_name)
    except FileNotFoundError: print(f"Error: Handler file {module_path} not found."); return None
    except AttributeError: print(f"Error: Class {handler_class_name} not found in {module_path}."); return None
    except Exception as e: print(f"Error importing handler for {tool_type}: {e}"); return None

def main():
    parser = argparse.ArgumentParser(description="Process vignettes with NER models.")
    parser.add_argument("--vignettes_file", default="data/vignettes.txt", help="Input vignettes file.")
    parser.add_argument("--output_json", default="output/ner_outputs.json", help="Output NER JSON.")
    parser.add_argument("--ner_config", required=True, help="NER tools JSON config.")
    args = parser.parse_args()

    ner_configurations = [];
    if os.path.exists(args.ner_config):
        try:
            with open(args.ner_config, 'r') as f: ner_configurations = json.load(f)
        except Exception as e: print(f"Error reading/parsing config file {args.ner_config}: {e}"); return
    else:
        try: ner_configurations = json.loads(args.ner_config)
        except Exception as e: print(f"Error parsing config string: {e}"); return
    if not isinstance(ner_configurations, list): print("Error: NER config must be a list."); return
    vignettes = load_vignettes(args.vignettes_file)
    if not vignettes: print("Exiting: vignette loading failed."); return
    all_ner_outputs = {}
    for config in ner_configurations:
        tool_type = config.get("tool_type"); model_specifier = config.get("model_path_or_name") or config.get("model_name") or config.get("model_path")
        if not tool_type or not model_specifier: print(f"Warning: Invalid config (missing tool_type/model_specifier): {config}"); continue
        print(f"\nProcessing tool: {tool_type}, model: {model_specifier}")
        HandlerClass = get_handler_class(tool_type)
        if not HandlerClass: print(f"Warning: Handler for '{tool_type}' not loaded. Skipping."); continue
        try:
            handler_instance = HandlerClass(model_specifier); handler_instance.load_model()
        except Exception as e: print(f"Error init/load model for {tool_type} ({model_specifier}): {e}"); continue
        if handler_instance.model is None: print(f"Skipping {tool_type} ({model_specifier}): model loading failed (model attribute is None)."); continue

        # Corrected line for output_key:
        sanitized_model_spec = model_specifier.replace('/', '_').replace('\\', '_')
        output_key = f"{handler_instance.get_tool_name()}_{sanitized_model_spec}"
        all_ner_outputs[output_key] = {}

        for v_id, v_text in vignettes.items(): all_ner_outputs[output_key][v_id] = handler_instance.process(v_text,v_id)
        print(f"Finished processing with {output_key}.")
    output_dir = Path(args.output_json).parent;
    try:
        output_dir.mkdir(parents=True, exist_ok=True);
        with open(args.output_json, 'w') as f: json.dump(all_ner_outputs, f, indent=2)
        print(f"\nNER outputs saved to: {args.output_json}")
    except Exception as e: print(f"Error saving NER outputs: {e}")
if __name__ == "__main__": main()
