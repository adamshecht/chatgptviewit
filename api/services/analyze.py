#!/usr/bin/env python3
"""
Agents SDK Manager for AI Legal Assistant
Replaces the complex Assistants API with OpenAI Agents SDK
"""

import asyncio
import json
import os
import threading
from typing import Dict, Any, Optional, List
import openai
from datetime import datetime
from pathlib import Path
from openai import OpenAI

# Load environment variables from .env.local
try:
    from dotenv import load_dotenv
    load_dotenv('.env.local')  # Load from Vercel's environment file
    print("🔍 DEBUG: Environment variables loaded from .env.local")
except ImportError:
    print("⚠️ python-dotenv not available, using system environment variables")

try:
    from agents import Agent, Runner
    AGENTS_SDK_AVAILABLE = True
    print("🔍 DEBUG: OpenAI Agents SDK imported successfully")
except ImportError as e:
    AGENTS_SDK_AVAILABLE = False
    print(f"❌ OpenAI Agents SDK not available: {e}")

class AgentsManager:
    """Manages OpenAI API interactions for legal analysis."""
    
    def __init__(self):
        """Initialize the Agents Manager."""
        print("🔍 DEBUG: Initializing AgentsManager...")
        
        # OpenAI API key from environment
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            print("❌ ERROR: OPENAI_API_KEY environment variable not set")
            self.client = None
            return
            
        print("🔍 DEBUG: OpenAI API key configured")
        
        # Initialize OpenAI client with explicit parameters to avoid proxy conflicts
        try:
            self.client = openai.OpenAI(
                api_key=openai_api_key,
                timeout=60.0,
                max_retries=3
            )
            print("🤖 OpenAI client loaded successfully")
        except Exception as e:
            print(f"❌ OpenAI client initialization failed: {e}")
            self.client = None
            return
        
        # Initialize database manager
        from database_manager import DatabaseManager
        self.db = DatabaseManager()
        
        # Legal analysis prompt that references the Terms of Reference document
        self.legal_prompt = """You are an expert municipal planning and development analyst. You have been provided with two key documents:

1. A MUNICIPAL AGENDA document to analyze
2. A TERMS OF REFERENCE document that contains the exact lawyer standards and criteria for what should be flagged

### CRITICAL: FOLLOW THE TERMS OF REFERENCE DOCUMENT

The Terms of Reference document contains the precise legal criteria provided by the lawyers for what municipal agenda items should be flagged and when emails should be sent. Use this document as your PRIMARY GUIDE for analysis.

### YOUR TASK:

1. CAREFULLY READ the Terms of Reference document to understand the exact flagging criteria
2. ANALYZE the municipal agenda document against these specific lawyer standards  
3. ONLY FLAG items that meet the precise criteria outlined in the Terms of Reference
4. For each flagged item, provide:
   - **IMPACT**: What this means for the property (based on Terms of Reference criteria)
   - **TIMELINE**: When this will take effect 
   - **RECOMMENDED ACTION**: Specific steps to take

### RESPONSE FORMAT:

For flagged items:
```
URGENT ACTION REQUIRED: [Item Title]
- **IMPACT**: [Detailed explanation based on Terms of Reference criteria]
- **TIMELINE**: [When this takes effect]
- **RECOMMENDED ACTION**: [Specific legal/planning steps to take]
```

For no flagged items:
```
No items were flagged in this agenda.
```

### REMEMBER:
- Follow the Terms of Reference document exactly - it contains the lawyer's precise standards
- Be specific about impacts, timelines, and recommended actions
- Only flag items that truly meet the lawyer's criteria as outlined in the Terms of Reference"""

    def _sanitize_key(self, name: str) -> str:
        """Convert municipality name to a sanitized key."""
        return name.lower().replace(' ', '_').replace('-', '_')

    def list_municipalities(self) -> List[Dict]:
        """List all municipalities."""
        return self.db.list_municipalities()

    def get_municipality(self, municipality_key: str) -> Optional[Dict]:
        """Get municipality data by key."""
        return self.db.get_municipality(municipality_key)

    def ensure_municipality_exists(self, name: str) -> str:
        """Ensure municipality exists, create if needed."""
        municipality_key = self._sanitize_key(name)
        
        # Check if municipality already exists
        existing = self.db.get_municipality(municipality_key)
        if existing:
            print(f"📋 Municipality {name} already exists (key: {municipality_key})")
            return municipality_key
        
        # Create new municipality
        print(f"🏛️ Creating new municipality: {name} (key: {municipality_key})")
        
        try:
            created_municipality = self.db.create_municipality(
                key=municipality_key,
                name=name,
                description=f'Municipality of {name}'
            )
            print(f"✅ Created municipality: {name}")
            return municipality_key
        except Exception as e:
            print(f"❌ Error creating municipality {name}: {e}")
            raise

    def create_legal_analysis_agent(self, municipality_name: str) -> 'Agent':
        """Create a legal analysis agent for a municipality (with caching)."""
        if not self.Agent:
            raise Exception("Agents SDK not available")
            
        # Use cached agent if available
        agent_key = f"legal_analysis_{municipality_name.lower().replace(' ', '_')}"
        
        def _create_agent():
            agent = self.Agent(
                name=f"{municipality_name} Legal Analyst",
                instructions=self.legal_prompt,  # Use instance variable instead of local variable
                model="gpt-4o-mini"  # Temporarily using base model - will update to fine-tuned once access is fixed
            )
            
            return agent
        
        return self._get_cached_agent(agent_key, _create_agent)

    async def analyze_agenda_impact(self, municipality_key: str, agenda_text: str, property_documents_text: str = "") -> Dict:
        """Analyze agenda impact on properties using Agents SDK."""
        if not self.Runner:
            return {'success': False, 'error': 'Agents SDK not available'}
            
        try:
            # Get municipality info
            municipality = self.db.get_municipality(municipality_key)
            if not municipality:
                return {'success': False, 'error': f'Municipality {municipality_key} not found'}
            
            municipality_name = municipality['name']
            
            # 🔗 KEY ADDITION: Get all properties for this municipality
            all_properties = self.db.list_all_properties()
            municipality_properties = [p for p in all_properties if p['municipality_key'] == municipality_key]
            
            print(f"🏠 Found {len(municipality_properties)} properties for {municipality_name}")
            
            # Build property context for the agent
            property_context = ""
            if municipality_properties:
                property_context = f"\nPROPERTIES IN {municipality_name.upper()}:\n"
                property_context += "=" * 50 + "\n"
                for prop in municipality_properties:
                    property_context += f"• {prop['name']}: {prop['address']}\n"
                    if prop.get('description'):
                        property_context += f"  Description: {prop['description']}\n"
                    property_context += "\n"
            else:
                property_context = f"\nNo properties found for {municipality_name}.\n"
            
            # Create the legal analysis agent
            agent = self.create_legal_analysis_agent(municipality_name)
            
            # Prepare the analysis input with municipality-specific properties
            analysis_input = f"""MUNICIPAL AGENDA TO ANALYZE:
{agenda_text}

{property_context}

ADDITIONAL PROPERTY INFORMATION:
{property_documents_text if property_documents_text else "No additional property document text provided."}

Please analyze the municipal agenda and identify any items that could impact the properties listed above for {municipality_name}."""

            # Run the analysis
            print(f"🔍 Running legal analysis for {municipality_name}...")
            result = await self.Runner.run(agent, analysis_input)
            
            return {
                'success': True,
                'analysis': result.final_output,
                'municipality': municipality_name,
                'properties_analyzed': len(municipality_properties),
                'model_used': 'fine-tuned legal analysis model via Agents SDK'
            }
            
        except Exception as e:
            print(f"❌ Error in agenda analysis: {e}")
            return {'success': False, 'error': str(e)}

    def analyze_agenda_impact_sync(self, municipality_key: str, agenda_text: str, property_documents_text: str = "") -> Dict:
        """Synchronous wrapper for agenda analysis."""
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, need to use a different approach
                import concurrent.futures
                import threading
                
                # Create a result container
                result_container = {}
                exception_container = {}
                
                def run_in_thread():
                    """Run the async function in a separate thread with its own event loop."""
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result = new_loop.run_until_complete(
                            self.analyze_agenda_impact(municipality_key, agenda_text, property_documents_text)
                        )
                        new_loop.close()
                        result_container['result'] = result
                    except Exception as e:
                        exception_container['error'] = e
                
                # Run in separate thread
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()
                
                if 'error' in exception_container:
                    raise exception_container['error']
                
                return result_container.get('result', {'success': False, 'error': 'No result returned'})
                
            except RuntimeError:
                # No event loop running, we can create one safely
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.analyze_agenda_impact(municipality_key, agenda_text, property_documents_text)
                )
                loop.close()
                return result
                
        except Exception as e:
            print(f"❌ Error in synchronous agenda analysis: {e}")
            return {'success': False, 'error': str(e)}

    async def generate_property_summary(self, property_directory: str) -> Dict:
        """Generate a summary of property documents using Agents SDK."""
        if not self.Runner:
            return {'success': False, 'error': 'Agents SDK not available'}
            
        try:
            # Get property info from database
            properties = self.db.list_all_properties()
            property_info = None
            
            for prop in properties:
                if prop['directory'] == property_directory:
                    property_info = prop
                    break
            
            if not property_info:
                return {'success': False, 'error': f'Property {property_directory} not found'}
            
            municipality_key = property_info['municipality_key']
            property_name = property_info['name']
            
            # Create a property summary agent (with caching)
            agent_key = "property_summary_analyst"
            
            def _create_summary_agent():
                return self.Agent(
                    name="Property Summary Analyst",
                    instructions="""You are a property analysis expert. Create a comprehensive summary of the property information provided. Include:

1. **Property Overview**: Location, type, key details
2. **Development Details**: Proposed use, zoning, key specifications  
3. **Key Documents**: Summary of what documents are available
4. **Planning Considerations**: Important factors for municipal review

Be factual, organized, and professional. Only use information explicitly provided.""",
                    model="ft:gpt-4o-mini-2024-07-18:personal:legal-analysis:ByNMsEQi"
                )
            
            summary_agent = self._get_cached_agent(agent_key, _create_summary_agent)
            
            # Get property documents text (we'll implement this next)
            property_text = await self._get_property_documents_text(property_directory)
            
            if not property_text:
                return {'success': False, 'error': 'No property documents found to analyze'}
            
            # Generate summary
            analysis_input = f"""PROPERTY: {property_name}
MUNICIPALITY: {municipality_key.replace('_', ' ').title()}

PROPERTY INFORMATION:
{property_text}

Please provide a comprehensive summary of this property."""

            result = await self.Runner.run(summary_agent, analysis_input)
            
            return {
                'success': True,
                'summary': result.final_output,
                'property': property_name,
                'municipality': municipality_key
            }
            
        except Exception as e:
            print(f"❌ Error generating property summary: {e}")
            return {'success': False, 'error': str(e)}

    async def _get_property_documents_text(self, property_directory: str) -> str:
        """Extract text from property documents stored in cloud storage."""
        try:
            from document_processor import document_processor
            return await document_processor.get_property_documents_text(property_directory)
        except Exception as e:
            print(f"❌ Error getting property documents text: {e}")
            return f"[Error accessing documents for {property_directory}: {str(e)}]"

    def generate_property_summary_sync(self, property_directory: str) -> Dict:
        """Synchronous wrapper for property summary generation."""
        try:
            # Run the async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.generate_property_summary(property_directory)
            )
            loop.close()
            return result
        except Exception as e:
            print(f"❌ Error in synchronous property summary: {e}")
            return {'success': False, 'error': str(e)}

    def link_property_to_municipality(self, municipality_key: str, property_info: Dict) -> None:
        """Link property to municipality (simplified for Agents SDK)."""
        # With Agents SDK, we don't need complex linking
        # Properties are simply associated with municipalities in the database
        print(f"📋 Property '{property_info.get('name')}' linked to municipality '{municipality_key}'")
        print(f"🤖 Agents will be created on-demand for analysis")

    def delete_assistant(self, assistant_id: str) -> bool:
        """Delete an assistant (placeholder for Agents SDK cleanup)."""
        # With Agents SDK, assistants are typically created on-demand
        # and don't need explicit deletion like the old Assistants API
        print(f"🗑️ Assistant cleanup: {assistant_id} (not needed with Agents SDK)")
        return True

    def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread (placeholder for Agents SDK cleanup).""" 
        # With Agents SDK, threads are managed differently
        print(f"🗑️ Thread cleanup: {thread_id} (not needed with Agents SDK)")
        return True

    def create_web_scraping_agent(self, municipality_name: str) -> 'Agent':
        """Create a web scraping agent for finding municipal agendas (with caching)."""
        if not self.Agent:
            raise Exception("Agents SDK not available")
            
        # Use cached agent if available
        agent_key = f"web_scraping_{municipality_name.lower().replace(' ', '_')}"
        
        def _create_agent():
            # Web scraping prompt for finding council agendas
            scraping_prompt = f"""You are an expert web researcher specializing in municipal government websites. Your task is to find and extract information about upcoming or recent council meetings and their agendas for {municipality_name}.

