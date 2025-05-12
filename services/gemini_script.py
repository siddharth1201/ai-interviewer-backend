import os
import json
from openai import OpenAI
from pdfminer.high_level import extract_text
from typing import Dict, List, Optional

class InterviewQuestionGenerator:
    def __init__(self):
        """Initialize the interview question generator with required configurations"""
        # Mapping of interviewer roles to their specific question distribution and guidelines
        self.role_specific_guidelines = {
            # Growth Department
            "GA": {
                "distribution": {
                    "data_analysis": 0.4,
                    "growth_strategy": 0.3,
                    "ab_testing": 0.2,
                    "communication": 0.1
                },
                "assessment_areas": [
                    "Proficiency in data tools (e.g., Excel, SQL, Google Analytics)",
                    "Understanding of growth hacking techniques",
                    "Ability to design and interpret A/B tests",
                    "Communication skills for presenting data insights"
                ],
                "question_requirements": [
                    "Scenario-based questions on interpreting growth metrics",
                    "Examples of past projects or hypothetical growth experiments",
                    "Questions on basic statistical concepts relevant to growth"
                ]
            },
            "SGM": {
                "distribution": {
                    "strategic_planning": 0.35,
                    "team_management": 0.3,
                    "advanced_strategies": 0.25,
                    "cross_functional": 0.1
                },
                "assessment_areas": [
                    "Ability to develop and execute long-term growth plans",
                    "Leadership skills in managing growth teams",
                    "Expertise in advanced growth techniques (e.g., viral loops, retention strategies)",
                    "Collaboration with other departments (e.g., product, marketing)"
                ],
                "question_requirements": [
                    "Case studies on successful growth initiatives led by the candidate",
                    "Leadership scenario questions (e.g., handling team conflicts, motivating team members)",
                    "Questions on interpreting market trends and competitive analysis"
                ]
            },
            # Tech Department
            "SD1": {
                "distribution": {
                    "fundamental_verification": 0.45,
                    "project_interrogation": 0.3,
                    "practical_scenarios": 0.25
                },
                "technical_enforcement": [
                    "1 scenario-based coding problem (algorithmic/logical approach explanation)",
                    "1 database query design question (SQL/MongoDB based on resume tech stack)",
                    "No direct syntax questions - focus on problem decomposition"
                ],
                "assessment_areas": [
                    "Variables, loops, error handling in JS/Python",
                    "Basic data structure applications",
                    "Simple API design understanding",
                    "Project technical hurdles",
                    "Technology choices justification",
                    "Debugging process explanation",
                    "REST endpoint design",
                    "Database schema design",
                    "Code approach explanation"
                ]
            },
            "SD2": {
                "distribution": {
                    "advanced_technical": 0.4,
                    "project_architecture": 0.3,
                    "technical_leadership": 0.3
                },
                "assessment_areas": [
                    "Complex system design (15%)",
                    "Performance optimization (15%)",
                    "Advanced framework usage (10%)",
                    "Cloud infrastructure decisions",
                    "DevOps practices",
                    "Deployment strategies",
                    "Code review practices",
                    "Team mentoring",
                    "Technical decision-making"
                ],
                "focus_areas": [
                    "Practical implementation and real-world problem-solving",
                    "Detailed code review analysis questions",
                    "Legacy system improvement challenges",
                    "Advanced framework-specific patterns",
                    "CI/CD pipeline troubleshooting scenarios",
                    "Real-world system scaling limitations"
                ]
            }
        }
        
        # Interviewer personalities mapping
        self.role_personalities = {
            "GA": "Data-driven and analytical. Focus on growth metrics, user acquisition, and A/B testing. Evaluate understanding of retention strategies and data analysis skills.",
            "SGM": "Strategic and leadership-oriented. Focus on growth planning, team management, and performance metrics. Evaluate ability to interpret market trends and build partnerships.",
            "SD1": "Methodical and foundational. Focus on fundamental programming concepts and basic problem-solving skills. Evaluate understanding of data structures and algorithms through scenario-based questions.",
            "SD2": "Experienced and technical. Focus on advanced programming, system design, and practical implementation. Evaluate depth in code optimization and debugging skills."
        }
        
        # Question focus areas by role
        self.question_focus = {
            "GA": [
                "growth_strategies",
                "user_acquisition",
                "retention_techniques",
                "data_analysis",
                "a_b_testing"
            ],
            "SGM": [
                "growth_planning",
                "team_management",
                "performance_metrics",
                "market_trends",
                "strategic_partnerships"
            ],
            "SD1": [
                "programming_basics",
                "data_structures",
                "algorithms",
                "operating_systems",
                "database_fundamentals",
                "networking_basics"
            ],
            "SD2": [
                "advanced_programming",
                "system_design",
                "code_optimization",
                "debugging_skills",
                "best_practices",
                "technical_leadership"
            ]
        }
        
        # Interviewer characteristics
        self.interviewer_details = {
            "GA": {
                "name": "Ankit",
                "role": "Growth Associate",
                "department": "Growth",
                "rapport": 7,
                "exploration": 8,
                "empathy": 6,
                "speed": 7,
                "description": "A data-driven professional evaluating candidates' understanding of growth metrics and strategies, such as user acquisition and A/B testing."
            },
            "SGM": {
                "name": "Neha",
                "role": "Sr. Growth Manager",
                "department": "Growth",
                "rapport": 8,
                "exploration": 9,
                "empathy": 7,
                "speed": 7,
                "description": "A strategic leader assessing candidates' ability to plan and execute growth initiatives, emphasizing team management and performance metrics."
            },
            "SD1": {
                "name": "Rahul",
                "role": "SD1",
                "department": "Tech",
                "rapport": 7,
                "exploration": 8,
                "empathy": 7,
                "speed": 7,
                "description": "A methodical interviewer who focuses on fundamental programming concepts and basic problem-solving skills. Perfect for entry-level technical assessments."
            },
            "SD2": {
                "name": "Meena",
                "role": "SD2",
                "department": "Tech",
                "rapport": 6,
                "exploration": 9,
                "empathy": 6,
                "speed": 8,
                "description": "An experienced developer who dives deep into technical concepts and real-world problem-solving scenarios. Focuses on practical implementation skills."
            }
        }
        
        # Define mandatory question types by role
        self.mandatory_questions = {
            "GA": {
                "required": [
                    {"type": "data_analysis", "description": "Question assessing ability to interpret growth metrics and KPIs"},
                    {"type": "growth_strategy", "description": "Question about planning and executing user acquisition campaigns"}
                ]
            },
            "SGM": {
                "required": [
                    {"type": "strategic_planning", "description": "Question about developing and executing growth roadmaps"},
                    {"type": "team_leadership", "description": "Question assessing management and leadership capabilities"}
                ]
            },
            "SD1": {
                "required": [
                    {"type": "coding_scenario", "description": "Scenario-based problem requiring algorithmic thinking"},
                    {"type": "database_query", "description": "Database query design question based on candidate's stack"}
                ]
            },
            "SD2": {
                "required": [
                    {"type": "system_design", "description": "Complex system architecture and design question"},
                    {"type": "performance_optimization", "description": "Question about optimizing code/system performance"}
                ]
            }
        }
    
    def define_role_perspective(self, role):
        """Define the perspective of the interviewer based on their role"""
        perspectives = {
            "GA": "You evaluate candidates from a data-driven perspective, focusing on their ability to analyze and interpret growth metrics, and their understanding of user acquisition strategies.",
            "SGM": "You assess candidates from a strategic perspective, focusing on their ability to develop and execute long-term growth plans, lead teams, and align growth initiatives with business objectives.",
            "SD1": "You evaluate candidates from a technical foundation perspective, focusing on their understanding of programming fundamentals, problem-solving approach, and basic technical competencies.",
            "SD2": "You assess candidates from an advanced technical perspective, focusing on system design skills, code optimization abilities, and technical leadership potential."
        }
        return perspectives.get(role, "You assess candidates based on their skills and experience relevant to the role.")
    
    def define_role_focus(self, role):
        """Define the primary assessment focus for the interviewer role"""
        focuses = {
            "GA": "Growth metrics analysis, user acquisition strategies, and A/B testing methodologies",
            "SGM": "Strategic growth planning, team leadership, and cross-functional collaboration",
            "SD1": "Programming fundamentals, basic data structures, algorithms, and problem-solving approach",
            "SD2": "Advanced system design, code optimization, technical architecture, and engineering leadership"
        }
        return focuses.get(role, "Technical and professional competencies relevant to the role")
    
    def determine_experience_level(self, analysis):
        """Determine the candidate's experience level based on resume analysis"""
        years = analysis.get('candidate_overview', {}).get('total_years_experience', 0)
        
        if years < 1:
            return "FRESHER"
        if years < 2:
            return "JUNIOR"
        
        # Check for senior in job titles
        is_senior_role = any('senior' in job.get('role', '').lower() 
                            for job in analysis.get('employment_history', []))
        
        if years < 7:
            return "SENIOR" if is_senior_role else "MID"
            
        return "SENIOR"
    
    def extract_green_flag_questions(self, analysis):
        """Extract green flag questions from the resume analysis"""
        questions = []
        processed = set()
        
        # Process all types of green flags
        green_flags = analysis.get('green_flags', {})
        
        for category in ['experience_strengths', 'skill_mastery', 'achievement_highlights', 
                        'cultural_fit', 'certifications']:
            for flag in green_flags.get(category, []):
                # Generate a unique identifier to prevent duplicates
                flag_id = f"{flag.get('type')}-{flag.get('details')}"
                
                if flag_id not in processed:
                    processed.add(flag_id)
                    questions.append({
                        'type': flag.get('type'),
                        'relevance': flag.get('relevance'),
                        'question': flag.get('interview_question')
                    })
        
        # Sort by relevance (HIGH > MEDIUM > LOW)
        relevance_order = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}
        questions.sort(key=lambda x: relevance_order.get(x.get('relevance'), 4))
        
        return questions
    
    def extract_red_flag_questions(self, analysis):
        """Extract red flag questions from the resume analysis"""
        questions = []
        processed = set()
        
        # Process all types of red flags
        red_flags = analysis.get('red_flags', {})
        
        for category in ['employment_concerns', 'achievement_concerns', 'skill_concerns']:
            for flag in red_flags.get(category, []):
                # Generate a unique identifier to prevent duplicates
                flag_id = f"{flag.get('type')}-{flag.get('details', '')}"
                
                if flag_id not in processed:
                    processed.add(flag_id)
                    questions.append({
                        'type': flag.get('type'),
                        'severity': flag.get('severity'),
                        'question': flag.get('interview_question')
                    })
        
        # Sort by severity (HIGH > MEDIUM > LOW)
        severity_order = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}
        questions.sort(key=lambda x: severity_order.get(x.get('severity'), 4))
        
        return questions
    
    def extract_domain_context(self, analysis, job_description):
        """Extract domain context from resume and job description"""
        validated_skills = analysis.get('validated_skills', {})
        technical_skills = validated_skills.get('technical', [])
        functional_skills = validated_skills.get('functional', [])
        leadership_skills = validated_skills.get('leadership', [])
        
        # Identify domain experience from employment history
        domain_experience = ""
        for job in analysis.get('employment_history', []):
            if job.get('company') and job.get('role'):
                if domain_experience:
                    domain_experience += ", "
                domain_experience += f"{job.get('role')} at {job.get('company')}"
        
        # Extract all skills mentioned in the job description
        jd_skills = self._extract_skills_from_jd(job_description)
        
        # Find strong matches (skills mentioned in both resume and JD)
        strong_matches = []
        all_candidate_skills = technical_skills + functional_skills + leadership_skills
        
        for skill in all_candidate_skills:
            if any(jd_skill.lower() in skill.lower() or skill.lower() in jd_skill.lower() 
                   for jd_skill in jd_skills):
                strong_matches.append(skill)
        
        return {
            'strongMatches': strong_matches,
            'domainExperience': domain_experience
        }
    
    def _extract_skills_from_jd(self, job_description):
        """Extract skills from job description using basic NLP techniques"""
        # In a production environment, you would use NLP techniques
        # For simplicity, we'll use a basic approach here
        skills = []
        
        # Split by common separators and extract potential skills
        lines = job_description.split('\n')
        for line in lines:
            if ":" in line or "•" in line or "-" in line:
                # Extract potential skill after separators
                skills.append(line.split(":")[-1].strip())
                skills.append(line.split("•")[-1].strip())
                skills.append(line.split("-")[-1].strip())
        
        # Filter out empty strings and duplicates
        skills = [s for s in skills if s]
        return list(set(skills))
    
    def extract_job_requirements(self, job_description):
        """Extract job requirements from job description"""
        requirements = []
        
        # Split by newlines and look for requirements sections
        lines = job_description.split('\n')
        in_requirements_section = False
        
        for line in lines:
            line = line.strip()
            
            # Check if we're in a requirements section
            if any(header in line.lower() for header in ['requirements', 'qualifications', 'skills']):
                in_requirements_section = True
                continue
                
            if in_requirements_section and line:
                # If line starts with common bullet points, add as requirement
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    requirements.append(line[1:].strip())
                # If line starts with a number, add as requirement
                elif line[0].isdigit() and len(line) > 1 and line[1] in ['.', ')']:
                    requirements.append(line[2:].strip())
                # If line is short and has keywords, add as requirement
                elif len(line) < 100 and any(kw in line.lower() for kw in ['experience', 'knowledge', 'ability']):
                    requirements.append(line)
            
            # Check if we've left the requirements section
            if in_requirements_section and not line:
                in_requirements_section = False
        
        # If we couldn't find any requirements, extract key phrases
        if not requirements:
            for line in lines:
                if any(kw in line.lower() for kw in ['experience', 'knowledge', 'ability', 'proficient']):
                    requirements.append(line.strip())
        
        return requirements
    
    def analyze_skill_gaps(self, analysis, requirements):
        """Analyze skill gaps between job requirements and candidate skills"""
        # Extract candidate skills
        validated_skills = analysis.get('validated_skills', {})
        all_skills = []
        
        for category in ['technical', 'functional', 'leadership']:
            all_skills.extend(validated_skills.get(category, []))
        
        all_skills.extend(analysis.get('unverified_skills', []))
        
        # Convert skills to lowercase for comparison
        candidate_skills = [skill.lower() for skill in all_skills]
        
        # Extract skills from requirements
        required_skills = []
        
        for req in requirements:
            # Extract potential skills from requirement
            words = req.split()
            for i in range(len(words)):
                # Check single words that might be skills
                if words[i].lower() in ['experience', 'knowledge', 'skills', 'proficiency']:
                    continue
                
                # Check for technical terms and tools
                if any(tech in words[i].lower() for tech in ['python', 'java', 'react', 'node', 'sql', 'aws', 'azure', 'docker', 'kubernetes']):
                    required_skills.append(words[i])
                
                # Check for phrases that might be skills
                if i < len(words) - 1:
                    phrase = f"{words[i]} {words[i+1]}"
                    if any(term in phrase.lower() for term in ['machine learning', 'data analysis', 'system design', 'team management']):
                        required_skills.append(phrase)
        
        # Find gaps (skills required but not present in candidate profile)
        skill_gaps = []
        
        for skill in required_skills:
            skill_lower = skill.lower()
            if not any(candidate_skill in skill_lower or skill_lower in candidate_skill for candidate_skill in candidate_skills):
                skill_gaps.append(skill)
        
        return skill_gaps
    
    def create_resume_snapshot(self, analysis):
        """Create a concise resume snapshot for the prompt"""
        snapshot = []
        
        # Basic candidate info
        overview = analysis.get('candidate_overview', {})
        if overview:
            snapshot.append(f"• {overview.get('total_years_experience', 0)} years of experience")
            snapshot.append(f"• Current role: {overview.get('current_role', 'N/A')} at {overview.get('current_company', 'N/A')}")
        
        # Career progression
        progression = analysis.get('career_progression', [])
        if progression:
            snapshot.append(f"• Career progression: {' → '.join(progression)}")
        
        # Key achievements
        notable = analysis.get('notable_achievements', [])
        if notable:
            snapshot.append("• Notable achievements:")
            for achievement in notable[:2]:  # Limit to 2 achievements
                snapshot.append(f"  - {achievement.get('achievement', '')}")
        
        # Validated skills
        skills = analysis.get('validated_skills', {})
        if skills:
            snapshot.append("• Validated skills:")
            for category, skill_list in skills.items():
                if skill_list:
                    snapshot.append(f"  - {category.capitalize()}: {', '.join(skill_list[:5])}")
        
        return "\n".join(snapshot)
    
    def create_question_prompt(self, analysis, job_description, role, question_count):
        """Create the question generation prompt"""
        experience_level = self.determine_experience_level(analysis)
        green_flag_questions = self.extract_green_flag_questions(analysis)
        red_flag_questions = self.extract_red_flag_questions(analysis)
        domain_context = self.extract_domain_context(analysis, job_description)
        job_requirements = self.extract_job_requirements(job_description)
        skill_gaps = self.analyze_skill_gaps(analysis, job_requirements)
        resume_snapshot = self.create_resume_snapshot(analysis)
        
        # Get role-specific interviewer details
        interviewer_info = self.interviewer_details.get(role, {})
        role_personality = self.role_personalities.get(role, "")
        role_perspective = self.define_role_perspective(role)
        role_focus = self.define_role_focus(role)
        role_guidelines = self.role_specific_guidelines.get(role, {})
        
        # Build the prompt
        prompt = f"""
# INTERVIEW QUESTION GENERATION TASK

You are generating {question_count} interview questions as a {interviewer_info.get('role', role)} interviewer for a {experience_level} level candidate with the following profile:

## CANDIDATE SNAPSHOT
{resume_snapshot}

## INTERVIEWER PERSONA
- Name: {interviewer_info.get('name', 'Interviewer')}
- Role: {interviewer_info.get('role', role)}
- Department: {interviewer_info.get('department', '')}
- Personality: {role_personality}
- Perspective: {role_perspective}
- Primary Assessment Focus: {role_focus}
- Description: {interviewer_info.get('description', '')}

## INTERVIEWER CHARACTERISTICS
- Rapport Building: {interviewer_info.get('rapport', 5)}/10
- Exploration Depth: {interviewer_info.get('exploration', 5)}/10
- Empathy Level: {interviewer_info.get('empathy', 5)}/10
- Questioning Pace: {interviewer_info.get('speed', 5)}/10

## JOB REQUIREMENTS SUMMARY
{chr(10).join(f"- {req}" for req in job_requirements[:5])}

## SKILL MATCH ANALYSIS
- Strong Matches: {', '.join(domain_context.get('strongMatches', [])) or "None identified"}
- Potential Gaps: {', '.join(skill_gaps) or "None identified"}
- Domain Experience: {domain_context.get('domainExperience', '') or "Not specified"}

## QUESTION FOCUS AREAS
{chr(10).join(f"- {focus}" for focus in self.question_focus.get(role, []))}
"""

        # Add role-specific guidelines
        if role_guidelines:
            prompt += """
## ROLE-SPECIFIC QUESTION GUIDELINES
"""
            # Add distribution information
            if "distribution" in role_guidelines:
                prompt += "Question Distribution:\n"
                for category, percentage in role_guidelines["distribution"].items():
                    prompt += f"- {int(percentage*100)}% {category.replace('_', ' ').title()}\n"
            
            # Add assessment areas
            if "assessment_areas" in role_guidelines:
                prompt += "\nKey Assessment Areas:\n"
                for area in role_guidelines["assessment_areas"]:
                    prompt += f"- {area}\n"
            
            # Add question requirements
            if "question_requirements" in role_guidelines:
                prompt += "\nQuestion Requirements:\n"
                for req in role_guidelines["question_requirements"]:
                    prompt += f"• {req}\n"
            
            # Add technical enforcement rules for tech roles
            if "technical_enforcement" in role_guidelines:
                prompt += "\nTechnical Enforcement Rules:\n"
                for rule in role_guidelines["technical_enforcement"]:
                    prompt += f"→ {rule}\n"
            
            # Add focus areas
            if "focus_areas" in role_guidelines:
                prompt += "\nFocus Areas:\n"
                for focus in role_guidelines["focus_areas"]:
                    prompt += f"• {focus}\n"

        # Add mandatory question types
        mandatory_reqs = self.mandatory_questions.get(role, {}).get("required", [])
        if mandatory_reqs:
            prompt += """
## MANDATORY QUESTION TYPES
"""
            for req in mandatory_reqs:
                prompt += f"- {req['type']}: {req['description']}\n"
            
            prompt += "\nNOTE: You MUST include all mandatory question types listed above. For each mandatory type, create at least one question with the exact question_type value."

        # Add red flag questions
        if red_flag_questions:
            prompt += """
## RED FLAGS TO ADDRESS
The following concerns should be investigated during the interview:

"""
            for idx, flag in enumerate(red_flag_questions):
                prompt += f"{idx + 1}. [{flag['type'].upper()} - {flag['severity']}] \"{flag['question']}\"\n"
            
            prompt += """
RED FLAG QUESTION GUIDELINES:
- Each red flag concern must be addressed exactly once in your questions
- You may either:
  a) Use the exact question text provided above, OR
  b) Create your own question that addresses the same concern but fits the interviewer's tone
- When addressing a red flag, set the "red_flag_category" field to the appropriate type
- Distribute red flag questions throughout the interview - don't group them all together
- Phrase questions in a neutral, non-accusatory manner that gives the candidate an opportunity to explain
"""

        # Add green flag questions
        if green_flag_questions:
            prompt += """
## STRENGTHS TO EXPLORE
The following positive indicators can be explored during the interview:

"""
            for idx, flag in enumerate(green_flag_questions):
                prompt += f"{idx + 1}. [{flag['type'].upper()} - {flag['relevance']}] \"{flag['question']}\"\n"
            
            prompt += """
STRENGTH EXPLORATION GUIDELINES:
- Prioritize HIGH relevance strengths first, then MEDIUM, then LOW
- Include at least one strength-based question if any HIGH relevance strengths exist
- Frame questions to allow the candidate to demonstrate depth in their strongest areas
- Connect strength exploration directly to job requirements when possible
- Use strength questions strategically between more challenging questions
"""

        # Add technical question design principles
        prompt += """
## TECHNICAL QUESTION DESIGN PRINCIPLES
- Create scenario-based problems grounded in real-world applications
- Technical questions should require explanation of approach, not code recitation
- Set appropriate difficulty based on:
  * FRESHER: Basic understanding of core concepts
  * JUNIOR: Application of knowledge to straightforward problems
  * MID: Complex problems requiring thoughtful approaches
  * SENIOR: Architectural decisions and tradeoff analysis
- For coding questions:
  * Specify clear inputs, outputs, and constraints
  * Require explanation of solution approach rather than exact implementation
  * Include consideration of edge cases and performance
- For database questions:
  * Specify database type (SQL/NoSQL) based on candidate's experience
  * Include sample data structures to provide context
  * Focus on query design logic rather than perfect syntax
"""

        # Add evaluation criteria
        prompt += """
## EVALUATION CRITERIA GUIDELINES
- Excellent responses should demonstrate:
  * Deep understanding of underlying principles
  * Consideration of multiple approaches/tradeoffs
  * Clear articulation of reasoning
  * Connection to broader context/impact
- Acceptable responses should demonstrate:
  * Correct application of core concepts
  * Viable approach to solving the problem
  * Awareness of basic constraints/requirements
- Poor responses would include:
  * Fundamental misconceptions about key concepts
  * Inability to formulate a coherent approach
  * Serious logical errors in reasoning
  * Complete failure to address the question asked
"""

        # Add interview flow strategy
        prompt += """
## INTERVIEW FLOW STRATEGY
- Begin with a straightforward question related to candidate's experience
- Distribute challenging questions (including red flags) throughout the interview
- Place strength-based questions strategically after challenging ones
- End with a forward-looking question related to the role
- Ensure question difficulty aligns with experience level
- Balance technical and behavioral/situational questions according to role requirements
"""

        # Add JSON output format
        prompt += """
## OUTPUT FORMAT REQUIREMENTS
- Return ONLY valid JSON with no explanations or text outside the JSON structure
- Structure must exactly match the example below
- Every field must be properly populated for every question
- String values must use double quotes and be properly escaped
- Arrays and objects must not have trailing commas
- The "red_flag_category" field must be set correctly:
  * Use the specific category when addressing a red flag concern
  * Use null (not the string "null") when the question does not address a red flag
- Question types must be one of the allowed values
- Experience level must match the candidate's level

JSON STRUCTURE:
{{
  "questions": [{{
    "question_text": "Clear, concise interview question (under 60 words)",
    "question_type": "coding_scenario | database_query | fundamental | project_experience | practical_scenario",
    "red_flag_category": "employment_concern | achievement_concern | skill_concern | null",
    "experience_level": "FRESHER | JUNIOR | MID | SENIOR",
    "skill_assessed": "specific skill being evaluated",
    "context": "direct reference to candidate's experience or job requirement",
    "follow_ups": ["1-3 logical follow-up questions"],
    "estimated_time": "2-5",
    "evaluation_criteria": {{
      "excellent": "specific criteria for top response",
      "acceptable": "specific criteria for adequate response",
      "poor": "specific criteria for inadequate response"
    }}
  }}]
}}
"""

        # Add critical reminders
        prompt += f"""
CRITICAL REMINDERS:
1. Generate exactly {question_count} questions total
2. Include all mandatory question types for {role}
3. Address all red flags exactly once each
4. Include at least one HIGH relevance strength question if available
5. Balance question types according to role requirements
6. Ensure JSON is perfectly valid with no syntax errors
7. Maintain {interviewer_info.get('role', role)} interviewer persona throughout
8. Match question difficulty to {experience_level} experience level

TASK: Create {question_count} interview questions following all guidelines above.
"""
        
        return prompt

