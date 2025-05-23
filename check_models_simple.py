#!/usr/bin/env python
import os
import re
from pathlib import Path

def check_model_for_specd(model_path):
    """Check if a model is likely compatible with speculative decoding based on its name."""
    filename = os.path.basename(model_path).lower()
    
    print(f"\nAnalyzing model: {os.path.basename(model_path)}")
    print("-" * 60)
    
    # Check for known compatible architectures in filename
    compatible_archs = ['llama', 'mistral', 'mixtral', 'gemma', 'medgemma', 'phi']
    
    model_family = None
    for arch in compatible_archs:
        if arch in filename:
            model_family = arch
            break
    
    if model_family:
        print(f"Detected model family: {model_family}")
        
        # Determine model size if possible
        size_match = re.search(r'(\d+)b', filename)
        model_size = size_match.group(1) if size_match else "unknown"
        if model_size != "unknown":
            print(f"Approximate model size: {model_size}B parameters")
        
        # Check quantization
        quant_level = None
        if 'q4_k' in filename:
            quant_level = "Q4_K (4-bit, good balance of quality and speed)"
        elif 'q5_k' in filename:
            quant_level = "Q5_K (5-bit, better quality, slightly slower)"
        elif 'q8_0' in filename:
            quant_level = "Q8_0 (8-bit, highest quality, slower)"
        elif 'f16' in filename:
            quant_level = "F16 (16-bit, highest quality, slowest)"
        
        if quant_level:
            print(f"Quantization: {quant_level}")
        
        # Determine compatibility and good draft model candidates
        print("\n✅ This model's architecture supports speculative decoding")
        
        # Suggest draft models based on architecture
        if model_family == 'medgemma':
            if model_size != "unknown" and int(model_size) > 7:
                print(f"Recommended draft model: A smaller MedGemma model (e.g., MedGemma-4B)")
            else:
                print(f"This model could serve as a draft model for larger MedGemma models")
        
        elif model_family == 'mistral' or model_family == 'mixtral':
            if 'mixtral' in filename and 'mistral' in filename:
                print(f"Recommended draft model: A Mistral-7B model for this Mixtral model")
            elif 'mistral' in filename and '7b' in filename:
                print(f"This model could serve as a draft model for Mixtral models")
                
        elif model_family == 'llama':
            if model_size != "unknown" and int(model_size) > 13:
                print(f"Recommended draft model: A smaller Llama model (e.g., Llama-7B)")
            else:
                print(f"This model could serve as a draft model for larger Llama models")
                
        return True, model_family
    else:
        print("❓ Could not determine model architecture from filename")
        print("This model may or may not support speculative decoding")
        print("Testing would be required to determine compatibility")
        return False, None

def main():
    models_dir = '/Users/derek/.lmstudio/models'
    gguf_files = []
    
    print("Searching for GGUF models in LM Studio directory...")
    
    # Find all GGUF models
    for root, _, files in os.walk(models_dir):
        for file in files:
            if file.endswith('.gguf'):
                gguf_files.append(os.path.join(root, file))
    
    if not gguf_files:
        print("No GGUF models found in the LM Studio directory.")
        return
    
    print(f"Found {len(gguf_files)} GGUF models")
    print("Analyzing compatibility with speculative decoding...")
    
    # Analyze models
    compatible_models = []
    model_families = {}
    
    for model_path in gguf_files:
        compatible, family = check_model_for_specd(model_path)
        if compatible:
            model_name = os.path.basename(model_path)
            compatible_models.append(model_name)
            if family:
                if family not in model_families:
                    model_families[family] = []
                model_families[family].append(model_name)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Summary: {len(compatible_models)}/{len(gguf_files)} models are likely compatible with speculative decoding")
    
    if model_families:
        print("\nModels by architecture family:")
        for family, models in model_families.items():
            print(f"\n{family.upper()} family models:")
            for model in models:
                print(f"- {model}")
    
    print("\nSpeculative Decoding Recommendations:")
    print("1. Pair models from the same architecture family (e.g., MedGemma with MedGemma)")
    print("2. Use a smaller model as the draft model for a larger model")
    print("3. Start with 8-10 draft tokens for models up to 13B, fewer for larger models")
    print("4. Draft temperature around 0.7-0.8 works well for medical domains")
    print("5. Both models should use the same tokenizer or vocabulary")
    
    print("\nRecommended pairings from your models:")
    if 'medgemma' in model_families and len(model_families['medgemma']) >= 2:
        med_models = model_families['medgemma']
        models_with_size = []
        for model in med_models:
            size_match = re.search(r'(\d+)b', model.lower())
            if size_match:
                size = int(size_match.group(1))
                models_with_size.append((model, size))
        
        if models_with_size:
            models_with_size.sort(key=lambda x: x[1])
            if len(models_with_size) >= 2:
                print(f"- Main model: {models_with_size[-1][0]}")
                print(f"  Draft model: {models_with_size[0][0]}")
    
    print("\nTo enable in LM Studio:")
    print("1. In Settings > Generation, enable 'Speculative Decoding'")
    print("2. Select a compatible draft model from the dropdown")
    print("3. Set draft_tokens and draft_temperature")
    print("4. Test different settings to find the optimal balance")

if __name__ == "__main__":
    main()