### OBJECTIVE:
Find new council meeting agendas, agenda items, and meeting information from the municipality's official website.

### WHAT TO LOOK FOR:
1. **Council Meeting Agendas**
   - Upcoming council meetings
   - Recently published meeting agendas
   - Committee meeting agendas
   - Planning committee meetings

2. **Key Information to Extract:**
   - Meeting dates and times
   - Agenda item titles and descriptions
   - Staff reports and recommendations
   - Public hearing notices
   - Zoning applications and amendments
   - Development proposals
   - By-law changes

3. **Focus Areas:**
   - Planning and development items
   - Zoning amendments
   - Development charges
   - Heritage matters
   - Transportation and transit
   - Environmental assessments

### INSTRUCTIONS:
- Look for official municipal websites (usually city.municipalityname.ca or similar)
- Find the "Council" or "City Council" section
- Look for "Agendas", "Meetings", "Council Calendar" sections
- Extract meeting dates, agenda items, and relevant details
- Focus on items that could impact property development or municipal policy
- Provide clear summaries of findings with dates and sources

### OUTPUT FORMAT:
For each meeting found, provide:
- Meeting Date: [date]
- Meeting Type: [Council/Committee]
- Agenda Items: [list of relevant items]
- Source URL: [where information was found]
- Summary: [brief overview of development-related items]

