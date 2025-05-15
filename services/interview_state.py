import time
import os
import asyncio
import traceback
import json
import websockets
import base64
from services.final_prompt import create_final_prompt
from services.gemini_script import InterviewQuestionGenerator, ResumeAnalyzer
from services.prompts import agent_prompt
from config.config import TEMP_DIR, client, CONFIG, MODEL


class InterviewState:
    def __init__(self):
        self.resume_path = None
        self.jd_path = None
        self.final_prompt = None
        self.candidate_name = None
        self.analyzer = ResumeAnalyzer(os.environ.get("OPENAI_API_KEY"))
        self.qa_generator = InterviewQuestionGenerator()

    async def prepare_interview(self, candidate_name):
        """Prepare the interview by analyzing resume and JD"""
        try:
            self.candidate_name = candidate_name
            # Parse and analyze documents
            resume_text = self.analyzer.parse_pdf(str(self.resume_path))
            jd_text = self.analyzer.parse_pdf(str(self.jd_path))
            analysis = self.analyzer.analyze_resume(resume_text)
            
            questions = self.analyzer.generate_questions(
                analysis=analysis,
                job_description=jd_text,
                interviewer_role="SD1",
                difficulty="hard"
            )

            # Get role specific information
            role = "SD1"
            role_specific_guidelines = self.qa_generator.role_specific_guidelines[role]
            role_personality = self.qa_generator.role_personalities[role]
            question_focus = self.qa_generator.question_focus[role]
            interviewer_details = self.qa_generator.interviewer_details[role]
            mandatory_questions = self.qa_generator.mandatory_questions[role]
            role_perspective = self.qa_generator.define_role_perspective(role)

            # Create final prompt with candidate name
            self.final_prompt = create_final_prompt(
                agent_prompt,
                role,
                15,  # minutes
                self.candidate_name,  # Using provided name
                "Interview for Software Development Engineer 1 position",
                role_specific_guidelines,
                role_personality,
                question_focus,
                interviewer_details,
                mandatory_questions,
                questions,
                role_perspective
            )
            #write final prompt to file
            with open(TEMP_DIR / "final_prompt.txt", "w") as f:
                f.write(self.final_prompt)
            return True
        
            
        
        except Exception as e:
            print(f"Error preparing interview: {e}")
            traceback.print_exc()
            return False
        
# Global interview state
interview_state = InterviewState()


