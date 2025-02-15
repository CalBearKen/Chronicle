from vllm import LLM, SamplingParams
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLaMA
llm = LLM(
    model="01-ai/Yi-2B-Chat",  # Using Yi 2B Chat model
    tensor_parallel_size=1,  # Adjust based on GPU count
    gpu_memory_utilization=0.85,  # Reduced slightly to be safer
    trust_remote_code=True,
    dtype="float16",  # Use half precision for memory efficiency
    max_model_len=8192,  # Reduced context length to save memory
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 500

class ChatCompletionResponse(BaseModel):
    choices: List[Dict[str, Any]]

def format_prompt(messages: List[ChatMessage]) -> str:
    """Format messages into Yi chat format"""
    formatted = ""
    for msg in messages:
        if msg.role == "system":
            formatted += f"<|im_start|>system\n{msg.content}<|im_end|>\n"
        elif msg.role == "user":
            formatted += f"<|im_start|>user\n{msg.content}<|im_end|>\n"
        elif msg.role == "assistant":
            formatted += f"<|im_start|>assistant\n{msg.content}<|im_end|>\n"
    return formatted

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completion(request: ChatCompletionRequest):
    try:
        # Format prompt
        prompt = format_prompt(request.messages)
        
        # Set sampling parameters
        sampling_params = SamplingParams(
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        # Generate response
        outputs = llm.generate(prompt, sampling_params)
        
        # Format response to match OpenAI API
        response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": outputs[0].outputs[0].text
                },
                "finish_reason": "stop",
                "index": 0
            }]
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 