import os

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import json
from typing import List, Optional
import asyncio
from ai_service import ai_service
from dotenv import load_dotenv

load_dotenv()

QUIZ_DATA_FILE = os.getenv("QUIZ_DATA_FILE", "quiz_example.json")
app = FastAPI(title="Quiz Application", description="Georgian Programming Quiz")

# Pydantic models
class Answer(BaseModel):
    answer: str

class QuizResult(BaseModel):
    total_questions: int
    correct_answers: int
    percentage: float
    detailed_results: List[dict]

class DetailedResult(BaseModel):
    id: int
    question: str
    options: List[str]
    user_answer: Optional[str]
    correct_answer: str
    is_correct: bool
    ai_explanation: Optional[str] = None

# Load quiz data
def load_quiz_data():
    try:
        with open(f"{QUIZ_DATA_FILE}", "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Quiz data not found")

# Save quiz data
def save_quiz_data(data):
    with open(f"{QUIZ_DATA_FILE}", "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/api/quiz")
async def get_quiz():
    """Get all quiz questions without correct answers"""
    quiz_data = load_quiz_data()
    # Remove correct answers from response for security
    clean_quiz = []
    for question in quiz_data:
        clean_question = {
            "id": question["id"],
            "question": question["question"],
            "options": question["options"]
        }
        clean_quiz.append(clean_question)
    return clean_quiz

@app.get("/api/quiz/{question_id}")
async def get_question(question_id: int):
    """Get specific question by ID"""
    quiz_data = load_quiz_data()
    question = next((q for q in quiz_data if q["id"] == question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return {
        "id": question["id"],
        "question": question["question"],
        "options": question["options"]
    }

@app.get("/api/quiz/{question_id}/correct-answer")
async def get_correct_answer(question_id: int):
    """Get correct answer for a specific question (for quick answer feature)"""
    quiz_data = load_quiz_data()
    question = next((q for q in quiz_data if q["id"] == question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    correct_answer = question.get("correct", [""])[0]
    correct_text = ""

    if correct_answer and question.get("options"):
        try:
            # Convert A, B, C, D to 0, 1, 2, 3
            option_index = ord(correct_answer) - ord("A")
            if 0 <= option_index < len(question["options"]):
                correct_text = question["options"][option_index]
        except (IndexError, ValueError):
            pass

    return {
        "id": question_id,
        "correct_answer": correct_answer,
        "correct_text": correct_text
    }

@app.post("/api/quiz/{question_id}/answer")
async def submit_answer(question_id: int, answer: Answer):
    """Submit answer for a specific question"""
    quiz_data = load_quiz_data()
    question = next((q for q in quiz_data if q["id"] == question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Save user answer (create field if it doesn't exist)
    if "user_answer" not in question:
        question["user_answer"] = []
    question["user_answer"] = [answer.answer]
    save_quiz_data(quiz_data)

    return {"message": "Answer submitted successfully", "answer": answer.answer}

@app.get("/api/results")
async def get_results():
    """Get quiz results with correct answers and AI explanations"""
    quiz_data = load_quiz_data()

    total_questions = len(quiz_data)
    correct_count = 0
    detailed_results = []

    # Collect all incorrect answers for batch AI processing
    incorrect_questions = []

    for question in quiz_data:
        question_id = question["id"]
        user_answer = question.get("user_answer", [])
        correct_answer_list = question.get("correct", [])
        correct_answer = correct_answer_list[0] if correct_answer_list else ""

        is_correct = len(user_answer) > 0 and user_answer[0] == correct_answer
        if is_correct:
            correct_count += 1
        else:
            # Add to incorrect questions for AI explanation
            # Only if user provided an answer AND it's wrong (not just unanswered)
            if user_answer and len(user_answer) > 0:
                incorrect_questions.append({
                    "question_data": question,
                    "user_answer": user_answer[0],
                    "correct_answer": correct_answer
                })

        detailed_results.append({
            "id": question_id,
            "question": question["question"],
            "options": question["options"],
            "user_answer": user_answer[0] if user_answer else None,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "ai_explanation": None  # Will be filled later
        })

    # Generate AI explanations for incorrect answers
    if incorrect_questions:
        print(f"[MAIN] Starting AI explanation generation for {len(incorrect_questions)} questions")
        explanations = await generate_ai_explanations(incorrect_questions)
        print(f"[MAIN] AI explanation generation completed")

        # Update detailed_results with AI explanations
        for i, result in enumerate(detailed_results):
            # Only add AI explanation if user gave a wrong answer (not if no answer given)
            if not result["is_correct"] and result["user_answer"] is not None:
                # Find matching explanation using the same key format as ai_service
                explanation_key = f"{result['id']}_{result['user_answer']}_{result['correct_answer']}"
                result["ai_explanation"] = explanations.get(explanation_key)

    percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0

    return QuizResult(
        total_questions=total_questions,
        correct_answers=correct_count,
        percentage=round(percentage, 2),
        detailed_results=detailed_results
    )

async def generate_ai_explanations(incorrect_questions):
    """Generate AI explanations for incorrect answers using batch processing"""
    print(f"[GENERATE_AI] Function called with {len(incorrect_questions)} questions")

    if not incorrect_questions:
        print(f"[GENERATE_AI] No questions provided, returning empty dict")
        return {}

    # Use batch processing to get all explanations in one API call
    print(f"[GENERATE_AI] Calling ai_service.get_batch_explanations()")
    explanations = await ai_service.get_batch_explanations(incorrect_questions)
    print(f"[GENERATE_AI] Received {len(explanations)} explanations")
    return explanations

@app.post("/api/reset")
async def reset_quiz():
    """Reset all user answers"""
    quiz_data = load_quiz_data()
    for question in quiz_data:
        question["user_answer"] = []
        # Don't reset correct answers - they should stay
    save_quiz_data(quiz_data)
    return {"message": "Quiz reset successfully"}

@app.get("/api/ai-stats")
async def get_ai_statistics():
    """Get AI API usage statistics"""
    stats = ai_service.get_statistics()
    return {
        "ai_statistics": stats,
        "message": f"Total API requests: {stats['total_requests']}, Questions processed: {stats['total_questions_processed']}"
    }

@app.post("/api/ai-stats/reset")
async def reset_ai_statistics():
    """Reset AI API usage statistics"""
    ai_service.reset_statistics()
    return {"message": "AI statistics reset successfully"}

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
