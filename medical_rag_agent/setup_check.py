#!/usr/bin/env python3
"""
Setup verification script for Medical RAG Agent.

This script checks if all dependencies are properly installed and
provides helpful error messages if they're missing.
"""

import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    try:
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"❌ Python {version.major}.{version.minor} detected. Python 3.8+ is required.")
            return False
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible.")
        return True
    except Exception as e:
        print(f"❌ Error checking Python version: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    dependencies = [
        ('python-dotenv', 'dotenv'),
        ('langchain', 'langchain'),
        ('langchain-openai', 'langchain_openai'),
        ('langchain-core', 'langchain_core'),
        ('llama-index', 'llama_index'),
        ('llama-index-core', 'llama_index.core'),
        ('faiss-cpu', 'faiss'),
        ('sentence-transformers', 'sentence_transformers'),
        ('transformers', 'transformers'),
        ('torch', 'torch'),
        ('pypdf2', 'PyPDF2')
    ]
    
    missing = []
    installed = []
    
    for package_name, import_name in dependencies:
        try:
            __import__(import_name)
            installed.append(package_name)
            print(f"✅ {package_name}")
        except ImportError:
            missing.append(package_name)
            print(f"❌ {package_name}")
    
    return missing, installed

def main():
    """Main setup verification function."""
    print("🔍 Medical RAG Agent Setup Verification")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    print("\n📦 Checking Dependencies:")
    print("-" * 30)
    
    missing, installed = check_dependencies()
    
    print(f"\n📊 Summary:")
    print(f"  ✅ Installed: {len(installed)} packages")
    print(f"  ❌ Missing: {len(missing)} packages")
    
    if missing:
        print(f"\n🔧 To install missing dependencies, run:")
        print(f"   pip install {' '.join(missing)}")
        print(f"\n   Or install all at once:")
        print(f"   pip install -r requirements.txt")
        
        print(f"\n💡 If you encounter issues:")
        print(f"   1. Make sure you're using a virtual environment")
        print(f"   2. Update pip: python -m pip install --upgrade pip")
        print(f"   3. For Apple Silicon Macs, you might need:")
        print(f"      pip install torch --index-url https://download.pytorch.org/whl/cpu")
        
        return False
    else:
        print(f"\n🎉 All dependencies are installed!")
        
        # Test basic imports
        print(f"\n🧪 Testing basic imports:")
        try:
            # Add src directory to Python path for imports
            src_path = str(Path(__file__).parent / 'src')
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
            
            from config import initialize_medical_rag_config
            print("✅ Configuration system")
            
            from agent.prompts import MEDICAL_AGENT_SYSTEM_PROMPT
            print("✅ Agent prompts")
            
            print(f"\n✅ Basic functionality tests passed!")
            
        except Exception as e:
            print(f"❌ Import test failed: {e}")
            print(f"   This might be normal if you haven't installed all dependencies yet.")
            return False
        
        return True

if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n🚀 Setup verification completed successfully!")
        print(f"   You can now run the medical RAG agent.")
    else:
        print(f"\n⚠️  Setup verification failed.")
        print(f"   Please install missing dependencies before proceeding.")
        sys.exit(1)
