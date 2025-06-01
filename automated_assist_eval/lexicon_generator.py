import json
import argparse
import re
from collections import Counter

# Placeholder for stop words, if we decide to use them.
# For clinical text, it's often better to be conservative with stop words.
# This list is an initial broad set, might need refinement or removal based on results.
STOP_WORDS = set([
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "for", "to", "with",
    "is", "are", "was", "were", "be", "been", "being", "as", "by", "if",
    "requires", "requiring", "unless", "prior", "approval", "current",
    "level", "care", "services", "provided", "coverage", "only", "non", "hrs", "hr",
    "without", "expected", "imminent", "improvement", "max", "flow", "size",
    "q1", "q2", "under", "evidence", "suspicion", "need", "needs", "new", "diagnosis",
    "risk", "ongoing", "monitoring", "intervention", "confirmed", "concern", "patients",
    "patient", "pt", "mos", "wks", "yrs", "etc", "from", "will", "should", "all", "any",
    "not", "no", "other", "status", "post", "due", "pending"
])

def find_criteria_strings(data_node):
    """
    Recursively traverses the JSON data to find all strings
    within lists keyed by 'exclusions' or 'general_exclusions'.
    Also includes strings from 'ac_exclusion_picu_accept' for the community campus,
    and 'accept' and 'clinical_team_decision' as they might contain relevant terms.
    """
    criteria = []
    if isinstance(data_node, dict):
        for key, value in data_node.items():
            # Added more keys that might contain relevant phrases/terms
            if key in ["exclusions", "general_exclusions", "ac_exclusion_picu_accept", "accept", "clinical_team_decision", "notes"]:
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            criteria.append(item)
                elif isinstance(value, str): # Sometimes a single string, not a list
                     criteria.append(value)
            elif isinstance(value, (dict, list)):
                criteria.extend(find_criteria_strings(value))
    elif isinstance(data_node, list):
        for item in data_node:
            criteria.extend(find_criteria_strings(item))
    # Remove duplicates at the source
    return sorted(list(set(criteria)))


def normalize_text(text):
    return text.lower()

def extract_keywords(text, stop_words=None):
    """
    Normalizes text, tokenizes by splitting on non-alphanumeric characters (keeping internal hyphens in words),
    and optionally removes stop words.
    """
    text_lower = normalize_text(text)
    # Regex to find words, allowing internal hyphens, excluding purely numeric tokens here
    tokens = re.findall(r'\b[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]\b|\b[a-zA-Z]\b', text_lower)

    keywords = [token for token in tokens if token and len(token) > 1]
    if stop_words:
        keywords = [word for word in keywords if word not in stop_words and word not in ["score"]] # also exclude 'score' if it's standalone
    return list(set(keywords))

def extract_key_phrases(text, n_values=(2, 3), stop_words=None):
    """
    Extracts n-grams (bi-grams and tri-grams by default) as key phrases.
    Text is normalized first. Filters out phrases composed entirely of stop words.
    """
    text_lower = normalize_text(text)
    words = re.findall(r'\b[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]\b|\b[a-zA-Z0-9]\b', text_lower) # include numbers in words for phrases

    phrases = []
    for n in n_values:
        for i in range(len(words) - n + 1):
            phrase_candidate_words = words[i:i+n]
            # Filter out phrases if all words are stop words (unless it's a short phrase like "q1-2")
            if stop_words and n > 1: # for n=1 (single words), keyword extraction handles it
                if all(word in stop_words for word in phrase_candidate_words):
                    continue

            # Avoid phrases that are just numbers (numerical patterns will catch these)
            if all(word.isdigit() for word in phrase_candidate_words):
                continue

            phrase = " ".join(phrase_candidate_words)
            phrases.append(phrase)

    return list(set(phrases))


