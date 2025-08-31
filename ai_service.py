import asyncio
import aiohttp
import json
import logging
import uuid
from datetime import datetime
from typing import Optional
from config import GOOGLE_API_KEY, ENABLE_AI_EXPLANATIONS, GEMINI_API_URL, GEMINI_MODEL

# Setup logging for API requests
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

class AIExplanationService:
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.enabled = ENABLE_AI_EXPLANATIONS and bool(self.api_key)
        self.request_count = 0
        self.total_questions_processed = 0
    
    async def get_batch_explanations(self, incorrect_questions: list) -> dict:
        """Generate AI explanations for multiple incorrect answers in one request"""
        if not self.enabled or not incorrect_questions:
            logger.info(f"AI disabled or no questions. Questions count: {len(incorrect_questions)}")
            return {self._get_question_key(q): self._get_default_explanation(q["user_answer"], q["correct_answer"]) 
                    for q in incorrect_questions}
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Log request details
        self.request_count += 1
        self.total_questions_processed += len(incorrect_questions)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"🚀 GEMINI API REQUEST #{self.request_count} [ID: {request_id}]")
        logger.info(f"📅 Time: {timestamp}")
        logger.info(f"🤖 Model: {GEMINI_MODEL}")
        logger.info(f"❓ Questions in this batch: {len(incorrect_questions)}")
        logger.info(f"📊 Total questions processed so far: {self.total_questions_processed}")
        logger.info(f"🔧 API Key configured: {'Yes' if self.api_key else 'No'}")
        
        try:
            prompt = self._create_batch_prompt(incorrect_questions)
            
            # Log prompt size
            prompt_size = len(prompt)
            logger.info(f"📝 Prompt size: {prompt_size} characters")
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Content-Type': 'application/json',
                }
                
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }]
                }
                
                url = f"{GEMINI_API_URL}?key={self.api_key}"
                
                logger.info(f"🌐 Sending request to Gemini API... [ID: {request_id}]")
                
                async with session.post(url, headers=headers, json=payload) as response:
                    response_time = datetime.now().strftime("%H:%M:%S")
                    
                    if response.status == 200:
                        data = await response.json()
                        if data.get('candidates') and len(data['candidates']) > 0:
                            content = data['candidates'][0].get('content', {})
                            if content.get('parts') and len(content['parts']) > 0:
                                ai_response = content['parts'][0].get('text', '').strip()
                                response_size = len(ai_response)
                                
                                logger.info(f"✅ SUCCESS at {response_time} [ID: {request_id}]")
                                logger.info(f"📄 Response size: {response_size} characters")
                                logger.info(f"💰 Cost estimate: ~${self._estimate_cost(prompt_size, response_size):.4f}")
                                logger.info(f"🏁 REQUEST #{self.request_count} COMPLETED [ID: {request_id}]")
                                
                                return self._parse_batch_response(ai_response, incorrect_questions)
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ API ERROR at {response_time} [ID: {request_id}]")
                        logger.error(f"🔴 Status: {response.status}")
                        logger.error(f"📋 Error: {error_text}")
                        
                        return {self._get_question_key(q): self._get_default_explanation(q["user_answer"], q["correct_answer"]) 
                                for q in incorrect_questions}
                        
        except Exception as e:
            logger.error(f"💥 EXCEPTION: {str(e)}")
            return {self._get_question_key(q): self._get_default_explanation(q["user_answer"], q["correct_answer"]) 
                    for q in incorrect_questions}
    
    def _get_question_key(self, question_info: dict) -> str:
        """Generate unique key for question"""
        return f"{question_info['question_data']['id']}_{question_info['user_answer']}_{question_info['correct_answer']}"
    
    def _get_default_explanation(self, user_answer: str, correct_answer: str) -> str:
        """Generate a simple default explanation when AI is unavailable"""
        return f"""**თქვენი პასუხი:** {user_answer} ❌  
**სწორი პასუხი:** {correct_answer} ✅

💡 **რჩევა:** გადახედეთ სასწავლო მასალას ამ თემაზე."""
    
    def _create_batch_prompt(self, incorrect_questions: list) -> str:
        """Create batch prompt for multiple questions"""
        option_labels = ['A', 'B', 'C', 'D']
        
        questions_text = ""
        for i, q_info in enumerate(incorrect_questions, 1):
            question = q_info["question_data"]
            user_answer = q_info["user_answer"]
            correct_answer = q_info["correct_answer"]
            
            options_text = ""
            for j, option in enumerate(question["options"]):
                options_text += f"{option_labels[j]}. {option}\n"
            
            questions_text += f"""
---
**კითხვა {i} (ID: {question['id']}):**
{question['question']}

**ვარიანტები:**
{options_text}
**მოსწავლის პასუხი:** {user_answer}
**სწორი პასუხი:** {correct_answer}
"""
        
        prompt = f"""თქვენ ხართ IT განათლების ექსპერტი და პროგრამირების ინსტრუქტორი. ქვემოთ მოცემული ყველა კითხვა დაკავშირებულია ინფორმაციულ ტექნოლოგიებთან, პროგრამირებასთან, კომპიუტერულ მეცნიერებასთან და ქსელურ ტექნოლოგიებთან.

გთხოვთ ახსნათ ქართულ ენაზე რატომ არის არასწორი თითოეული მოცემული პასუხი, გამოიყენეთ IT ტერმინოლოგია და ტექნიკური ცოდნა.

{questions_text}

**მოთხოვნები:**
1. თითოეული კითხვისთვის მოკლე, ლაკონური ახსნა
2. მოიცავდეს რატომ არის სწორი სწორი პასუხი (IT ტექნიკური თვალსაზრისით)
3. რატომ არის არასწორი მოსწავლის პასუხი (ტექნიკური განმარტებით)
4. გამოიყენეთ markdown ფორმატირება
5. მაქსიმუმ 2-3 წინადადება თითო კითხვაზე
6. გამოიყენეთ ქართული IT ტერმინოლოგია და ტექნიკური ენა

**ფორმატი:**
```
### კითხვა 1 (ID: X)
**სწორი პასუხი (Y):** [IT ტექნიკური ახსნა]
**რატომაა არასწორი (Z):** [ტექნიკური განმარტება]

### კითხვა 2 (ID: X)
...
```"""
        
        return prompt
    
    def _parse_batch_response(self, ai_response: str, incorrect_questions: list) -> dict:
        """Parse AI response and map to question keys"""
        explanations = {}
        
        # Split response by question sections
        sections = ai_response.split("### კითხვა")
        
        for i, section in enumerate(sections[1:], 1):  # Skip first empty section
            try:
                # Extract question ID from section
                id_match = section.split("(ID: ")[1].split(")")[0] if "(ID: " in section else None
                
                if id_match:
                    question_id = int(id_match)
                    # Find matching question
                    for q_info in incorrect_questions:
                        if q_info["question_data"]["id"] == question_id:
                            key = self._get_question_key(q_info)
                            # Clean up the explanation text
                            explanation = f"### კითხვა {i} (ID: {question_id})\n" + section.split(f"(ID: {question_id})")[1].strip()
                            explanations[key] = explanation
                            break
            except Exception as e:
                print(f"Error parsing question section {i}: {e}")
                continue
        
        # Fill in default explanations for any missing questions
        for q_info in incorrect_questions:
            key = self._get_question_key(q_info)
            if key not in explanations:
                explanations[key] = self._get_default_explanation(q_info["user_answer"], q_info["correct_answer"])
        
        return explanations
    
    def _estimate_cost(self, prompt_size: int, response_size: int) -> float:
        """Estimate API cost based on character count (approximate)"""
        # Gemini 2.0 Flash pricing (approximate): $0.000075 per 1K characters for input, $0.0003 per 1K characters for output
        input_cost = (prompt_size / 1000) * 0.000075
        output_cost = (response_size / 1000) * 0.0003
        return input_cost + output_cost
    
    def get_statistics(self) -> dict:
        """Get API usage statistics"""
        return {
            "total_requests": self.request_count,
            "total_questions_processed": self.total_questions_processed,
            "enabled": self.enabled,
            "api_key_configured": bool(self.api_key)
        }
    
    def reset_statistics(self):
        """Reset API usage statistics"""
        old_count = self.request_count
        old_questions = self.total_questions_processed
        self.request_count = 0
        self.total_questions_processed = 0
        logger.info(f"🔄 STATISTICS RESET: {old_count} requests, {old_questions} questions")
    
    def _create_prompt(self, question: str, options: list, user_answer: str, correct_answer: str) -> str:
        """Create a prompt for AI explanation generation"""
        option_labels = ['A', 'B', 'C', 'D']
        options_text = ""
        for i, option in enumerate(options):
            options_text += f"{option_labels[i]}. {option}\n"
        
        prompt = f"""თქვენ ხართ განათლების ექსპერტი. გთხოვთ ახსნათ ქართულ ენაზე რატომ არის არასწორი მოცემული პასუხი და რატომ არის სწორი სწორი პასუხი.

კითხვა: {question}

ვარიანტები:
{options_text}

მოსწავლის პასუხი: {user_answer}
სწორი პასუხი: {correct_answer}

გთხოვთ მიაწოდოთ:
1. რატომ არის სწორი "{correct_answer}" პასუხი
2. რატომ არის არასწორი "{user_answer}" პასუხი  
3. მოკლე ახსნა სხვა ვარიანტების შესახებ

ახსნა უნდა იყოს მკაფიო, მარტივი და განმანათლებელი. გამოიყენეთ ქართული ტექნიკური ტერმინოლოგია."""

        return prompt

# Global instance
ai_service = AIExplanationService() 