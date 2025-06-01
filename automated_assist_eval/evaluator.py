import json
import argparse
import re
from collections import Counter, defaultdict

def normalize_text(text):
    return text.lower()

def load_json_file(file_path, description="file"):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {description.capitalize()} not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {description} at {file_path}")
        return None

def load_vignettes_for_evaluator(file_path):
    """
    Loads vignettes from a text file for the evaluator.
    This logic should ideally be shared/consistent with ner_processor.py's loader.
    Returns a dictionary of {vignette_id: vignette_text}.
    """
    vignettes = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Regex to capture "Patient #X (ID: Y):" or "Patient #X:" as a delimiter
        # and the text following it.
        # This regex splits the text, keeping the delimiters.
        raw_parts = re.split(r"(Patient #\d+\s*(?:\(ID:\s*\w+\))?:\s*)", content)

        if len(raw_parts) > 1: # Pattern was found and split occurred
            current_id_base = None
            vignette_text_acc = ""
            entry_index = 0 # To ensure unique vignette IDs if base IDs repeat (shouldn't with this logic)

            # raw_parts[0] is text before the first delimiter, if any.
            # Then parts alternate: delimiter, text, delimiter, text...
            for i, part in enumerate(raw_parts):
                if part.startswith("Patient #"):
                    # If there was a previous patient's text accumulated, save it
                    if current_id_base and vignette_text_acc.strip():
                        vignettes[f"{current_id_base}_v{entry_index}"] = vignette_text_acc.strip()
                        entry_index += 1

                    # Clean up the ID to use as a key
                    current_id_base = part.strip().rstrip(':').replace("Patient #", "Pt")
                    current_id_base = current_id_base.replace(" ", "_").replace("(", "").replace(")", "").replace(":", "")
                    vignette_text_acc = "" # Reset accumulator for the new patient's text
                elif part.strip(): # This is text after a delimiter, or initial text
                    if current_id_base is None and i == 0: # Text before the first "Patient #"
                        # Decide what to do with text before the first "Patient #"
                        # For now, we'll ignore it unless it's the *only* text.
                        if len(raw_parts) == 1: # No "Patient #" delimiters found at all
                             vignette_text_acc += part
                        # else: print(f"Note: Ignoring pre-first-Patient# text: {part[:50]}...")
                    else:
                        vignette_text_acc += part

            # Save the last vignette accumulated
            if current_id_base and vignette_text_acc.strip():
                 vignettes[f"{current_id_base}_v{entry_index}"] = vignette_text_acc.strip()

        # Fallback or if no "Patient #" delimiters were effective
        if not vignettes and content.strip():
             print(f"Vignette loading: Primary 'Patient #' delimiter not effective or no vignettes found using it. Trying double newline split for '{file_path}'.")
             parts = content.split('\n\n')
             valid_parts = [p.strip() for p in parts if p.strip()]
             if len(valid_parts) > 0:
                 for i, part_text in enumerate(valid_parts):
                     # This ID generation must match ner_processor.py's fallback
                     vignettes[f"Vignette_{i+1}"] = part_text
             elif content.strip(): # Single block of text if no other splitting worked
                 vignettes["Vignette_1"] = content.strip()


        if not vignettes:
            print(f"Warning: No vignettes were loaded from {file_path}. The file might be empty or in an unexpected format.")

    except FileNotFoundError:
        print(f"Error: Vignettes file not found at {file_path}")
        return None
    except Exception as e:
        print(f"Error loading vignettes from {file_path}: {e}")
        return None

    print(f"Loaded {len(vignettes)} vignettes from {file_path} for evaluation context.")
    return vignettes