def extract_numerical_patterns(text_input, original_criterion_context):
    patterns = []
    text = text_input # Use original casing for extracting the 'text' field, but lowercase for matching

    # Regex for various numerical patterns
    # 1. Comparisons with optional units: e.g., <2.5 kg, >=6, <9 (non-trauma), >60 cc/kg, score >=6
    # Operator, value, optional unit
    # Added 'score' to operator part, and handling for unicode operators
    regex_comparison = r"""
        (?:(?:crs\s*[-]?\s*)?score\s*)?                    # Optional "CRS [-] Score " prefix
        (>=|<=|>|<|≥|≤)                                       # Operator
        \s*
        (\d+(?:\.\d+)?)                                    # Number (integer or float)
        \s*
        (kg|cc/kg|days|hours|mos|wks|yrs|f|g/dl|cc|mg|mmhg|bpm|percent)? # Optional common units
        (?:\s*\(?[^)]*\)?)?                                # Optional context in parentheses
    """
    for match in re.finditer(regex_comparison, text, re.IGNORECASE | re.VERBOSE):
        matched_text = match.group(0)
        operator_orig, value_str, unit = match.groups()[0:3] # operator, value, unit
        operator = operator_orig.replace('≥','>=').replace('≤','<=')
        try:
            value = float(value_str)
            patterns.append({
                "text": matched_text.strip(), "type": "comparison", "operator": operator,
                "value": value, "unit": unit if unit else None,
                "original_criterion_context": original_criterion_context
            })
        except ValueError:
            print(f"Warning (comparison): Could not parse value '{value_str}' in: {matched_text}")

    # 2. Ranges: e.g., 4-5, 10-14 (often with context like "Score 4-5")
    # Number, hyphen, number
    regex_range = r"""
        (?:score\s+|cs\s*)?                                 # Optional "Score " or "CS " (for CRS Score)
        (\d+(?:\.\d+)?)                                    # First number
        \s*-\s*
        (\d+(?:\.\d+)?)                                    # Second number
        (?:\s*\(?[^)]*\)?)?                                # Optional context
    """
    for match in re.finditer(regex_range, text, re.IGNORECASE | re.VERBOSE):
        # Avoid matching parts of dates like "2024-v1" or version numbers
        pre_char_idx = match.start() - 1
        if pre_char_idx >= 0 and text[pre_char_idx].isalnum() and not text[pre_char_idx].isspace():
            if not (text[pre_char_idx-1:pre_char_idx+1].lower() == "q1" or text[pre_char_idx-1:pre_char_idx+1].lower() == "q2"): # allow q1-2, q2-4 etc.
                continue

        matched_text = match.group(0)
        val1_str, val2_str = match.groups()[0:2]
        try:
            val1 = float(val1_str)
            val2 = float(val2_str)
            patterns.append({
                "text": matched_text.strip(), "type": "range",
                "values": sorted([val1, val2]),
                "original_criterion_context": original_criterion_context
            })
        except ValueError:
            print(f"Warning (range): Could not parse values '{val1_str}', '{val2_str}' in: {matched_text}")

    # 3. Specific "qX-Y" or "qX hr" type patterns for frequency: e.g., q1-2, q2 hr, q1h, q2h
    regex_frequency = r"""
        (q\d+(?:-\d+)?(?:h|hr|hrs)?)                        # qX, qX-Y, qXh, qXhr, qX-Yh etc.
        (?:\s*(?:assessments|treatments|temp|checks|blood|draws))? # Optional context words
    """
    for match in re.finditer(regex_frequency, text, re.IGNORECASE | re.VERBOSE):
        matched_text = match.group(0)
        freq_pattern = match.group(1)
        patterns.append({
            "text": matched_text.strip(), "type": "frequency",
            "pattern": freq_pattern,
            "original_criterion_context": original_criterion_context
        })

    # 4. Number with unit, not explicitly comparison/range (more generic measurement)
    # Ensure it's not already captured by a comparison regex if it starts with an operator
    regex_measurement = r"""
        (?<![><=≥≤])(?:(?<![><=≥≤]\s))                      # Negative lookbehind for comparison operators
        (\d+(?:\.\d+)?)                                  # Number
        \s+
        (kg|cc/kg|days|hours|mos|wks|yrs|f|g/dl|cc|mg|mmhg|bpm|percent|%) # Common units
        (?!\s*-\s*\d)                                    # Negative lookahead for ranges
    """
    current_pattern_texts = [p["text"].lower() for p in patterns]
    for match in re.finditer(regex_measurement, text, re.IGNORECASE | re.VERBOSE):
        matched_text = match.group(0).strip()
        if matched_text.lower() in current_pattern_texts: # Avoid double capture from more specific regex
            continue

        value_str, unit = match.groups()[0:2]
        try:
            value = float(value_str)
            patterns.append({
                "text": matched_text, "type": "measurement", "value": value, "unit": unit,
                "original_criterion_context": original_criterion_context
            })
            current_pattern_texts.append(matched_text.lower())
        except ValueError:
            print(f"Warning (measurement): Could not parse value '{value_str}' in: {matched_text}")

    # Deduplicate patterns based on 'text' field for *this specific criterion string*
    unique_patterns_for_criterion = []
    seen_texts_for_criterion = set()
    for p in patterns:
        if p["text"].lower() not in seen_texts_for_criterion: # Use lower for seen check
            unique_patterns_for_criterion.append(p)
            seen_texts_for_criterion.add(p["text"].lower())

    return unique_patterns_for_criterion


