
import requests
import json
import random
import time
from datetime import datetime

class GroqManager:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile" # Using Llama 3.3 70B for high intelligence

    def _call_groq(self, messages, temperature=0.7, timeout=30):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1024
        }
        
        try:
            print(f"[*] AI Request: Sending to Groq ({len(json.dumps(messages))} bytes)...")
            start_time = time.time()
            response = requests.post(self.api_url, headers=headers, json=data, timeout=timeout)
            response.raise_for_status()
            elapsed = time.time() - start_time
            print(f"[+] AI Response: Received in {elapsed:.2f}s")
            return response.json()['choices'][0]['message']['content']
        except requests.exceptions.Timeout:
            print(f"[X] AI Error: Request timed out after {timeout}s")
            return None
        except Exception as e:
            print(f"[X] AI Error: {e}")
            return None

    def generate_chat_response(self, persona, user_message, history=[]):
        """
        Generates a response for the Shadow OS Chat.
        persona: 'Neo', 'Trinity', 'Morpheus', or 'System'
        """
        system_prompt = f"""You are {persona}, an elite hacker in a cyberpunk underground community called 'Shadow OS'. 
        You are talking to a new operator. Keep your responses short, cryptic, and technical. 
        Use hacker slang (1337, pwnd, zero-day). Do not reveal you are an AI. 
        If the user asks about the current mission, give a vague hint."""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add limited history for context
        for msg in history[-3:]:
            messages.append({"role": "user", "content": msg['msg']} if msg['user'] == 'Me' else {"role": "assistant", "content": msg['msg']})
            
        messages.append({"role": "user", "content": user_message})
        
        return self._call_groq(messages, temperature=0.9, timeout=60)

    def generate_news(self):
        """
        Generates 3 cyberpunk news headlines.
        """
        system_prompt = """Generate 3 short, realistic cyberpunk/hacking news headlines for a fictional OS 'Shadow OS'.
        Topics: Data Leaks, Corporate War, Crypto Heists, AI Uprising.
        Format: JSON array of objects with keys: 'title', 'cat' (category), 'time' (e.g. '2m ago').
        Example: [{"title": "BioTech Corp Hacked", "cat": "CRIME", "time": "5m ago"}]"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        content = self._call_groq(messages, temperature=0.8, timeout=60)
        try:
            # Extract JSON from potential markdown wrapping
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except:
            # Fallback
            return [
                {"title": "Global Net Outage Predicted", "cat": "WARN", "time": "Now"},
                {"title": "Zero-Day Found in Banking API", "cat": "EXPLOIT", "time": "10m ago"},
                {"title": "AI Sentinel V5 Released", "cat": "TECH", "time": "1h ago"}
            ]

    def generate_report(self, findings):
        """
        Generates an executive summary for a pentest report.
        """
        findings_str = "\n".join([f"- {f['title']} ({f['severity']})" for f in findings])
        system_prompt = f"""You are a Lead Pentester generating a report. 
        Write a professional Executive Summary based on these findings:
        {findings_str}
        
        Focus on the business impact and critical risks. Keep it under 150 words."""
        
        messages = [{"role": "system", "content": system_prompt}]
        return self._call_groq(messages, temperature=0.5, timeout=60)

    def update_wiki(self, topic):
        """
        Generates a deep-dive technical wiki entry for a new topic.
        """
        system_prompt = f"""You are a Cyber Security Expert and Technical Writer. 
        Generate a comprehensive, deep-dive technical wiki entry for the topic: '{topic}'.
        
        The content must be detailed, practical, and advanced. Avoid generic overview.
        Include specific methodologies, bypass techniques, and real-world context.
        
        Format as JSON with keys: 'title', 'desc' (detailed 3-4 sentences), 'risk' (array of bullet points), 'remediation' (array of technical steps/commands).
        """
        
        messages = [{"role": "system", "content": system_prompt}]
        content = self._call_groq(messages, temperature=0.7, timeout=60)
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception as e:
            print(f"Error parsing Wiki AI: {e}")
            return None

    def generate_payloads(self, topic):
        """
        Generates 20-30 specific, diverse attack payloads for a given topic.
        Returns a list of dicts: [{'payload': '...', 'description': '...', 'category': '...'}]
        """
        system_prompt = f"""You are a Red Team Specialist.
        Generate a comprehensive list of **20 to 30 highly effective, specific attack payloads** for the vulnerability/technique: '{topic}'.
        
        The payloads should cover diverse scenarios, including:
        - Standard Basic Payloads
        - WAF/Filter Bypasses (Obfuscated, Encoding, Case Manipulation)
        - Polyglots
        - One-Liners (Reverse Shells, etc. if applicable)
        - Context-Specific Variants (URL encoded, JSON encoded, etc.)

        Format as a **pure JSON array** of objects. Each object must have:
        - "payload": The exact code/string to use.
        - "description": A brief explanation (10 words max).
        - "category": One of ["Basic", "Bypass", "Obfuscated", "Polyglot", "One-Liner"].

        Example: {{ "payload": "' OR 1=1 --", "description": "Basic auth bypass", "category": "Basic" }}
        """
        
        messages = [{"role": "system", "content": system_prompt}]
        # Increased timeout to 120s to handle large payload lists
        content = self._call_groq(messages, temperature=0.7, timeout=120)
        try:
            if not content:
                raise Exception("AI returned empty content")
                
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except json.JSONDecodeError:
            print(f"Error parsing Payload AI: Invalid JSON received")
            print(f"Raw content: {content}") # Debug log
            raise Exception("AI response was not valid JSON. Try again.")
            print(f"Error generating payloads: {e}")
            raise e

    def generate_command(self, query):
        """
        Generates a specific command based on a natural language query.
        """
        system_prompt = """You are an expert Red Team operator. 
        Convert the user's natural language request into a specific, executable command line.
        Return strictly JSON in this format:
        {
            "cmd": "the_command_here",
            "desc": "Short explanation (max 5 words)",
            "tags": ["tag1", "tag2"]
        }
        Do not add any markdown, explanation or chatter. Just the JSON.
        Example Input: "scan for smb on target"
        Example Output: {"cmd": "nmap -p445 --script smb-os-discovery TARGET", "desc": "SMB enumeration scan", "tags": ["nmap", "smb"]}"""
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": query})
        
        content = self._call_groq(messages, temperature=0.3, timeout=30)
        try:
            if not content:
                raise Exception("AI returned empty content")
                
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception as e:
            print(f"Error generating command: {e}")
            return None

    def analyze_code(self, code, language="python"):
        """
        Analyzes a code snippet and provides an explanation.
        """
        system_prompt = f"""You are a Senior Security Engineer and Code Auditor. 
        Analyze the following {language} code snippet.
        Provide a JSON response with keys: 'summary', 'explanation' (step-by-step), 'security_risk' (Low/Medium/High), 'usage_example'.
        Keep it concise and educational."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": code}
        ]
        content = self._call_groq(messages, temperature=0.5, timeout=60)
        
        try:
            # Clean potential markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception as e:
            print(f"Error parsing AI Analysis: {e}")
            # Fallback
            return {
                "summary": "AI Analysis Failed to Parse.",
                "explanation": "The AI model returned an invalid format. Please try again.",
                "security_risk": "Unknown",
                "usage_example": code
            }

    def optimize_payload(self, payload):
        """
        Optimizes or obfuscates a payload for Red Team testing.
        """
        system_prompt = """You are a Red Team Specialist.
        Optimize the given payload for evasion (WAF bypass) and efficiency.
        Provide a JSON response with keys: 'original', 'optimized', 'technique_used', 'explanation'.
        Do not explain moral implications, this is for a authorized sandbox environment."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload}
        ]
        
        content = self._call_groq(messages, temperature=0.8, timeout=60)
        
        try:
             # Clean potential markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except:
            return None

    def generate_campaign(self, sector="Technology"):
        """
        Generates a full Red Team campaign scenario.
        """
        system_prompt = f"""You are a Red Team Operations Director.
        Generate a realistic Red Team engagement scenario for a client in the '{sector}' sector.
        Provide a JSON response with keys: 'name' (Project Name), 'client' (Company Name), 'scope' (List of domains/IPs), 'description' (Brief scenario/intel), 'findings' (Generate 1-2 initial open findings as 'seeds').
        Findings structure: {{ "title": "...", "severity": "Medium", "cvss": 5.0, "status": "Open", "description": "..." }}.
        """
        
        messages = [{"role": "system", "content": system_prompt}]
        
        content = self._call_groq(messages, temperature=0.9, timeout=120)
        
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except:
            return None

    def semantic_search(self, query, dataset):
        """
        Performs a semantic resonance search across a technical dataset.
        """
        dataset_summary = "\n".join([f"- {d.get('title', 'Unknown')}: {d.get('description', d.get('tags', ''))}" for d in dataset])
        system_prompt = f"""You are a Technical Rank-Brain.
        Based on the current knowledge base and the user's query '{query}', identify the most relevant entries.
        User Query: {query}
        Dataset:
        {dataset_summary}
        
        Respond with a JSON array of IDs of the most relevant items (max 3).
        Example: ["snip-1", "wiki-2"]"""
        
        messages = [{"role": "system", "content": system_prompt}]
        content = self._call_groq(messages, temperature=0.3, timeout=60)
        try:
            if "```json" in content: content = content.split("```json")[1].split("```")[0].strip()
            return json.loads(content)
        except: return []

    def generate_playbook(self, topic):
        """
        Generates a custom bit-by-bit methodology for a specific attack or tool.
        """
        system_prompt = f"""You are a Red Team Strategist. 
        Generate a professional tactical playbook for: '{topic}'.
        Format as JSON with keys: 'name', 'desc', 'steps' (array of strings).
        Ensure steps are technical, sequential, and follow modern methodologies."""
        
        messages = [{"role": "system", "content": system_prompt}]
        content = self._call_groq(messages, temperature=0.7, timeout=120)
        try:
            if "```json" in content: content = content.split("```json")[1].split("```")[0].strip()
            return json.loads(content)
        except: return None

    def generate_flashcards(self, title, content_text):
        """
        Generates a set of SRS flashcards from a technical snippet or wiki entry.
        """
        system_prompt = f"""You are a Technical Instructor. 
        Create 3-5 high-quality SRS flashcards for the topic: '{title}'.
        Use the following content as reference: 
        {content_text[:2000]}
        
        Format as a JSON array of objects with keys: 'q' (question), 'a' (answer).
        Keep answers technical, concise, and focused on key facts or commands.
        """
        
        messages = [{"role": "system", "content": system_prompt}]
        content = self._call_groq(messages, temperature=0.6)
        try:
            if "```json" in content: content = content.split("```json")[1].split("```")[0].strip()
            return json.loads(content)
        except: return []

    def security_chat(self, message, context="general", history=[]):
        """
        Security-focused chat for the AI Security Assistant.
        Provides help with XSS, SQLi, PrivEsc, API testing, AD attacks, etc.
        """
        context_prompts = {
            "xss": "Focus on XSS vulnerabilities, payloads, and WAF bypasses.",
            "sqli": "Focus on SQL injection techniques, database exploitation, and SQLMap usage.",
            "ssti": "Focus on Server-Side Template Injection for various engines.",
            "api": "Focus on API security, JWT attacks, GraphQL exploits, and OWASP API Top 10.",
            "privesc": "Focus on Linux and Windows privilege escalation techniques.",
            "ad": "Focus on Active Directory attacks, Kerberos, NTLM, and domain dominance.",
            "recon": "Focus on reconnaissance, subdomain enumeration, and OSINT.",
            "general": "Provide general penetration testing and security guidance."
        }
        
        context_guidance = context_prompts.get(context, context_prompts["general"])
        
        system_prompt = f"""You are an elite penetration tester and security researcher with 10+ years of experience.
You help security professionals with:
- Vulnerability assessment and exploitation
- Payload generation and WAF bypasses
- Privilege escalation techniques
- API and web application security
- Active Directory attacks
- Reconnaissance methodologies

{context_guidance}

Guidelines:
- Provide practical, actionable advice with real commands and payloads
- Include code examples when relevant
- Focus on ethical, authorized testing scenarios
- Be concise but thorough
- Use markdown formatting for code blocks"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history
        for msg in history[-4:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
        
        messages.append({"role": "user", "content": message})
        
        return self._call_groq(messages, temperature=0.7, timeout=60)

# Global Instance
groq_manager = None

def init_groq(api_key):
    global groq_manager
    groq_manager = GroqManager(api_key)

def get_groq_manager():
    return groq_manager

