import re
from pathlib import Path
from typing import List, Dict, Any
from athen.config import WIKI_DIR
from athen.llm import LLMClient

class LLMWiki:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.wiki_dir = WIKI_DIR
        self.wiki_dir.mkdir(parents=True, exist_ok=True)

    def get_all_pages(self) -> List[Path]:
        """List all markdown files in the wiki directory."""
        return list(self.wiki_dir.glob("*.md"))

    def query(self, query_text: str, limit: int = 3) -> str:
        """
        Simple keyword/regex-based retrieval to search wiki pages.
        Returns combined contents of relevant pages.
        """
        pages = self.get_all_pages()
        if not pages:
            return ""

        # Score pages by keyword match
        scored_pages = []
        words = set(re.findall(r'\w+', query_text.lower()))
        
        for page in pages:
            content = page.read_text(encoding="utf-8", errors="replace")
            content_lower = content.lower()
            title_lower = page.stem.lower()
            
            score = 0
            # Double weight for title matches
            for word in words:
                if word in title_lower:
                    score += 10
                if word in content_lower:
                    score += content_lower.count(word)
            
            if score > 0:
                scored_pages.append((score, page, content))

        # Sort descending by score
        scored_pages.sort(key=lambda x: x[0], reverse=True)
        top_pages = scored_pages[:limit]
        
        if not top_pages:
            return ""
            
        context_blocks = []
        for _, page, content in top_pages:
            context_blocks.append(f"--- WIKI PAGE: {page.name} ---\n{content}\n")
        
        return "\n".join(context_blocks)

    async def ingest(self, source_name: str, new_info: str) -> str:
        """
        Ingest new information. Uses the LLM client to update existing markdown pages
        or create new ones, compounding the knowledge.
        """
        # Get list of existing page names
        existing_pages = [p.stem for p in self.get_all_pages()]
        
        system_prompt = (
            "You are the Memory Engine of Athen Agents. Your job is to ingest new information "
            "into a persistent, interlinked set of Markdown wiki files (the 'second brain').\n"
            f"Existing wiki topics: {existing_pages}\n\n"
            "INSTRUCTIONS:\n"
            "1. Read the new information carefully.\n"
            "2. Decide if this updates an existing wiki page, or requires creating new pages.\n"
            "3. Return a JSON array of files to write or modify. Each item in the array MUST contain:\n"
            "   - 'filename': The title of the page (e.g. 'Project_Setup.md' or 'User_Preferences.md')\n"
            "   - 'action': 'create' or 'update'\n"
            "   - 'content': The complete, updated, and well-structured Markdown content for that page.\n"
            "4. Keep the pages structured, concise, and interlinked using standard Markdown links (e.g., [[OtherPage]] or [OtherPage](file://...)).\n"
            "5. Respond ONLY with a valid JSON array. Do not wrap in markdown code blocks."
        )

        prompt = f"Source: {source_name}\nNew Information:\n{new_info}"
        
        try:
            res = await self.llm_client.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                temperature=0.2
            )
            
            content = res["content"].strip()
            # Strip markdown json blocks if returned
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
                
            operations = json.loads(content)
            results = []
            for op in operations:
                filename = op["filename"]
                # Clean filename
                filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '', filename)
                if not filename.endswith(".md"):
                    filename += ".md"
                
                filepath = self.wiki_dir / filename
                filepath.write_text(op["content"], encoding="utf-8")
                results.append(f"{op['action'].capitalize()}d wiki page: {filename}")
                
            return "\n".join(results) if results else "No wiki pages needed updates."
        except Exception as e:
            return f"Failed to auto-ingest into Wiki: {str(e)}"

    async def lint(self) -> str:
        """
        Scans all wiki files to fix links, merge duplicate pages,
        and resolve contradictions.
        """
        pages = self.get_all_pages()
        if not pages:
            return "Wiki is empty. Nothing to lint."

        wiki_data = {}
        for p in pages:
            wiki_data[p.name] = p.read_text(encoding="utf-8", errors="replace")

        system_prompt = (
            "You are the Wiki Linter for Athen Agents. Analyze the current set of wiki pages "
            "and suggest merges, deletions, or link fixes to prevent contradictions and duplicates.\n"
            "Return a JSON object containing:\n"
            " - 'actions': A list of file changes. Each action has 'filename', 'action' ('update' or 'delete'), and 'content' (if update).\n"
            " - 'summary': A summary of changes made.\n"
            "Respond ONLY with valid JSON. Do not include markdown formatting."
        )

        prompt = f"Current Wiki Data:\n{json.dumps(wiki_data, indent=2)}"
        
        try:
            res = await self.llm_client.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                temperature=0.2
            )
            
            content = res["content"].strip()
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
                
            data = json.loads(content)
            actions = data.get("actions", [])
            for act in actions:
                filename = act["filename"]
                action = act["action"]
                filepath = self.wiki_dir / filename
                
                if action == "delete" and filepath.exists():
                    filepath.unlink()
                elif action == "update":
                    filepath.write_text(act["content"], encoding="utf-8")
            
            return f"Wiki Lint Completed:\n{data.get('summary', 'No changes proposed.')}"
        except Exception as e:
            return f"Wiki lint failed: {str(e)}"

    def get_links(self) -> Dict[str, Any]:
        """Return relationship links between wiki files based on link mentions."""
        pages = self.get_all_pages()
        nodes = [p.stem for p in pages]
        links = []
        for p in pages:
            content = p.read_text(encoding="utf-8", errors="replace")
            # Find [[Topic]] links
            matches = re.findall(r'\[\[(.*?)\]\]', content)
            for m in matches:
                target = m.split('|')[0].strip()
                if target in nodes:
                    links.append({"source": p.stem, "target": target})
        return {"nodes": nodes, "links": links}

import json