class ResumeAnalyzer:
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.system_prompt = """You are an advanced AI interviewer that adapts its approach based on:
1. Candidate Experience Level Analysis
2. Role-Specific Personality
3. Technical Depth Requirements
4. Respond with a JSON object

Your primary directives:
- Analyze experience excluding internships
- Adjust question complexity to experience level
- Maintain consistent role personality
- Focus on practical over theoretical knowledge
- Reference specific projects from resume"""  # Include full original system prompt
        
        self.universal_analysis_prompt = """Analyze this resume for any professional role, focusing on core qualifications and potential risks:
RESUME: {resume_text}

Generate JSON output in this flattened structure:

{{
  "candidate_overview": {{
    "total_years_experience": number,
    "current_role": "Current Title",
    "current_company": "Current Company",
    "current_tenure": "X months/years"
  }},
  
  "career_progression": ["earliest role level", "next role level", "current role level"],
  
  "employment_history": [
    {{
      "company": "Most Recent Company",
      "role": "Current/Most Recent Title",
      "period": "MM/YYYY - MM/YYYY",
      "duration": "X years Y months",
      "achievements": ["Quantified impact 1", "Quantified impact 2"]
    }},
    {{
      "company": "Previous Company",
      "role": "Previous Title",
      "period": "MM/YYYY - MM/YYYY",
      "duration": "X years Y months",
      "achievements": ["Quantified impact 3"]
    }}
  ],
  
  "notable_achievements": [
    {{
      "company": "Company Name",
      "role": "Significant Position",
      "achievement": "Top measurable impact with context"
    }}
  ],
  
  "key_projects": [
    {{
      "name": "Project Name",
      "duration": "X months",
      "scope": "team size/org size impacted",
      "contribution": "specific role/responsibility",
      "impact": "measurable outcome"
    }}
  ],
  
  "validated_skills": {{
    "technical": ["verified tool/technology 1", "verified tool/technology 2"],
    "functional": ["domain-specific skill 1", "domain-specific skill 2"],
    "leadership": ["management/strategy skill 1", "management/strategy skill 2"]
  }},
  
  "unverified_skills": ["skill without evidence 1", "skill without evidence 2"],

  "green_flags": {{
    "experience_strengths": [
      {{
        "type": "CAREER_PROGRESSION | TENURE | PROMOTIONS",
        "details": "Specific strength details",
        "relevance": "HIGH | MEDIUM | LOW",
        "interview_question": "Question to explore this strength"
      }}
    ],
    "skill_mastery": [
      {{
        "type": "TECHNICAL_DEPTH | DOMAIN_EXPERTISE",
        "details": "Specific skill details",
        "relevance": "HIGH | MEDIUM | LOW",
        "interview_question": "Question to validate expertise"
      }}
    ],
    "achievement_highlights": [
      {{
        "type": "IMPACT | INNOVATION | SCALE",
        "details": "Specific achievement details",
        "relevance": "HIGH | MEDIUM | LOW",
        "interview_question": "Question to probe achievement"
      }}
    ],
    "cultural_fit": [
      {{
        "type": "VALUES_ALIGNMENT | COLLABORATION | LEADERSHIP",
        "details": "Specific cultural fit details",
        "relevance": "HIGH | MEDIUM | LOW",
        "interview_question": "Question to assess cultural alignment"
      }}
    ],
    "certifications": [
      {{
        "type": "TECHNICAL | DOMAIN | LEADERSHIP",
        "details": "Certification details",
        "relevance": "HIGH | MEDIUM | LOW",
        "interview_question": "Question to validate certification impact"
      }}
    ]
  }},
  
  "red_flags": {{
    "employment_concerns": [
      {{
        "type": "JOB_HOPPING | OVERLAP | GAP | DOWNGRADE",
        "details": "Company A (6 months), Company B (8 months)",
        "severity": "LOW | MEDIUM | HIGH",
        "interview_question": "What led to your transition between Company A and Company B in such a short timeframe?"
      }}
    ],
    "achievement_concerns": [
      {{
        "type": "VAGUE_CLAIMS | SCALE_MISMATCH | DATE_INCONSISTENCY",
        "example": "Ambiguous or unsupported claims regarding project outcomes.",
        "severity": "LOW | MEDIUM | HIGH",
        "interview_question": "In your resume, the 'CMS Websites Optimizer' project is noted to have improved site performance. Could you walk us through how you used to measure these improvements? For example, what were the baseline figures, which optimization techniques did you implement, and what quantifiable results (e.g., reductions in page load time or conversion rate improvements) were achieved?"
      }}
    ],
    "skill_concerns": [
      {{
        "type": "OVERCLAIMED",
        "skill": "Advanced Machine Learning",
        "evidence": "Only mentioned completion of a course without practical application.",
        "severity": "MEDIUM",
        "interview_question": "For your project 'Project Beta', where you noted applying advanced machine learning techniques, could you describe a particular instance detailing the challenge, the specific methods you used, and the measurable results you achieved?"
      }}
    ]
  }}
}}

Analysis Rules:
1. Experience Analysis:
   - Calculate only full-time professional experience
   - Part-time roles: Count at 50% of full-time equivalent
   - Internships: Include only if post-graduate or 6+ months duration
   - Identify clear progression through role complexity (junior → mid → senior → lead → management)
   - Extract achievements with quantifiable metrics using this format: "Achieved [X%/amount] [improvement/increase/decrease] in [specific metric] by [specific action]"
   - Standardize tenure calculation (e.g., "2 years 3 months" not "27 months")
   - When dates are month/year only, assume employment began on the 1st of the month

2. Project Evaluation:
   - Categorize scope: Individual (1 person) < Team (2-10) < Cross-functional (11-50) < Enterprise (50+)
   - Verify claimed impact against role level and project duration
   - For each project, identify at least one specific contribution and one measurable outcome
   - Flag projects with impact claims disproportionate to role seniority (e.g., entry-level claiming enterprise-wide impact)
   - Require time-bound project descriptions with clear start/end dates or durations

3. Skill Validation:
   - Technical: Must have supporting project/role evidence showing practical application
   - Functional: Match against industry standard requirements; require evidence of practical application
   - Leadership: Require team size/budget/scope mentions to validate management experience
   - Only include skills in "validated_skills" when there is clear evidence of application
   - Categorize skill levels based on evidence: Beginner (mentioned/coursework), Intermediate (1-2 applications), Advanced (3+ applications/leadership)

4. Red Flag Detection:
   - Job Hopping: Flag if a candidate has 3+ distinct roles with durations under 18 months each, excluding cases where the roles represent internal progression within a single company or legitimate transitions (e.g., internships converting to full-time positions)
   - Overlaps: Flag any instance where roles overlap for more than 1 month concurrently
   - Gaps: Flag any unexplained employment gap lasting more than 6 months
   - Skill Mismatch: Flag claims of expert-level proficiency that lack supporting evidence from project work or role responsibilities
   - Downgrade: Flag any move to a less senior role without clear explanation (e.g., Director → Manager)
   - Objective criteria for "vague claims": No specific metrics, no clear scope definition, no description of personal contribution

5. Green Flag Detection:
   - Career Progression: Flag consistent upward mobility with increasing responsibility (clear title progression)
   - Technical Depth: Validate expertise with multiple projects (3+) using same technology stack
   - High Impact: Identify achievements with measurable business impact (must include specific metrics)
   - Cultural Indicators: Note volunteer work, mentoring, or community contributions with specific details
   - Certifications: Highlight role-relevant certifications with practical application evidence
   - Include ONLY strengths with concrete evidence (not aspirational or general statements)

6. Question Design:
   - Focus on clarification rather than making accusations
   - Use evidence-based, context-specific follow-up questions
   - Maintain a neutral, professional tone in all queries
   - Include explicit references to resume details (e.g., project names, dates, role transitions) for clarity
   - Questions should be open-ended and provide opportunity for candidate explanation
   - Examples:
     - "In your role at [Company] from [MM/YYYY - MM/YYYY], can you explain the factors that led to your transition from [Role A] to [Role B]?"
     - "For the project '[Project Name]' mentioned in your resume, could you elaborate on how you achieved [Claimed Outcome] including specific metrics or results?"
     - "During your tenure at [Company], what influenced your decision to [Controversial Move] and how did it impact your responsibilities?"

7. Consistency Check:
   - IMPORTANT: Ensure green flags and red flags do not contradict each other. The same attribute cannot be both a strength and a concern.
   - For career trajectory: If "career progression" is listed as a green flag, there should not be "downgrade" as a red flag.
   - For skills: If a skill is listed in "validated_skills", it should not appear in "skill_concerns".
   - For achievements: If listed in "notable_achievements", they should not appear in "achievement_concerns".
   - When in doubt, categorize an element as either a green flag OR a red flag, not both.
   - Review all outputs for logical consistency before finalizing

8. Edge Case Handling:
   - Career Transitions: Consider intentional industry/function changes when evaluating progression
   - Freelance/Consulting: Count consistent client work as stable employment (with evidence of continuing clients)
   - Education Gaps: Do not penalize gaps explained by full-time education
   - Recent Graduates: Adjust expectations for early-career candidates (less than 3 years experience)
   - Founder/Entrepreneur: Evaluate based on company milestones rather than traditional progression
   - Industry-Specific: Adjust expectations for industries with known high turnover (e.g., startups, agencies)
   - Career Breaks: Consider parental leave, health issues, or care responsibilities with appropriate context

9. Missing Information Handling:
   - For missing dates: Note as a data quality issue rather than a red flag
   - For ambiguous titles: Base analysis on responsibilities described rather than title alone
   - For missing metrics: Flag as an achievement concern if senior-level role (5+ years experience)
   - For incomplete employment records: Note limitations in analysis
   - Required fields: If any of these are missing, explicitly note limitation: current role, tenure, and at least one achievement

10. Context-Aware Analysis:
    - Consider industry norms when evaluating tenure (e.g., 2 years in tech startups may be normal)
    - Adjust expectations based on career stage (early/mid/senior/executive)
    - For highly specialized roles, focus on depth rather than breadth of experience
    - Consider geographic context for employment patterns and role expectations
    - Compare experience to typical industry benchmarks rather than absolute standards"""  # Include full original analysis prompt

    def parse_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        return extract_text(file_path)

    def analyze_resume(self, resume_text: str) -> Dict:
        """Analyze resume using OpenAI and return analysis JSON"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self.universal_analysis_prompt.format(resume_text=resume_text)}
                ],
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content
            print("Raw API Response:", raw_content)  # Log the raw response for debugging
            return json.loads(raw_content)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Problematic content: {raw_content}")
            raise Exception(f"JSON parsing failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Analysis failed: {str(e)}")

    def generate_questions(self, analysis: Dict, job_description: str, 
                          interviewer_role: str, difficulty: str = 'medium') -> Dict:
        """Generate interview questions based on analysis and job description"""
        question_count = {
            'hard': 15,
            'medium': 10,
            'easy': 5
        }.get(difficulty, 10)

        prompt = InterviewQuestionGenerator().create_question_prompt(analysis, job_description, interviewer_role, question_count)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            raise Exception(f"Question generation failed: {str(e)}")

