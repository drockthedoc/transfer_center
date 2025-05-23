#!/usr/bin/env python
import os
import sys
import gguf
import argparse
import re
from pathlib import Path

def check_model_compatibility(model_path):
    """Check if a GGUF model is compatible with speculative decoding."""
    print(f"\nAnalyzing model: {os.path.basename(model_path)}")
    print("-" * 60)
    
    try:
        # Load the model and examine its properties
        reader = gguf.Reader(model_path)
        
        # Get metadata
        arch = None
        model_family = None
        context_length = None
        
        # Try to determine model type from metadata or filename
        for k, v in reader.fields.items():
            if isinstance(k, str) and 'architecture' in k:
                arch = str(v)
                print(f"Found architecture field: {k} = {v}")
            if isinstance(k, str) and 'context_length' in k:
                context_length = v
                print(f"Found context length: {k} = {v}")
        
        # If no architecture found in metadata, try to infer from filename
        if not arch:
            filename = os.path.basename(model_path).lower()
            if any(name in filename for name in ['llama', 'mistral', 'mixtral', 'gemma', 'medgemma', 'phi']):
                for name in ['llama', 'mistral', 'mixtral', 'gemma', 'medgemma', 'phi']:
                    if name in filename:
                        model_family = name
                        break
        else:
            model_family = arch
        
        # Print tensor info
        print(f"Model family (detected): {model_family}")
        print(f"Context length: {context_length}")
        
        # Print metadata fields
        print("\nMetadata fields:")
        metadata_count = 0
        for k, v in reader.fields.items():
            if metadata_count < 10:  # Limit to 10 fields to avoid flooding output
                print(f"  {k}: {v}")
                metadata_count += 1
            else:
                print(f"  ... and {len(reader.fields) - 10} more fields")
                break
        
        # Check tensor data
        tensors = reader.tensors
        
        # Print number of tensors and first few names
        print(f"\nTotal tensors: {len(tensors)}")
        print("Sample tensor names:")
        tensor_count = 0
        for name, tensor in tensors.items():
            if tensor_count < 5:  # Limit to 5 tensors
                print(f"  - {name} (shape: {tensor.shape}, type: {tensor.tensor_type})")
                tensor_count += 1
            else:
                break
        
        # Speculative decoding compatibility check
        compatible = False
        
        # Check architecture compatibility
        if model_family and model_family.lower() in ['llama', 'mistral', 'mixtral', 'gemma', 'medgemma', 'phi']:
            # These architectures generally support speculative decoding with proper draft models
            compatible = True
            print("\n✅ This model's architecture supports speculative decoding")
            print("   For best results, use with a compatible draft model of the same architecture family")
        else:
            if model_family:
                print(f"\n❓ The model family '{model_family}' may or may not support speculative decoding")
                print("   Testing would be required to confirm compatibility")
            else:
                print("\n❓ Could not determine model architecture")
                print("   Examine the model file name and metadata to make a determination")
        
        # Additional notes
        if compatible:
            if 'medgemma' in model_path.lower():
                print("\nSpecial notes:")
                print("- MedGemma models work well with speculative decoding when paired with a matching draft model")
                print("- For best results, use a smaller MedGemma model as the draft model")
            
            if re.search(r'q4_k', model_path.lower()):
                print("\nQuantization note:")
                print("- Q4_K quantization is good for balance of quality and speed with speculative decoding")
        
        return compatible
        
    except Exception as e:
        print(f"Error analyzing model: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Check GGUF models for speculative decoding compatibility')
    parser.add_argument('--model_dir', type=str, default='/Users/derek/.lmstudio/models',
                        help='Directory containing GGUF models')
    parser.add_argument('--max_models', type=int, default=5,
                        help='Maximum number of models to check')
    parser.add_argument('--specific_model', type=str, default=None,
                        help='Check a specific model file (provide full path)')
    
    args = parser.parse_args()
    
    # Check a specific model if provided
    if args.specific_model:
        if os.path.exists(args.specific_model) and args.specific_model.endswith('.gguf'):
            check_model_compatibility(args.specific_model)
            print("\nSpeculative Decoding Setup Tips:")
            print("1. For optimal performance, use a smaller model of the same architecture as the draft model")
            print("2. Ensure both models use the same tokenizer or are from the same model family")
            print("3. Set appropriate draft_tokens (8-10 for 13B or smaller models)")
            print("4. Adjust draft_temperature (0.7-0.8 works well) to balance speed and quality")
            return
        else:
            print(f"Error: Specified model '{args.specific_model}' does not exist or is not a GGUF file")
            return
    
    # Find all GGUF models
    model_dir = Path(args.model_dir)
    gguf_files = []
    
    for root, _, files in os.walk(model_dir):
        for file in files:
            if file.endswith('.gguf'):
                gguf_files.append(os.path.join(root, file))
    
    print(f"Found {len(gguf_files)} GGUF models")
    print("Checking compatibility with speculative decoding...")
    
    # Check each model, up to the max_models limit
    compatible_models = []
    potential_compatible_models = []
    
    for i, model_path in enumerate(gguf_files[:args.max_models]):
        is_compatible = check_model_compatibility(model_path)
        if is_compatible:
            compatible_models.append(os.path.basename(model_path))
        elif any(name in model_path.lower() for name in ['llama', 'mistral', 'mixtral', 'gemma', 'medgemma', 'phi']):
            potential_compatible_models.append(os.path.basename(model_path))
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Summary: {len(compatible_models)}/{min(len(gguf_files), args.max_models)} models are confirmed compatible with speculative decoding")
    
    if compatible_models:
        print("\nCompatible models:")
        for model in compatible_models:
            print(f"- {model}")
    
    if potential_compatible_models:
        print("\nPotentially compatible models (based on naming):")
        for model in potential_compatible_models:
            print(f"- {model}")
    
    print("\nSpeculative Decoding Setup Tips:")
    print("1. For optimal performance, use a smaller model of the same architecture as the draft model")
    print("2. Ensure both models use the same tokenizer or are from the same model family")
    print("3. Set appropriate draft_tokens (8-10 for 13B or smaller models)")
    print("4. Adjust draft_temperature (0.7-0.8 works well) to balance speed and quality")
    print("\nRecommended Combinations:")
    print("- Main model: MedGemma-27B, Draft model: MedGemma-4B")
    print("- Main model: Mixtral-8x7B, Draft model: Mistral-7B")
    print("- Main model: Llama3-70B, Draft model: Llama3-8B")
    
    print("\nSpeculative Decoding Configuration in LM Studio:")
    print("1. In Settings > Generation, enable 'Speculative Decoding'")
    print("2. Select a compatible draft model")
    print("3. Configure draft_tokens and draft_temperature")
    print("4. Test performance with various settings to find the optimal balance")

    
if __name__ == "__main__":
    main()
