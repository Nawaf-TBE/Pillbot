#!/usr/bin/env python3
"""
Installation Test Script for PriorAuthAutomation

This script verifies that all required dependencies are properly installed,
especially Tesseract OCR which is a system-level dependency.
"""

import sys
import os
from pathlib import Path

def test_python_imports():
    """Test that all required Python packages can be imported."""
    print("🐍 Testing Python Package Imports")
    print("-" * 40)
    
    required_packages = [
        ("pypdf", "pypdf"),
        ("pytesseract", "pytesseract"),
        ("cv2", "opencv-python"),
        ("PIL", "Pillow"),
        ("fitz", "PyMuPDF"),
        ("requests", "requests"),
        ("dotenv", "python-dotenv"),
        ("reportlab", "reportlab")
    ]
    
    failed_imports = []
    
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print(f"✅ {package_name}")
        except ImportError as e:
            print(f"❌ {package_name} - {e}")
            failed_imports.append(package_name)
    
    if failed_imports:
        print(f"\n⚠️  Missing packages: {', '.join(failed_imports)}")
        print("Install with: pip install " + " ".join(failed_imports))
        return False
    else:
        print("\n✅ All Python packages are installed!")
        return True

def test_tesseract_installation():
    """Test that Tesseract OCR is properly installed and accessible."""
    print("\n🔍 Testing Tesseract OCR Installation")
    print("-" * 40)
    
    try:
        import pytesseract
        
        # Test 1: Get Tesseract version
        try:
            version = pytesseract.get_tesseract_version()
            print(f"✅ Tesseract version: {version}")
        except Exception as e:
            print(f"❌ Cannot get Tesseract version: {e}")
            print("   Make sure Tesseract is installed:")
            print("   - macOS: brew install tesseract")
            print("   - Ubuntu: sudo apt-get install tesseract-ocr")
            print("   - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
            return False
        
        # Test 2: Get available languages
        try:
            languages = pytesseract.get_languages()
            print(f"✅ Available languages: {len(languages)} languages")
            print(f"   Languages: {', '.join(languages[:10])}{'...' if len(languages) > 10 else ''}")
        except Exception as e:
            print(f"⚠️  Cannot get language list: {e}")
        
        # Test 3: Simple OCR test
        try:
            from PIL import Image, ImageDraw, ImageFont
            import tempfile
            
            # Create a simple test image with text
            img = Image.new('RGB', (300, 100), color='white')
            d = ImageDraw.Draw(img)
            d.text((10, 30), "TEST OCR 123", fill='black')
            
            # Save temporarily and test OCR
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                img.save(tmp_file.name)
                
                # Perform OCR
                text = pytesseract.image_to_string(img)
                
                # Clean up
                os.unlink(tmp_file.name)
                
                if "TEST" in text.upper() or "OCR" in text.upper():
                    print("✅ OCR functionality test passed")
                    print(f"   Extracted: '{text.strip()}'")
                else:
                    print(f"⚠️  OCR test unclear result: '{text.strip()}'")
        
        except Exception as e:
            print(f"⚠️  OCR functionality test failed: {e}")
        
        return True
        
    except ImportError:
        print("❌ pytesseract not installed")
        print("Install with: pip install pytesseract")
        return False

def test_optional_services():
    """Test optional services (LlamaParse, etc.)."""
    print("\n🔧 Testing Optional Services")
    print("-" * 40)
    
    # Test LlamaParse API key
    from dotenv import load_dotenv
    load_dotenv()
    
    llamaparse_key = os.getenv("LLAMAPARSE_API_KEY")
    if llamaparse_key:
        print("✅ LLAMAPARSE_API_KEY found in environment")
        try:
            import llama_parse
            print("✅ llama-parse package installed")
        except ImportError:
            print("⚠️  llama-parse package not installed")
            print("   Install with: pip install llama-parse")
    else:
        print("⚠️  LLAMAPARSE_API_KEY not found in environment")
        print("   Set in .env file for document parsing functionality")
    
    return True

def test_project_structure():
    """Test that the project structure is correct."""
    print("\n📁 Testing Project Structure")
    print("-" * 40)
    
    required_paths = [
        "src/",
        "src/services/",
        "src/services/ocr_service.py",
        "src/services/pdf_utils.py",
        "src/services/data_store.py",
        "src/main.py",
        "requirements.txt"
    ]
    
    missing_paths = []
    
    for path in required_paths:
        if os.path.exists(path):
            print(f"✅ {path}")
        else:
            print(f"❌ {path}")
            missing_paths.append(path)
    
    if missing_paths:
        print(f"\n⚠️  Missing files/directories: {', '.join(missing_paths)}")
        return False
    else:
        print("\n✅ Project structure is correct!")
        return True

def run_sample_test():
    """Run a quick sample test of the OCR service."""
    print("\n🧪 Running Sample OCR Test")
    print("-" * 40)
    
    try:
        # Add src to path
        sys.path.append(os.path.join(os.getcwd(), 'src'))
        
        from services.ocr_service import check_ocr_availability, get_ocr_service_info
        
        # Check availability
        if check_ocr_availability():
            print("✅ OCR service is available")
            
            # Get service info
            info = get_ocr_service_info()
            print(f"   Service: {info.get('service', 'Unknown')}")
            print(f"   Status: {info.get('status', 'Unknown')}")
            print(f"   Version: {info.get('version', 'Unknown')}")
            
            return True
        else:
            print("❌ OCR service is not available")
            return False
            
    except Exception as e:
        print(f"❌ Sample test failed: {e}")
        return False

def main():
    """Run all installation tests."""
    print("🔧 PriorAuthAutomation Installation Test")
    print("=" * 50)
    
    tests = [
        ("Python Imports", test_python_imports),
        ("Tesseract OCR", test_tesseract_installation),
        ("Project Structure", test_project_structure),
        ("Optional Services", test_optional_services),
        ("Sample OCR Test", run_sample_test)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test failed with error: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Installation Test Summary")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your installation is ready.")
        print("\nNext steps:")
        print("1. Set up .env file with your LlamaParse API key (optional)")
        print("2. Run: python src/main.py")
        print("3. Or run individual tests: python src/test_ocr_service.py")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("- Install missing Python packages: pip install -r requirements.txt")
        print("- Install Tesseract OCR system package")
        print("- Check project file structure")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 