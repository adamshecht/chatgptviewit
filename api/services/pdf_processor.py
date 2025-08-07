#!/usr/bin/env python3
"""
PDF Processing System
Extracts text from PDFs for AI analysis
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
import PyPDF2
import pdfplumber
from datetime import datetime

class PDFProcessor:
    """Handles PDF text extraction for agenda and property documents."""
    
    def __init__(self):
        """Initialize the PDF processor."""
        pass
    
    def extract_text_pypdf2(self, pdf_path: str) -> str:
        """
        Extract text using PyPDF2 (fast but basic).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            str: Extracted text
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
                
                return text.strip()
                
        except Exception as e:
            print(f"❌ PyPDF2 extraction failed for {pdf_path}: {e}")
            return ""
    
    def extract_text_pdfplumber(self, pdf_path: str) -> str:
        """
        Extract text using pdfplumber (better for complex layouts).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            str: Extracted text
        """
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            return text.strip()
            
        except Exception as e:
            print(f"❌ pdfplumber extraction failed for {pdf_path}: {e}")
            return ""
    
    def extract_text_hybrid(self, pdf_path: str) -> str:
        """
        Extract text using hybrid approach (try pdfplumber first, fallback to PyPDF2).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            str: Extracted text
        """
        # Try pdfplumber first (better quality)
        text = self.extract_text_pdfplumber(pdf_path)
        
        # If pdfplumber fails or returns empty, try PyPDF2
        if not text or len(text.strip()) < 50:
            print(f"⚠️  pdfplumber result poor, trying PyPDF2 for {pdf_path}")
            text = self.extract_text_pypdf2(pdf_path)
        
        return text
    
    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes, filename: str = "") -> str:
        """
        Extract text from PDF bytes (for uploaded files).
        
        Args:
            pdf_bytes: PDF file content as bytes
            filename: Optional filename for error messages
            
        Returns:
            str: Extracted text
        """
        try:
            import io
            from PyPDF2 import PdfReader
            
            # Create a file-like object from bytes
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)
            
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            
            print(f"✅ Extracted {len(text)} characters from PDF bytes ({filename})")
            return text.strip()
            
        except Exception as e:
            print(f"❌ PDF bytes extraction failed for {filename}: {e}")
            # Try with pdfplumber as fallback
            try:
                import io
                import pdfplumber
                
                pdf_file = io.BytesIO(pdf_bytes)
                text = ""
                
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                
                print(f"✅ Extracted {len(text)} characters from PDF bytes using pdfplumber ({filename})")
                return text.strip()
                
            except Exception as e2:
                print(f"❌ Both PDF extraction methods failed for {filename}: {e2}")
                return ""
    
    def process_agenda_pdf(self, pdf_path: str) -> Dict:
        """
        Process an agenda PDF and extract structured information.
        
        Args:
            pdf_path: Path to agenda PDF
            
        Returns:
            Dict: Processed agenda data
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            print(f"❌ PDF not found: {pdf_path}")
            return {}
        
        print(f"📄 Processing agenda PDF: {pdf_file.name}")
        
        # Extract text
        text = self.extract_text_hybrid(pdf_path)
        
        if not text:
            print(f"❌ No text extracted from {pdf_file.name}")
            return {}
        
        # Basic metadata
        agenda_data = {
            "filename": pdf_file.name,
            "filepath": str(pdf_file),
            "processed_date": datetime.now().isoformat(),
            "text_length": len(text),
            "page_count": self._get_page_count(pdf_path),
            "full_text": text,
            "summary": self._create_text_summary(text)
        }
        
        print(f"✅ Extracted {len(text)} characters from {pdf_file.name}")
        return agenda_data
    
    def process_property_documents(self, property_dir: str) -> Dict:
        """
        Process all PDF documents for a property.
        
        Args:
            property_dir: Path to property directory
            
        Returns:
            Dict: All property document texts organized by category
        """
        property_path = Path(property_dir)
        docs_dir = property_path / "documents"
        
        if not docs_dir.exists():
            print(f"❌ Documents directory not found: {docs_dir}")
            return {}
        
        print(f"📁 Processing property documents: {property_path.name}")
        
        property_docs = {
            "property_dir": str(property_path),
            "processed_date": datetime.now().isoformat(),
            "categories": {}
        }
        
        # Process each category
        categories = ["architectural_drawings", "site_plans", "legal_documents", "meeting_history"]
        
        for category in categories:
            cat_dir = docs_dir / category
            if not cat_dir.exists():
                continue
            
            category_docs = []
            pdf_files = list(cat_dir.glob("*.pdf"))
            
            if pdf_files:
                print(f"  📄 Processing {len(pdf_files)} {category} files...")
            
            for pdf_file in pdf_files:
                print(f"    ↳ {pdf_file.name}")
                text = self.extract_text_hybrid(str(pdf_file))
                
                if text:
                    doc_data = {
                        "filename": pdf_file.name,
                        "filepath": str(pdf_file),
                        "text_length": len(text),
                        "text": text,
                        "summary": self._create_text_summary(text, max_length=200)
                    }
                    category_docs.append(doc_data)
                    print(f"      ✅ Extracted {len(text)} characters")
                else:
                    print(f"      ❌ Failed to extract text")
            
            if category_docs:
                property_docs["categories"][category] = category_docs
        
        # Create combined text for all documents
        all_text = ""
        for category, docs in property_docs["categories"].items():
            all_text += f"\n\n=== {category.upper().replace('_', ' ')} ===\n\n"
            for doc in docs:
                all_text += f"--- {doc['filename']} ---\n"
                all_text += doc['text'] + "\n\n"
        
        property_docs["combined_text"] = all_text
        property_docs["total_text_length"] = len(all_text)
        
        print(f"✅ Property processing complete: {len(all_text)} total characters")
        return property_docs
    
    def _get_page_count(self, pdf_path: str) -> int:
        """Get the number of pages in a PDF."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages)
        except:
            return 0
    
    def _create_text_summary(self, text: str, max_length: int = 300) -> str:
        """Create a brief summary of the text."""
        if len(text) <= max_length:
            return text
        
        # Try to find a good breaking point
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        last_newline = truncated.rfind('\n')
        
        break_point = max(last_period, last_newline)
        if break_point > max_length * 0.7:  # If we found a good break point
            return truncated[:break_point + 1] + "..."
        else:
            return truncated + "..."
    
    def save_processed_data(self, data: Dict, output_path: str):
        """Save processed data to JSON file."""
        import json
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved processed data to: {output_path}")
        except Exception as e:
            print(f"❌ Error saving data: {e}")