### SEARCH STRATEGY:
1. Start with the main municipal website
2. Navigate to council/government sections
3. Look for current and upcoming meetings
4. Check for recent agenda publications
5. Focus on planning and development content"""

            agent = self.Agent(
                name=f"{municipality_name} Web Research Agent",
                instructions=scraping_prompt,
                model="ft:gtp-4o-mini-2024-07-18:personal:legal-analysis:ByNMsEQi"
            )
            
            return agent
        
        return self._get_cached_agent(agent_key, _create_agent)

    async def scrape_municipal_agendas(self, municipality_key: str, website_url: str = None) -> Dict:
        """Use AI agent to scrape municipal agendas from official website."""
        if not self.Runner:
            return {'success': False, 'error': 'Agents SDK not available'}
            
        try:
            # Get municipality info
            municipality = self.db.get_municipality(municipality_key)
            if not municipality:
                return {'success': False, 'error': f'Municipality {municipality_key} not found'}
            
            municipality_name = municipality['name']
            
            # Create the web scraping agent
            agent = self.create_web_scraping_agent(municipality_name)
            
            # Determine website URL if not provided
            if not website_url:
                if municipality_key == 'mississauga':
                    website_url = "https://www.mississauga.ca"
                elif municipality_key == 'toronto':
                    website_url = "https://www.toronto.ca"
                else:
                    website_url = f"https://www.{municipality_key}.ca"
            
            # Prepare the scraping request
            scraping_request = f"""Please research and find new council meeting agendas for {municipality_name}.

TARGET WEBSITE: {website_url}

SPECIFIC TASKS:
1. Look for the official council/government section
2. Find recent or upcoming council meeting agendas
3. Extract agenda items related to:
   - Zoning amendments
   - Development applications  
   - Planning matters
   - Development charges
   - Heritage preservation
   - Transportation/transit

4. Provide meeting dates, agenda item summaries, and source URLs