def main():
    parser = argparse.ArgumentParser(description="Evaluate NER outputs against a critical lexicon.")
    parser.add_argument("--lexicon_file", default="output/critical_lexicon.json", help="Path to the critical lexicon JSON file.")
    parser.add_argument("--ner_outputs_file", default="output/ner_outputs.json", help="Path to the NER outputs JSON file.")
    parser.add_argument("--vignettes_file", default="data/vignettes.txt", help="Path to the original vignettes text file.")
    args = parser.parse_args()

    lexicon = load_json_file(args.lexicon_file, "lexicon")
    ner_outputs = load_json_file(args.ner_outputs_file, "NER outputs")
    # Load original vignettes using the evaluator's own loader
    # This ensures vignette_ids can be matched if ner_processor produced them.
    raw_vignettes_map = load_vignettes_for_evaluator(args.vignettes_file)

    if not lexicon or not ner_outputs or not raw_vignettes_map:
        print("Exiting due to errors loading input files (lexicon, NER outputs, or vignettes). Check paths and file integrity.")
        return

    lex_keywords = set(normalize_text(k) for k in lexicon.get("keywords", []))
    lex_key_phrases = set(normalize_text(p) for p in lexicon.get("key_phrases", []))
    # For numerical patterns, we match the exact "text" field after normalization for simplicity here
    lex_numerical_patterns_text = set(normalize_text(p["text"]) for p in lexicon.get("numerical_patterns", []))

    for model_config_name, model_results in ner_outputs.items():
        print(f"\nEvaluation Report for NER Model/Config: {model_config_name}")
        print("--------------------------------------------------")

        total_vignettes_in_ner_output = len(model_results)
        if total_vignettes_in_ner_output == 0: print("No vignettes processed by this model."); continue

        m_total_kw_matches, m_total_kp_matches, m_total_num_matches = 0, 0, 0
        m_total_lex_terms_in_vignettes, m_total_lex_terms_found_by_ner = 0, 0
        m_matched_term_labels = defaultdict(Counter)
        m_missed_lex_terms = Counter()

        vignettes_actually_evaluated_count = 0
        for vignette_id, ner_entities in model_results.items():
            original_vignette_text_raw = raw_vignettes_map.get(vignette_id)
            if not original_vignette_text_raw:
                # print(f"Warning: Original text for vignette '{vignette_id}' not found in loaded vignettes. Skipping its detailed analysis.")
                continue # Skip this vignette if its original text is missing for coverage

            vignettes_actually_evaluated_count +=1
            original_vignette_text_norm = normalize_text(original_vignette_text_raw)
            ner_entity_texts_norm = [normalize_text(e.get("text","")) for e in ner_entities] # Ensure e["text"] exists

            # 1. Direct Lexicon Match Analysis
            for i, ent_text_norm in enumerate(ner_entity_texts_norm):
                entity_original_label = ner_entities[i].get("label", "NOLABEL")
                if ent_text_norm in lex_keywords:
                    m_total_kw_matches += 1; m_matched_term_labels[ent_text_norm].update([entity_original_label])
                if ent_text_norm in lex_key_phrases:
                    m_total_kp_matches += 1; m_matched_term_labels[ent_text_norm].update([entity_original_label])
                if ent_text_norm in lex_numerical_patterns_text:
                    m_total_num_matches += 1; m_matched_term_labels[ent_text_norm].update([entity_original_label])

            # 2. Lexicon Term Coverage in Vignette
            current_vignette_lex_terms = set()
            for term_set in [lex_keywords, lex_key_phrases, lex_numerical_patterns_text]:
                for term in term_set:
                    if term in original_vignette_text_norm: # Check if term is present in the normalized original text
                        current_vignette_lex_terms.add(term)

            m_total_lex_terms_in_vignettes += len(current_vignette_lex_terms)
            for term in current_vignette_lex_terms:
                if term in ner_entity_texts_norm: m_total_lex_terms_found_by_ner += 1
                else: m_missed_lex_terms[term] += 1

        print(f"  Vignettes Evaluated (where original text was found): {vignettes_actually_evaluated_count} / {total_vignettes_in_ner_output}")
        if vignettes_actually_evaluated_count == 0 and total_vignettes_in_ner_output > 0:
            print("  NOTE: No vignettes could be evaluated for coverage due to mismatch in vignette IDs or missing original texts.")

        print(f"  Direct Lexicon Matches by NER:")
        print(f"    - Keyword Matches: {m_total_kw_matches}")
        print(f"    - Key Phrase Matches: {m_total_kp_matches}")
        print(f"    - Numerical Pattern Matches (textual): {m_total_num_matches}")

        coverage = (m_total_lex_terms_found_by_ner / m_total_lex_terms_in_vignettes * 100) if m_total_lex_terms_in_vignettes > 0 else 0
        print(f"  Lexicon Term Coverage (based on {vignettes_actually_evaluated_count} vignettes):")
        print(f"    - Terms Present in Vignettes: {m_total_lex_terms_in_vignettes}")
        print(f"    - Terms Found by NER: {m_total_lex_terms_found_by_ner}")
        print(f"    - Coverage Percentage: {coverage:.2f}%")

        if m_missed_lex_terms:
            print(f"  Top 5 Missed Lexicon Terms (present in vignettes, not extracted by NER):")
            for term, count in m_missed_lex_terms.most_common(5): print(f"    - '{term}': missed {count} times")

        if m_matched_term_labels:
            matched_term_counts = Counter({term: sum(labels.values()) for term, labels in m_matched_term_labels.items()})
            print(f"  Label Distribution for Top 3 Most Matched Lexicon Terms:")
            for term, total_matches in matched_term_counts.most_common(3):
                label_dist_str = ", ".join([f"'{lbl}':{cnt}" for lbl, cnt in m_matched_term_labels[term].most_common(3)])
                print(f"    - Term '{term}' (matched {total_matches} times): Labels {{ {label_dist_str} }}")
        print("--------------------------------------------------")

if __name__ == "__main__":
    main()