# Global instance
pdf_processor = PDFProcessor()

def main():
    """Interactive PDF processing."""
    # processor = PDFProcessor() # This line is no longer needed as pdf_processor is global
    
    while True:
        print("\n📄 PDF Processor")
        print("1. Process single agenda PDF")
        print("2. Process property documents")
        print("3. Test PDF text extraction")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            pdf_path = input("Enter path to agenda PDF: ").strip()
            if os.path.exists(pdf_path):
                data = pdf_processor.process_agenda_pdf(pdf_path)
                if data:
                    # Save processed data
                    output_path = pdf_path.replace('.pdf', '_processed.json')
                    pdf_processor.save_processed_data(data, output_path)
                    print(f"\n📊 Summary:")
                    print(f"Text length: {data['text_length']} characters")
                    print(f"Pages: {data['page_count']}")
                    print(f"Preview: {data['summary']}")
            else:
                print("❌ File not found.")
        
        elif choice == "2":
            property_dir = input("Enter path to property directory: ").strip()
            if os.path.exists(property_dir):
                data = pdf_processor.process_property_documents(property_dir)
                if data:
                    # Save processed data
                    output_path = os.path.join(property_dir, "processed_documents.json")
                    pdf_processor.save_processed_data(data, output_path)
                    
                    print(f"\n📊 Summary:")
                    print(f"Total text: {data['total_text_length']} characters")
                    print(f"Categories processed: {len(data['categories'])}")
                    for cat, docs in data['categories'].items():
                        print(f"  - {cat}: {len(docs)} documents")
            else:
                print("❌ Directory not found.")
        
        elif choice == "3":
            pdf_path = input("Enter path to PDF for testing: ").strip()
            if os.path.exists(pdf_path):
                print("\n🔍 Testing extraction methods...")
                
                # Test PyPDF2
                print("1. PyPDF2:")
                text1 = pdf_processor.extract_text_pypdf2(pdf_path)
                print(f"   Length: {len(text1)} characters")
                print(f"   Preview: {text1[:200]}...")
                
                # Test pdfplumber
                print("\n2. pdfplumber:")
                text2 = pdf_processor.extract_text_pdfplumber(pdf_path)
                print(f"   Length: {len(text2)} characters")
                print(f"   Preview: {text2[:200]}...")
                
                # Test hybrid
                print("\n3. Hybrid:")
                text3 = pdf_processor.extract_text_hybrid(pdf_path)
                print(f"   Length: {len(text3)} characters")
                print(f"   Preview: {text3[:200]}...")
            else:
                print("❌ File not found.")
        
        elif choice == "4":
            break
        
        else:
            print("Invalid option.")


if __name__ == "__main__":
    main() 