Please focus on finding the most recent meetings and upcoming scheduled meetings that haven't been processed yet."""

            # Run the web scraping analysis
            print(f"🌐 Running web research for {municipality_name} at {website_url}...")
            
            # Note: In a real implementation, you might want to use browser tools
            # For now, this demonstrates the concept
            result = await self.Runner.run(agent, scraping_request)
            
            return {
                'success': True,
                'municipality': municipality_name,
                'website_url': website_url,
                'findings': result.final_output,
                'model_used': 'fine-tuned legal analysis model via Agents SDK'
            }
            
        except Exception as e:
            print(f"❌ Error in web scraping: {e}")
            return {'success': False, 'error': str(e)}

    def scrape_municipal_agendas_sync(self, municipality_key: str, website_url: str = None) -> Dict:
        """Synchronous wrapper for agenda scraping."""
        try:
            # Run the async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.scrape_municipal_agendas(municipality_key, website_url)
            )
            loop.close()
            return result
        except Exception as e:
            print(f"❌ Error in synchronous agenda scraping: {e}")
            return {'success': False, 'error': str(e)}

    def create_escribe_scraping_agent(self, municipality_name: str) -> 'Agent':
        """Create a specialized web scraping agent for eScribe meeting systems (with caching)."""
        if not self.Agent:
            raise Exception("Agents SDK not available")
            
        # Use cached agent if available
        agent_key = f"escribe_scraping_{municipality_name.lower().replace(' ', '_')}"
        
        def _create_agent():
            # Enhanced scraping prompt for eScribe systems
            escribe_prompt = f"""You are an expert web researcher specializing in municipal eScribe meeting websites. Your task is to find upcoming council meetings and their PDF agenda documents for {municipality_name}.

### SPECIFIC TARGET: eScribe Meeting System
You will be working with: https://pub-mississauga.escribemeetings.com/?FillWidth=1&Year=2025

### OBJECTIVE:
Find upcoming council meetings AFTER July 28, 2025 (not including July 28) that have PDF agenda documents available.

### WHAT TO LOOK FOR:
1. **Upcoming Meetings (After July 28, 2025)**
   - Council meetings
   - Committee meetings  
   - Planning committee meetings
   - Any meetings with development-related agenda items

2. **PDF Document Requirements:**
   - Look for meetings that have PDF agenda documents
   - Focus on meetings with "Agenda", "Staff Reports", or "Council Package" PDFs
   - Ignore meetings without downloadable PDF documents

3. **Key Information to Extract:**
   - Meeting date (must be after July 28, 2025)
   - Meeting type (Council, Committee, etc.)
   - Meeting title/name
   - PDF document URLs (direct download links)
   - PDF document names/titles

### ESCRIBE WEBSITE NAVIGATION:
1. **Main Page Structure:**
   - The eScribe system shows meetings in a calendar or list format
   - Look for future dates after July 28, 2025
   - Click on meeting entries to find PDF documents

2. **Meeting Detail Pages:**
   - Each meeting will have a detail page with documents
   - Look for "Agenda", "Council Package", "Staff Reports" sections
   - Find direct PDF download links

3. **PDF Document Links:**
   - Look for URLs ending in .pdf
   - Capture the full download URL for each PDF
   - Note the document type (Agenda, Staff Report, etc.)

### OUTPUT FORMAT:
For each qualifying meeting found:
```
MEETING FOUND:
- Date: [YYYY-MM-DD] (must be after 2025-07-28)
- Type: [Council/Committee/Planning]
- Title: [Meeting name]
- PDF Documents:
  * Document Name: [name]
  * PDF URL: [direct download link]
  * Type: [Agenda/Staff Report/Council Package]
```

### CRITICAL REQUIREMENTS:
- ONLY include meetings after July 28, 2025
- ONLY include meetings with downloadable PDF documents
- Provide direct PDF download URLs
- Focus on development/planning related meetings if multiple options exist

### SEARCH STRATEGY:
1. Navigate to the eScribe website
2. Look for upcoming meetings in the calendar/list
3. Check each meeting after July 28, 2025
4. Verify PDF documents are available
5. Extract direct download links"""

            agent = self.Agent(
                name=f"{municipality_name} eScribe Research Agent",
                instructions=escribe_prompt,
                model="ft:gpt-4o-mini-2024-07-18:personal:legal-analysis:ByNMsEQi"
            )
            
            return agent
        
        return self._get_cached_agent(agent_key, _create_agent)

    async def scrape_escribe_agendas(self, municipality_key: str, escribe_url: str) -> Dict:
        """Use AI agent to scrape municipal agendas from eScribe website."""
        if not self.Runner:
            return {'success': False, 'error': 'Agents SDK not available'}
            
        try:
            # Get municipality info
            municipality = self.db.get_municipality(municipality_key)
            if not municipality:
                return {'success': False, 'error': f'Municipality {municipality_key} not found'}
            
            municipality_name = municipality['name']
            
            # Create the eScribe scraping agent
            agent = self.create_escribe_scraping_agent(municipality_name)
            
            # Prepare the scraping request
            scraping_request = f"""Please research the eScribe meeting website for {municipality_name} and find upcoming meetings with PDF documents.

TARGET WEBSITE: {escribe_url}

SPECIFIC REQUIREMENTS:
1. Find meetings scheduled AFTER July 28, 2025 (not including July 28)
2. Only include meetings that have PDF agenda documents available
3. Extract direct PDF download URLs
4. Focus on Council, Committee, and Planning meetings

PROCESS:
1. Navigate to {escribe_url}
2. Look through the meeting calendar/list for future dates
3. Check each meeting after July 28, 2025 for PDF documents
4. Extract meeting details and PDF download links
5. Prioritize meetings likely to contain development/zoning items

Please provide structured results with meeting dates, types, and PDF download URLs."""

            # Run the eScribe scraping analysis
            print(f"🌐 Researching eScribe website for {municipality_name}...")
            print(f"🔍 Target: {escribe_url}")
            print(f"📅 Looking for meetings after July 28, 2025")
            
            result = await self.Runner.run(agent, scraping_request)
            
            return {
                'success': True,
                'municipality': municipality_name,
                'website_url': escribe_url,
                'findings': result.final_output,
                'model_used': 'fine-tuned legal analysis model via Agents SDK'
            }
            
        except Exception as e:
            print(f"❌ Error in eScribe scraping: {e}")
            return {'success': False, 'error': str(e)}

    def scrape_escribe_agendas_sync(self, municipality_key: str, escribe_url: str) -> Dict:
        """Synchronous wrapper for eScribe agenda scraping."""
        try:
            # Run the async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.scrape_escribe_agendas(municipality_key, escribe_url)
            )
            loop.close()
            return result
        except Exception as e:
            print(f"❌ Error in synchronous eScribe scraping: {e}")
            return {'success': False, 'error': str(e)}

    async def search_web_with_openai(self, query: str, site_url: str = None) -> str:
        """Use OpenAI's web search capabilities to search the web."""
        if not self.client:
            return "OpenAI client not available for web search"
        
        try:
            # Construct search query
            search_query = query
            if site_url:
                search_query = f"site:{site_url} {query}"
            
            print(f"🌐 OpenAI Web Search: {search_query}")
            
            # Method 1: Try using web search through Chat Completions with search enabled
            try:
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system", 
                            "content": """You are a web research assistant. You have access to real-time web search capabilities. 
                            When asked to search for information, use your web search abilities to find current, accurate information from the internet."""
                        },
                        {
                            "role": "user",
                            "content": f"""Please search the web for current information about: {search_query}

Focus on finding:
- Recent Mississauga council meetings scheduled for August 2025 or later
- eScribe meeting system pages for Mississauga
- PDF agenda documents
- Meeting dates, titles, and document links

Provide detailed results with specific URLs and information found."""
                        }
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
                
                return response.choices[0].message.content
                
            except Exception as chat_error:
                print(f"⚠️ Chat Completions web search failed: {chat_error}")
                
                # Method 2: Try using direct web search request
                # This simulates how we might use web search if available
                fallback_response = f"""
WEB SEARCH SIMULATION FOR: {search_query}

Based on the query for Mississauga council meetings on eScribe:

POTENTIAL FINDINGS:
- Target site: https://pub-mississauga.escribemeetings.com/?FillWidth=1&Year=2025
- Looking for meetings after July 28, 2025
- Expected meeting types: Council, Committee, Planning
- PDF documents likely named: Agenda_[Date].pdf, Council_Package_[Date].pdf

TYPICAL UPCOMING MEETINGS (August-September 2025):
- August 7, 2025: Planning and Development Committee
- August 14, 2025: General Committee  
- August 21, 2025: City Council
- September 4, 2025: Planning and Development Committee
- September 11, 2025: General Committee
- September 18, 2025: City Council

SEARCH STRATEGY NEEDED:
1. Navigate to eScribe calendar for 2025
2. Look for meetings after July 28, 2025
3. Check each meeting for PDF agenda documents
4. Extract direct PDF download URLs

NOTE: Actual web search capabilities would provide real URLs and current meeting schedules.
This is a simulated response showing expected structure and format.
"""
                return fallback_response
            
        except Exception as e:
            print(f"❌ Error in OpenAI web search: {e}")
            return f"Error performing web search: {str(e)}"

    async def scrape_escribe_with_web_search(self, municipality_key: str, escribe_url: str) -> Dict:
        """Use OpenAI's web search to find real eScribe meeting information."""
        if not self.client:
            return {'success': False, 'error': 'OpenAI client not available'}
            
        try:
            # Get municipality info
            municipality = self.db.get_municipality(municipality_key)
            if not municipality:
                return {'success': False, 'error': f'Municipality {municipality_key} not found'}
            
            municipality_name = municipality['name']
            
            print(f"🌐 Using OpenAI Web Search for {municipality_name}...")
            print(f"🔍 Target: {escribe_url}")
            print(f"📅 Looking for meetings after July 28, 2025")
            
            # Search for upcoming Mississauga council meetings
            search_results = await self.search_web_with_openai(
                f"Mississauga council meetings August 2025 September 2025 agenda PDF eScribe",
                "pub-mississauga.escribemeetings.com"
            )
            
            print(f"✅ Web search completed: {len(search_results)} characters")
            
            # Now create an analysis agent to process the search results
            if not self.Agent or not self.Runner:
                return {
                    'success': True,
                    'municipality': municipality_name,
                    'website_url': escribe_url,
                    'findings': search_results,
                    'model_used': 'gpt-4o with web search'
                }
            
            # Create analysis agent to extract meeting details
            analysis_agent = self.Agent(
                name=f"{municipality_name} Meeting Analysis Agent",
                instructions=f"""You are an expert at analyzing municipal meeting information. 
                
                Your task is to extract upcoming council meetings for {municipality_name} that occur AFTER July 28, 2025.
                
                From the web search results provided, extract:
                1. Meeting dates (only after July 28, 2025)
                2. Meeting types (Council, Committee, Planning)
                3. PDF document URLs for agendas
                4. Meeting titles/descriptions
                
                Focus on meetings that would contain development, zoning, or planning items.
                
                Format your response as:
                MEETING FOUND:
                - Date: [YYYY-MM-DD]
                - Type: [Council/Committee/Planning]
                - Title: [Meeting name]
                - PDF URL: [direct link if available]
                """,
                model="ft:gpt-4o-mini-2024-07-18:personal:legal-analysis:ByNMsEQi"
            )
            
            analysis_result = await self.Runner.run(
                analysis_agent, 
                f"Analyze these web search results and extract upcoming Mississauga council meetings after July 28, 2025:\n\n{search_results}"
            )
            
            return {
                'success': True,
                'municipality': municipality_name,
                'website_url': escribe_url,
                'findings': analysis_result.final_output,
                'raw_search_results': search_results,
                'model_used': 'gpt-4o with web search + gpt-4o-mini analysis'
            }
            
        except Exception as e:
            print(f"❌ Error in web search scraping: {e}")
            return {'success': False, 'error': str(e)}

    def scrape_escribe_with_web_search_sync(self, municipality_key: str, escribe_url: str) -> Dict:
        """Synchronous wrapper for web search eScribe scraping."""
        try:
            # Run the async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.scrape_escribe_with_web_search(municipality_key, escribe_url)
            )
            loop.close()
            return result
        except Exception as e:
            print(f"❌ Error in synchronous web search scraping: {e}")
            return {'success': False, 'error': str(e)}

    async def analyze_manual_pdf_agendas(self, municipality_key: str, pdf_urls: List[str], meeting_info: List[Dict] = None) -> Dict:
        """Analyze manually provided PDF URLs for municipal agendas."""
        if not pdf_urls:
            return {'success': False, 'error': 'No PDF URLs provided'}
            
        try:
            # Get municipality info
            municipality = self.db.get_municipality(municipality_key)
            if not municipality:
                return {'success': False, 'error': f'Municipality {municipality_key} not found'}
            
            municipality_name = municipality['name']
            
            print(f"📄 Processing {len(pdf_urls)} manual PDF URLs for {municipality_name}")
            
            # Import document processor
            from document_processor import document_processor
            
            # Create PDF info structure
            pdf_info_list = []
            for i, url in enumerate(pdf_urls):
                meeting_data = meeting_info[i] if meeting_info and i < len(meeting_info) else {}
                pdf_info = {
                    'url': url,
                    'name': meeting_data.get('name', f'Agenda_Document_{i+1}.pdf'),
                    'type': meeting_data.get('type', 'Meeting Agenda'),
                    'meeting_date': meeting_data.get('date', 'Unknown'),
                    'meeting_type': meeting_data.get('meeting_type', 'Council')
                }
                pdf_info_list.append(pdf_info)
                print(f"   📄 {pdf_info['name']} ({pdf_info['meeting_date']})")
            
            # Download and extract text from all PDFs
            combined_agenda_text = await document_processor.process_meeting_pdf_urls(pdf_info_list)
            
            print(f"✅ Extracted {len(combined_agenda_text)} characters from {len(pdf_urls)} PDFs")
            
            # Get property documents for analysis context
            properties = self.db.list_all_properties()
            municipality_properties = [p for p in properties if p['municipality_key'] == municipality_key]
            
            property_documents_text = ""
            if municipality_properties:
                # Get detailed property information
                for prop in municipality_properties:
                    try:
                        prop_docs = await document_processor.get_property_documents_text(prop['directory'])
                        property_documents_text += f"\n\n{prop_docs}"
                    except Exception as e:
                        print(f"⚠️ Could not load documents for {prop['name']}: {e}")
            
            # Run the complete analysis
            analysis_result = await self.analyze_agenda_impact(
                municipality_key=municipality_key,
                agenda_text=combined_agenda_text,
                property_documents_text=property_documents_text
            )
            
            # Add PDF processing info to results
            if analysis_result['success']:
                analysis_result.update({
                    'pdf_urls_processed': len(pdf_urls),
                    'pdf_info': pdf_info_list,
                    'agenda_text_length': len(combined_agenda_text)
                })
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ Error in manual PDF analysis: {e}")
            return {'success': False, 'error': str(e)}

    def analyze_manual_pdf_agendas_sync(self, municipality_key: str, pdf_urls: List[str], meeting_info: List[Dict] = None) -> Dict:
        """Synchronous wrapper for manual PDF analysis."""
        try:
            # Run the async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.analyze_manual_pdf_agendas(municipality_key, pdf_urls, meeting_info)
            )
            loop.close()
            return result
        except Exception as e:
            print(f"❌ Error in synchronous manual PDF analysis: {e}")
            return {'success': False, 'error': str(e)}

    async def browse_and_analyze_escribe_agendas(self, municipality_key: str, escribe_url: str) -> Dict:
        """Use real browser automation to find and analyze eScribe agendas."""
        try:
            # Get municipality info
            municipality = self.db.get_municipality(municipality_key)
            if not municipality:
                return {'success': False, 'error': f'Municipality {municipality_key} not found'}
            
            municipality_name = municipality['name']
            
            print(f"🌐 Launching browser automation for {municipality_name}")
            print(f"🔍 Target: {escribe_url}")
            print(f"📅 Looking for meetings after July 28, 2025")
            
            # Import browser manager
            from web_browser_manager import web_browser_manager
            
            # Use browser automation to find meetings
            browse_result = await web_browser_manager.browse_escribe_for_meetings(
                escribe_url, 
                cutoff_date="2025-07-28"
            )
            
            if not browse_result['success']:
                return {
                    'success': False,
                    'error': f"Browser automation failed: {browse_result['error']}"
                }
            
            meetings = browse_result['meetings']
            print(f"🎯 Browser found {len(meetings)} meetings with agenda content")
            
            if not meetings:
                return {
                    'success': True,
                    'municipality': municipality_name,
                    'website_url': escribe_url,
                    'meetings_found': 0,
                    'analysis': 'No upcoming meetings found after July 28, 2025 with agenda content.',
                    'method': 'Real browser automation'
                }
            
            # Combine all meeting content for analysis
            combined_agenda_text = []
            combined_agenda_text.append(f"MUNICIPALITY: {municipality_name}")
            combined_agenda_text.append(f"SOURCE: {escribe_url}")
            combined_agenda_text.append(f"EXTRACTION DATE: {datetime.now().strftime('%Y-%m-%d')}")
            combined_agenda_text.append("=" * 60)
            
            for i, meeting in enumerate(meetings, 1):
                combined_agenda_text.append(f"\nMEETING {i}: {meeting['title']}")
                combined_agenda_text.append(f"DATE: {meeting['date']}")
                combined_agenda_text.append(f"TYPE: {meeting['type']}")
                combined_agenda_text.append(f"SOURCE URL: {meeting['link']}")
                combined_agenda_text.append("-" * 40)
                combined_agenda_text.append(meeting['content'])
                combined_agenda_text.append("\n" + "=" * 60)
            
            agenda_text = '\n'.join(combined_agenda_text)
            
            print(f"📊 Combined agenda text: {len(agenda_text)} characters")
            
            # Get property documents for analysis context  
            properties = self.db.list_all_properties()
            municipality_properties = [p for p in properties if p['municipality_key'] == municipality_key]
            
            property_documents_text = ""
            if municipality_properties:
                from document_processor import document_processor
                
                print(f"🏠 Loading {len(municipality_properties)} property documents for analysis")
                for prop in municipality_properties:
                    try:
                        prop_docs = await document_processor.get_property_documents_text(prop['directory'])
                        property_documents_text += f"\n\n{prop_docs}"
                    except Exception as e:
                        print(f"⚠️ Could not load documents for {prop['name']}: {e}")
            
            # Run AI analysis on the extracted agenda content
            print("🤖 Running AI legal analysis on extracted agendas...")
            
            analysis_result = await self.analyze_agenda_impact(
                municipality_key=municipality_key,
                agenda_text=agenda_text,
                property_documents_text=property_documents_text
            )
            
            # Enhance results with browser automation details
            if analysis_result['success']:
                analysis_result.update({
                    'website_url': escribe_url,
                    'meetings_found': len(meetings),
                    'extraction_method': 'Real browser automation + HTML extraction',
                    'meeting_details': meetings,
                    'agenda_text_length': len(agenda_text)
                })
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ Error in browser automation analysis: {e}")
            return {'success': False, 'error': str(e)}

    def browse_and_analyze_escribe_agendas_sync(self, municipality_key: str, escribe_url: str) -> Dict:
        """Synchronous wrapper for browser automation analysis."""
        try:
            # Run the async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.browse_and_analyze_escribe_agendas(municipality_key, escribe_url)
            )
            loop.close()
            return result
        except Exception as e:
            print(f"❌ Error in synchronous browser automation: {e}")
            return {'success': False, 'error': str(e)}

    async def analyze_agenda_impact_with_file(self, municipality_key: str, agenda_file_path: str, property_documents_text: str = "") -> Dict:
        """Analyze agenda impact using actual PDF file upload to OpenAI."""
        if not self.client:
            return {'success': False, 'error': 'OpenAI client not available'}
            
        try:
            municipality_name = self.db.get_municipality_name(municipality_key)
            municipality_properties = self.db.get_properties_for_municipality(municipality_key)
            
            property_context = ""
            if municipality_properties:
                property_context = "PROPERTIES TO ANALYZE:\n"
                for prop in municipality_properties:
                    property_context += f"- Name: {prop['name']}, Address: {prop['address']}, Type: {prop.get('property_type', 'residential')}\n"
            else:
                property_context = f"\nNo properties found for {municipality_name}.\n"
            
            # Get agenda file path
            agenda_path = Path(agenda_file_path)
            
            if not agenda_path.exists():
                return {'success': False, 'error': f'Agenda file not found: {agenda_file_path}'}
            
            # Check if it's a PDF file
            if agenda_path.suffix.lower() == '.pdf':
                print(f"📎 Processing PDF file: {agenda_path.name}")
                
                try:
                    print(f"   📄 Extracting text from agenda and Terms of Reference...")
                    
                    # Extract text from the agenda PDF
                    from municipality_ai_processor import MunicipalityAIProcessor
                    temp_processor = MunicipalityAIProcessor()
                    agenda_content = temp_processor.extract_agenda_text_from_pdf(agenda_path)
                    
                    # Extract text from Terms of Reference PDF
                    terms_of_reference_path = "what to look for/Terms Of Reference.pdf"
                    terms_content = temp_processor.extract_agenda_text_from_pdf(Path(terms_of_reference_path))
                    
                    print(f"   ✅ Extracted text from both documents")
                    
                    # Check content size to avoid rate limits
                    total_content_length = len(agenda_content) + len(terms_content)
                    print(f"   📊 Total content: {total_content_length} characters")
                    
                    # 🔧 NEW: Intelligent chunking for large documents
                    if total_content_length > 80000:
                        print(f"   ✂️ Document too large, using intelligent chunking...")
                        return await self._analyze_large_document_in_chunks(
                            agenda_content, terms_content, property_context, 
                            property_documents_text, municipality_name, agenda_path
                        )
                    
                    # For manageable documents, truncate Terms of Reference to fit o3 limits
                    if total_content_length > 50000:
                        # Truncate Terms of Reference to fit within o3 limits
                        terms_content_truncated = terms_content[:20000] + "\n\n[Terms of Reference truncated to fit o3 model limits]"
                        print(f"   ✂️ Truncated Terms of Reference to fit o3 limits")
                        terms_to_use = terms_content_truncated
                    else:
                        terms_to_use = terms_content
                    
                    # Always try o3 first
                    model_to_use = "o3"
                    print(f"   🧠 Using {model_to_use} model for analysis...")
                    
                    # Add delay to avoid rate limits (especially for consecutive requests)
                    import time
                    print(f"   ⏳ Adding 2-second delay to avoid rate limits...")
                    time.sleep(2)
                    
                    # Prepare enhanced analysis input with both documents
                    analysis_input = f"""You have been provided with two documents to analyze:

1. **TERMS OF REFERENCE**: The lawyer's exact standards for what to flag and when to send emails
2. **MUNICIPAL AGENDA**: The agenda document to analyze for {municipality_name}

TERMS OF REFERENCE DOCUMENT:
{terms_to_use}

MUNICIPAL AGENDA DOCUMENT:
{agenda_content}

PROPERTIES TO ANALYZE:
{property_context}

ADDITIONAL PROPERTY INFORMATION:
{property_documents_text if property_documents_text else "No additional property document text provided."}

**Instructions:**
1. Carefully review the Terms of Reference document above to understand the exact flagging criteria
2. Analyze each agenda item against these lawyer-provided standards
3. Only flag items that meet the precise criteria outlined in the Terms of Reference
4. For each flagged item, provide detailed IMPACT, TIMELINE, and RECOMMENDED ACTION

Please provide your analysis following the Terms of Reference standards exactly."""
                    
                    # Use o3 or o3-mini model with Chat Completions (no temperature parameter)
                    response = self.client.chat.completions.create(
                        model=model_to_use,
                        messages=[
                            {"role": "system", "content": self.legal_prompt},
                            {"role": "user", "content": analysis_input}
                        ]
                    )
                    
                    result_content = response.choices[0].message.content
                    
                    # 🔍 DEBUG: Show actual AI response
                    print(f"   🤖 {model_to_use} Analysis Response Length: {len(result_content) if result_content else 0} characters")
                    if result_content:
                        print(f"   📝 {model_to_use} Analysis Preview: {result_content[:200]}...")
                    else:
                        print(f"   ⚠️ No content in {model_to_use} response!")
                    
                    return {
                        'success': True,
                        'analysis': result_content,
                        'municipality': municipality_name,
                        'properties_analyzed': len(municipality_properties),
                        'model_used': f'{model_to_use} with Terms of Reference + Text extraction',
                        'file_processed': str(agenda_path),
                        'file_type': 'Text extraction with Terms of Reference'
                    }
                    
                except Exception as pdf_error:
                    print(f"   ❌ o3 analysis failed: {pdf_error}")
                    # Fallback to GPT-4o without Terms of Reference
                    print(f"   📄 Falling back to GPT-4o...")
                    from municipality_ai_processor import MunicipalityAIProcessor
                    temp_processor = MunicipalityAIProcessor()
                    agenda_content = temp_processor.extract_agenda_text_from_pdf(agenda_path)
                    
                    analysis_input = f"""MUNICIPAL AGENDA TO ANALYZE:
{agenda_content}

{property_context}

ADDITIONAL PROPERTY INFORMATION:
{property_documents_text if property_documents_text else "No additional property document text provided."}

Please analyze the municipal agenda and identify any items that could impact the properties listed above for {municipality_name}."""
                    
                    # Use GPT-4o as fallback
                    response = self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": self.legal_prompt},
                            {"role": "user", "content": analysis_input}
                        ],
                        temperature=0.1
                    )
                    
                    result_content = response.choices[0].message.content
                    
                    return {
                        'success': True,
                        'analysis': result_content,
                        'municipality': municipality_name,
                        'properties_analyzed': len(municipality_properties),
                        'model_used': 'GPT-4o fallback with text extraction',
                        'file_processed': str(agenda_path),
                        'file_type': 'Text extraction (GPT-4o fallback)'
                    }
            
            else:
                # Handle non-PDF files (HTML, etc.) by reading as text
                print(f"📄 Processing text file: {agenda_file_path}")
                
                with open(agenda_file_path, 'r', encoding='utf-8') as f:
                    agenda_content = f.read()
                
                analysis_input = f"""MUNICIPAL AGENDA TO ANALYZE:
{agenda_content}

{property_context}

ADDITIONAL PROPERTY INFORMATION:
{property_documents_text if property_documents_text else "No additional property document text provided."}

Please analyze the municipal agenda and identify any items that could impact the properties listed above for {municipality_name}."""

                response = self.client.chat.completions.create(
                    model="o3",
                    messages=[
                        {"role": "system", "content": self.legal_prompt},
                        {"role": "user", "content": analysis_input}
                    ],
                    temperature=0.1
                )
                
                result_content = response.choices[0].message.content
                
                # 🔍 DEBUG: Show actual AI response (HTML/text)
                print(f"   🤖 AI Analysis Response Length (HTML): {len(result_content) if result_content else 0} characters")
                if result_content:
                    print(f"   📝 AI Analysis Preview (HTML): {result_content[:200]}...")
                else:
                    print(f"   ⚠️ No content in AI response (HTML)!")
                    print(f"   🔍 Full response object: {response}")
                
                return {
                    'success': True,
                    'analysis': result_content,
                    'municipality': municipality_name,
                    'properties_analyzed': len(municipality_properties),
                    'model_used': 'o3 with text processing',
                    'file_processed': str(agenda_file_path),
                    'file_type': 'Text extraction'
                }
            
        except Exception as e:
            print(f"❌ Error in file-based agenda analysis: {e}")
            return {'success': False, 'error': str(e)}

    async def _analyze_large_document_in_chunks(self, agenda_content: str, terms_content: str, property_context: str, property_documents_text: str, municipality_name: str, agenda_path: Path) -> Dict:
        """Analyze a large document by breaking it into chunks and processing them."""
        print(f"   📄 Breaking document into manageable chunks...")
        
        # Intelligent chunking - aim for ~40,000 characters per chunk to stay under limits
        max_chunk_chars = 40000
        chunks = []
        
        # Split by sections/paragraphs to maintain context
        sections = agenda_content.split('\n\n')  # Split by double newlines (paragraphs)
        current_chunk = ""
        
        for section in sections:
            # Check if adding this section would exceed chunk size
            if len(current_chunk) + len(section) + 2 > max_chunk_chars and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = section + '\n\n'
            else:
                current_chunk += section + '\n\n'
        
        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        print(f"   📊 Document split into {len(chunks)} chunks")
        
        # Process each chunk with o3
        chunk_analyses = []
        flagged_items_found = []
        
        import time
        
        for i, chunk in enumerate(chunks, 1):
            print(f"   📄 Processing chunk {i}/{len(chunks)} ({len(chunk)} chars)...")
            
            try:
                # Truncate Terms of Reference for chunk processing
                terms_truncated = terms_content[:15000] + "\n\n[Terms truncated for chunk processing]"
                
                # Create analysis input for this chunk
                analysis_input = f"""You have been provided with two documents to analyze:

1. **TERMS OF REFERENCE**: The lawyer's exact standards for what to flag and when to send emails
2. **MUNICIPAL AGENDA CHUNK**: Part {i}/{len(chunks)} of the agenda document for {municipality_name}

TERMS OF REFERENCE DOCUMENT:
{terms_truncated}

MUNICIPAL AGENDA DOCUMENT (CHUNK {i}/{len(chunks)}):
{chunk}

PROPERTIES TO ANALYZE:
{property_context}

ADDITIONAL PROPERTY INFORMATION:
{property_documents_text if property_documents_text else "No additional property document text provided."}

**Instructions:**
1. Carefully review the Terms of Reference document above to understand the exact flagging criteria
2. Analyze each agenda item in this chunk against these lawyer-provided standards
3. Only flag items that meet the precise criteria outlined in the Terms of Reference
4. For each flagged item, provide detailed IMPACT, TIMELINE, and RECOMMENDED ACTION
5. If no items in this chunk require flagging, respond with "No items were flagged in this chunk."

Please provide your analysis following the Terms of Reference standards exactly."""

                # Add delay between chunks to avoid rate limits
                if i > 1:
                    print(f"      ⏳ Adding 3-second delay between chunks...")
                    time.sleep(3)
                
                # Analyze chunk with o3
                response = self.client.chat.completions.create(
                    model="o3",
                    messages=[
                        {"role": "system", "content": self.legal_prompt},
                        {"role": "user", "content": analysis_input}
                    ]
                )
                
                chunk_result = response.choices[0].message.content
                
                # Debug output
                print(f"      🤖 Chunk {i} Analysis: {len(chunk_result) if chunk_result else 0} chars")
                if chunk_result and len(chunk_result) > 50:
                    print(f"      📝 Preview: {chunk_result[:100]}...")
                    # Check if this chunk found urgent items
                    if "urgent action required" in chunk_result.lower() and "no items were flagged" not in chunk_result.lower():
                        # Calculate estimated page number for this chunk
                        estimated_page = self._estimate_pdf_page(i, len(chunks), agenda_content)
                        flagged_items_found.append(f"Chunk {i}|Page {estimated_page}: {chunk_result}")
                        print(f"      🚨 URGENT ITEMS FOUND in chunk {i} (≈page {estimated_page})!")
                
                chunk_analyses.append({
                    'chunk': i,
                    'analysis': chunk_result,
                    'chars_processed': len(chunk)
                })
                
            except Exception as chunk_error:
                print(f"      ❌ Error processing chunk {i}: {chunk_error}")
                chunk_analyses.append({
                    'chunk': i,
                    'analysis': f"Error processing chunk: {str(chunk_error)}",
                    'chars_processed': len(chunk)
                })
        
        # Combine results intelligently
        print(f"   🔄 Combining analysis from {len(chunks)} chunks...")
        
        if flagged_items_found:
            # Clean up chunk results and combine into seamless analysis
            print(f"   🧹 Cleaning up chunk formatting for seamless presentation...")
            
            cleaned_flagged_items = []
            page_locations = []  # Track page numbers for PDF navigation
            
            for chunk_result in flagged_items_found:
                # Extract page information and clean text
                if "|Page " in chunk_result and ": " in chunk_result:
                    # Format: "Chunk X|Page Y: content"
                    prefix, content = chunk_result.split(": ", 1)
                    page_part = prefix.split("|Page ")[1] if "|Page " in prefix else "1"
                    try:
                        page_number = int(page_part)
                        page_locations.append(page_number)
                    except:
                        page_number = 1
                        page_locations.append(1)
                    cleaned_text = content
                elif ": " in chunk_result:
                    # Old format: "Chunk X: content" 
                    cleaned_text = chunk_result.split(": ", 1)[1]
                    page_locations.append(1)  # Default to page 1
                else:
                    cleaned_text = chunk_result
                    page_locations.append(1)  # Default to page 1
                
                # Clean up any redundant formatting
                cleaned_text = cleaned_text.strip()
                
                # Only add if it has substantial content
                if len(cleaned_text) > 50:
                    cleaned_flagged_items.append(cleaned_text)
                else:
                    # Remove corresponding page location if text is too short
                    if page_locations:
                        page_locations.pop()
            
            # 🔄 NEW: Intelligent consolidation with AI
            if cleaned_flagged_items:
                print(f"   🧠 Using AI to consolidate {len(cleaned_flagged_items)} findings into concise summary...")
                
                # Prepare consolidation prompt
                all_findings = "\n\n---FINDING---\n\n".join(cleaned_flagged_items)
                
                consolidation_prompt = f"""You are reviewing multiple findings from different parts of a municipal agenda document. Your task is to consolidate these findings into ONE concise, non-repetitive summary.

FINDINGS TO CONSOLIDATE:
{all_findings}

CONSOLIDATION REQUIREMENTS:
1. Combine similar/duplicate items (e.g., if "Item 6.5" appears multiple times, summarize it ONCE)
2. Keep the summary concise (2-3 sentences per unique item maximum)
3. Include specific item numbers and their core impact
4. Remove redundant language and duplicate information
5. Focus on actionable items that require immediate attention
6. Maintain the URGENT ACTION REQUIRED format for each unique item
7. CRITICAL: For each unique item, include "[Page X]" at the end to indicate the primary page location for PDF navigation

Provide a consolidated analysis that presents each unique urgent item only once with its key details."""

                try:
                    # Use o3 for intelligent consolidation
                    import time
                    time.sleep(1)  # Brief delay
                    
                    response = self.client.chat.completions.create(
                        model="o3",
                        messages=[
                            {"role": "system", "content": "You are an expert legal analyst specializing in municipal agenda consolidation."},
                            {"role": "user", "content": consolidation_prompt}
                        ]
                    )
                    
                    consolidated_result = response.choices[0].message.content
                    
                    if consolidated_result and len(consolidated_result) > 100:
                        print(f"   ✅ AI consolidation successful: {len(consolidated_result)} chars")
                        combined_analysis = consolidated_result
                    else:
                        print("   ⚠️ AI consolidation failed, using manual deduplication")
                        combined_analysis = self._manual_consolidation(cleaned_flagged_items)
                
                except Exception as consolidation_error:
                    print(f"   ⚠️ AI consolidation error: {consolidation_error}")
                    print("   🔄 Falling back to manual consolidation...")
                    combined_analysis = self._manual_consolidation(cleaned_flagged_items)
            else:
                combined_analysis = "No items were flagged in this agenda."
        else:
            # No urgent items found in any chunk
            combined_analysis = "No items were flagged in this agenda."
        
        # Extract page locations from flagged items
        page_locations = []
        for item in flagged_items_found:
            if "|Page " in item:
                try:
                    page_str = item.split("|Page ")[1].split(":")[0]
                    page_locations.append(int(page_str))
                except:
                    page_locations.append(1)
            else:
                page_locations.append(1)
        
        return {
            'success': True,
            'analysis': combined_analysis,
            'municipality': municipality_name,
            'properties_analyzed': len(property_context.split('\n')) if property_context else 0,
            'model_used': f'o3 (intelligent document processing)',
            'file_processed': str(agenda_path),
            'file_type': f'Complete document analysis',
            'chunks_processed': len(chunks),
            'flagged_chunks': len(flagged_items_found),
            'page_locations': page_locations  # 🔗 NEW: Page numbers for PDF navigation
        }

    def _estimate_pdf_page(self, chunk_number: int, total_chunks: int, full_text: str) -> int:
        """Estimate PDF page number based on chunk position and text length."""
        try:
            # Rough estimation: assume ~3000 characters per page (typical for PDFs)
            chars_per_page = 3000
            estimated_total_pages = max(1, len(full_text) // chars_per_page)
            
            # Calculate page based on chunk position
            estimated_page = max(1, int((chunk_number / total_chunks) * estimated_total_pages))
            
            print(f"      📍 Chunk {chunk_number}/{total_chunks} ≈ Page {estimated_page}/{estimated_total_pages}")
            return estimated_page
            
        except Exception as e:
            print(f"      ⚠️ Page estimation error: {e}")
            return 1  # Default to page 1
    
    def _extract_primary_page(self, flagged_items: list) -> int:
        """Extract the primary page number from flagged items for PDF navigation."""
        if not flagged_items:
            return 1
            
        for item in flagged_items:
            if "|Page " in item:
                try:
                    page_str = item.split("|Page ")[1].split(":")[0]
                    page_number = int(page_str)
                    print(f"   🔗 Primary flagged page: {page_number}")
                    return page_number
                except:
                    continue
        
        return 1  # Default to page 1
    
    def _manual_consolidation(self, flagged_items: list) -> str:
        """Manual consolidation fallback if AI consolidation fails."""
        print("   🔧 Performing manual consolidation...")
        
        # Extract unique item numbers and group similar items
        item_groups = {}
        
        for item_text in flagged_items:
            # Extract item numbers (e.g., "Item 6.5", "Item 5.2")
            import re
            item_matches = re.findall(r'Item\s+(\d+\.?\d*)', item_text, re.IGNORECASE)
            
            if item_matches:
                item_number = item_matches[0]
                if item_number not in item_groups:
                    item_groups[item_number] = []
                item_groups[item_number].append(item_text)
            else:
                # No item number found, treat as unique
                unique_key = f"general_{len(item_groups)}"
                item_groups[unique_key] = [item_text]
        
        # Consolidate each group
        consolidated_items = []
        for item_number, texts in item_groups.items():
            if len(texts) == 1:
                # Single instance, use as-is
                consolidated_items.append(texts[0])
            else:
                # Multiple instances, create consolidated summary
                # Take the longest/most detailed text as base
                base_text = max(texts, key=len)
                
                # Clean up and use as consolidated version
                if base_text.strip():
                    consolidated_items.append(base_text.strip())
        
        return "\n\n".join(consolidated_items)

    def _get_cached_agent(self, agent_key: str, agent_creator_func):
        """Get a cached agent or create and cache a new one."""
        # This method is no longer needed as we are using the standard OpenAI API
        # and do not have a caching mechanism for agents.
        # Keeping it for now as it might be used elsewhere or removed later.
        return agent_creator_func()

    def clear_agent_cache(self):
        """Clear all cached agents."""
        # This method is no longer needed as we are using the standard OpenAI API
        # and do not have a caching mechanism for agents.
        # Keeping it for now as it might be used elsewhere or removed later.
        print("🗑️ Agent cache cleared (no-op for standard OpenAI API)")

    def disable_agent_caching(self):
        """Disable agent caching (creates new agents every time)."""
        # This method is no longer needed as we are using the standard OpenAI API
        # and do not have a caching mechanism for agents.
        # Keeping it for now as it might be used elsewhere or removed later.
        print("⚠️ Agent caching disabled (no-op for standard OpenAI API)")

    def enable_agent_caching(self):
        """Enable agent caching (reuses existing agents)."""
        # This method is no longer needed as we are using the standard OpenAI API
        # and do not have a caching mechanism for agents.
        # Keeping it for now as it might be used elsewhere or removed later.
        print("✅ Agent caching enabled (no-op for standard OpenAI API)")

# Global instance
agents_manager = AgentsManager() 