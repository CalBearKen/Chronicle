from vllm import LLM, SamplingParams
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn

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
    model="meta-llama/Llama-2-7b-chat-hf",  # Using smaller 7B model
    tensor_parallel_size=1,
    gpu_memory_utilization=0.95,  # Increased to allow more memory for cache
    trust_remote_code=True,
    dtype="float16",
    max_model_len=2048,  # Reduced context length to fit in memory
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
    """Format messages into Llama chat format"""
    formatted = ""
    # Start with system message if present
    system_msg = next((msg for msg in messages if msg.role == "system"), None)
    if system_msg:
        formatted = f"<s>[INST] <<SYS>>\n{system_msg.content}\n<</SYS>>\n\n"
    
    # Add user/assistant messages
    for msg in messages:
        if msg.role == "user":
            formatted += f"{msg.content} [/INST]"
        elif msg.role == "assistant":
            formatted += f"{msg.content}</s><s>[INST]"
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