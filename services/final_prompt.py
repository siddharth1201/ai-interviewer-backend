import json

import json

def create_final_prompt(agent_prompt, role, mins, candidate_name, objective, role_specific_guidelines, role_personality, question_focus, interviewer_details, mandatory_questions, questions, role_perspective):
    """
    Creates the final agent prompt by replacing placeholders with actual values.

    Args:
        agent_prompt (str): The base agent prompt with placeholders.
        role (str): The role for the interview (e.g., "SD1").
        mins (int): The interview duration in minutes.
        candidate_name (str): The name of the candidate.
        objective (str): The interview objective.
        role_specific_guidelines (dict): Dictionary containing role-specific guidelines.
        role_personality (str): A string describing the role's personality.
        question_focus (list): A list of strings representing question focus areas.
        interviewer_details (dict): Dictionary containing interviewer details (name, role, etc.).
        mandatory_questions (dict): Dictionary containing mandatory questions.
        questions (list): A list of role specific questions
        role_perspective (str): A string describing the role's perspective.

    Returns:
        str: The final agent prompt with all placeholders replaced.
    """

    interviewer_name = interviewer_details['name']

    # Build the mandatory questions string based on mandatory_questions
    mandatory_questions_list = []
    if mandatory_questions and "required" in mandatory_questions:
        for question in mandatory_questions["required"]:
            if question['type'] == 'coding_scenario':
                mandatory_questions_list.append("Describe a coding scenario and ask the candidate to explain their approach.")
            elif question['type'] == 'database_query':
                mandatory_questions_list.append("Present a database query design problem and ask the candidate to design a solution.")
            else:
                mandatory_questions_list.append(f"Ask a question related to {question['description']}")  # Handle other question types if necessary
    mandatory_questions_string = "\n".join(mandatory_questions_list)


    # Build the questions string based on questions
    role_specific_questions_string = "\n".join(questions)

    # Example behavioral questions (replace with your actual behavioral questions if available)
    behavioral_questions = None # Or provide a list of behavioral questions here, e.g. ["Tell me about a time you failed...", "Describe a time you worked in a team..."]
    behavioral_questions_string = "\n".join(behavioral_questions) if behavioral_questions else None

    # Example context, follow_ups, and evaluation criteria
    context = "Evaluate the candidate's approach to problem-solving, code clarity, and efficiency."
    follow_ups = ["Why did you choose this approach?", "What are the trade-offs?", "Can you optimize your solution?"]
    evaluation_criteria = {
        "excellent": "Demonstrates a clear understanding of the problem and provides an efficient solution.",
        "acceptable": "Understands the problem and provides a functional solution.",
        "poor": "Struggles to understand the problem or provides an inadequate solution."
    }

    # Convert to JSON strings where needed
    evaluation_criteria_json = json.dumps(evaluation_criteria)

    # Perform variable substitution
    final_prompt = agent_prompt.replace("{{role}}", role)
    final_prompt = final_prompt.replace("{{mins}}", str(mins))
    final_prompt = final_prompt.replace("{{name}}", candidate_name)
    final_prompt = final_prompt.replace("{{objective}}", objective)
    final_prompt = final_prompt.replace("{{questionFocus}}", ", ".join(question_focus))
    final_prompt = final_prompt.replace("{{description}}", interviewer_details['description'])
    final_prompt = final_prompt.replace("{{interviewerName}}", interviewer_name)
    final_prompt = final_prompt.replace("{{interviewerPersonality}}", role_personality)
    final_prompt = final_prompt.replace("{{candidateName}}", candidate_name)
    final_prompt = final_prompt.replace("{{questions}}", str(questions))
    final_prompt = final_prompt.replace("{{context}}", context)
    final_prompt = final_prompt.replace("{{follow_ups}}", ", ".join(follow_ups))
    final_prompt = final_prompt.replace("{{evaluation_criteria.excellent}}", evaluation_criteria["excellent"])
    final_prompt = final_prompt.replace("{{evaluation_criteria.acceptable}}", evaluation_criteria["acceptable"])
    final_prompt = final_prompt.replace("{{evaluation_criteria.poor}}", evaluation_criteria["poor"])
    final_prompt = final_prompt.replace("{{behavioralQuestions}}", behavioral_questions_string if behavioral_questions_string else "null")

    return final_prompt
