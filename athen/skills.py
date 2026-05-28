import re
from pathlib import Path
from typing import List, Dict, Any
from athen.config import SKILLS_DIR

class SkillsEngine:
    def __init__(self):
        self.skills_dir = SKILLS_DIR
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def get_all_skills(self) -> List[Dict[str, str]]:
        """Retrieve all saved skills with their titles and descriptions."""
        skills = []
        for file in self.skills_dir.glob("*.md"):
            content = file.read_text(encoding="utf-8", errors="replace")
            # Try to extract Description from markdown file
            desc_match = re.search(r"## Description\n(.*?)(\n##|$)", content, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else "No description available."
            skills.append({
                "name": file.stem,
                "file_path": str(file),
                "description": description,
                "content": content
            })
        return skills

    def save_skill(self, name: str, description: str, usage_instructions: str) -> Path:
        """Save a newly learned skill in markdown format."""
        # Sanitize name
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name).lower()
        filepath = self.skills_dir / f"{safe_name}.md"
        
        markdown_content = f"""# Skill: {name}

## Description
{description}

## Usage Instructions
{usage_instructions}
"""
        filepath.write_text(markdown_content, encoding="utf-8")
        return filepath

    def query_skills(self, task_description: str) -> str:
        """
        Scan skills and return instruction text for any skills matching the task.
        """
        skills = self.get_all_skills()
        matched_blocks = []
        
        words = set(re.findall(r'\w+', task_description.lower()))
        for skill in skills:
            # Simple keyword matching on description and name
            score = 0
            for word in words:
                if word in skill["name"].lower():
                    score += 5
                if word in skill["description"].lower():
                    score += 1
            
            if score >= 3: # Match threshold
                matched_blocks.append(
                    f"### Learned Skill: {skill['name']}\n{skill['content']}\n"
                )
                
        if not matched_blocks:
            return ""
            
        return "\n## RELEVANT SKILLS PREVIOUSLY LEARNED:\n" + "\n".join(matched_blocks)