def main():
    parser = argparse.ArgumentParser(description="Generate a lexicon from clinical exclusion criteria JSON.")
    parser.add_argument("--input_json", default="data/criteria.json", help="Path to the input criteria JSON file.")
    parser.add_argument("--output_lexicon", default="output/critical_lexicon.json", help="Path to save the generated lexicon JSON file.")
    parser.add_argument("--use_stop_words", action="store_true", help="Enable stop word removal for keywords and key_phrases.")
    args = parser.parse_args()

    active_stop_words = STOP_WORDS if args.use_stop_words else None
    if args.use_stop_words:
        print("Stop word removal is ENABLED.")
    else:
        print("Stop word removal is DISABLED.")

    print(f"Loading criteria from: {args.input_json}")
    try:
        with open(args.input_json, 'r') as f:
            criteria_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input JSON file not found at {args.input_json}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {args.input_json}")
        return

    all_criteria_strings = find_criteria_strings(criteria_data)
    print(f"Found {len(all_criteria_strings)} unique criteria strings to process.")
    if not all_criteria_strings:
        print("No criteria strings found. Exiting.")
        return

    lexicon = {"keywords": set(), "key_phrases": set(), "numerical_patterns": [] }

    for i, criterion_text in enumerate(all_criteria_strings):
        # print(f"Processing criterion {i+1}/{len(all_criteria_strings)}: {criterion_text[:100]}...") # Verbose
        current_keywords = extract_keywords(criterion_text, stop_words=active_stop_words)
        lexicon["keywords"].update(current_keywords)

        current_key_phrases = extract_key_phrases(criterion_text, stop_words=active_stop_words)
        lexicon["key_phrases"].update(current_key_phrases)

        current_numerical_patterns = extract_numerical_patterns(criterion_text, criterion_text)
        lexicon["numerical_patterns"].extend(current_numerical_patterns)

    lexicon["keywords"] = sorted(list(lexicon["keywords"]))
    lexicon["key_phrases"] = sorted(list(lexicon["key_phrases"]))

    # Global deduplication of numerical_patterns: if two different criteria strings produce
    # the exact same numerical pattern (text, type, values, etc.), only keep one.
    # This is reasonable as the evaluator will match against these unique patterns.
    # The original_criterion_context can list multiple if needed, or we pick the first.
    # For now, simple deduplication based on the string representation of the pattern dict.
    # More robust: tuple of key items.

    unique_numerical_patterns_globally = []
    seen_numerical_pattern_reprs = set()
    for p in lexicon["numerical_patterns"]:
        # Create a canonical representation for checking duplicates
        # Exclude original_criterion_context for global deduplication purpose
        p_repr_items = (p["text"], p["type"], p.get("operator"), tuple(sorted(p.get("values", []))) if p.get("values") else None, p.get("value"), p.get("unit"), p.get("pattern"))
        p_repr = str(p_repr_items)
        if p_repr not in seen_numerical_pattern_reprs:
            unique_numerical_patterns_globally.append(p)
            seen_numerical_pattern_reprs.add(p_repr)
    lexicon["numerical_patterns"] = unique_numerical_patterns_globally

    print(f"Generated lexicon with {len(lexicon['keywords'])} keywords, {len(lexicon['key_phrases'])} key phrases, and {len(lexicon['numerical_patterns'])} numerical_patterns.")

    print(f"Saving lexicon to: {args.output_lexicon}")
    try:
        with open(args.output_lexicon, 'w') as f:
            json.dump(lexicon, f, indent=2)
        print("Lexicon saved successfully.")
    except IOError:
        print(f"Error: Could not write lexicon to {args.output_lexicon}")

if __name__ == "__main__":
    main()
