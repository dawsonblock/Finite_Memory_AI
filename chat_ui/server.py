#!/usr/bin/env python3
"""
Flask Backend Server for Finite Memory AI Chat UI
Connects the web interface to the Finite Memory AI backend with DeepSeek API
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
import requests

# Add parent directory to path to import finite_memory_llm
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finite_memory_llm import CompleteFiniteMemoryLLM, APIChatBackend
from transformers import AutoTokenizer

app = Flask(__name__, static_folder='.')
CORS(app)

# Global LLM instance
llm = None
current_settings = {
    'policy': 'sliding',
    'max_tokens': 8192,  # Increased for longer conversations
    'model': 'gpt2'
}


# DeepSeek API configuration
DEEPSEEK_API_KEY = "sk-26271e770fe94be59854da9117bbff4b"
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1/chat/completions"


def call_deepseek_direct(messages, max_tokens=1000):
    """Call DeepSeek API directly with messages array"""
    try:
        print(f"Calling DeepSeek with {len(messages)} messages")
        
        # Get the user's question for thinking simulation
        user_question = messages[-1]['content'] if messages else ""
        
        response = requests.post(
            DEEPSEEK_API_BASE,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9,
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        result = data['choices'][0]['message']['content']
        
        # Check if response has reasoning (DeepSeek R1 model)
        if 'reasoning_content' in data['choices'][0]:
            reasoning = data['choices'][0]['reasoning_content']
            print(f"DeepSeek reasoning: {reasoning}")
            result = f"**Thinking:** {reasoning}\n\n{result}"
        else:
            # Simulate thinking process for regular responses
            thinking = generate_thinking(user_question, result)
            if thinking:
                result = f"**Thinking:** {thinking}\n\n{result}"
        
        print(f"DeepSeek response ({len(result)} chars): {result[:100]}...")
        return result
    except Exception as e:
        print(f"DeepSeek direct API error: {e}")
        import traceback
        traceback.print_exc()
        raise


def generate_thinking(question, response):
    """Generate a thinking process based on the question and response"""
    # Only generate thinking if response is substantial
    if len(response.strip()) < 50:
        return ""  # Don't add thinking for very short responses
    
    question_lower = question.lower()
    
    # Don't add generic thinking for continuation requests
    if any(word in question_lower for word in ['continue', 'more', 'go on', 'keep going']):
        return ""  # Let the actual response speak for itself
    
    if any(word in question_lower for word in ['explain', 'what is', 'how does', 'why']):
        return f"I need to explain '{question[:50]}...' in a clear and understandable way. I'll break down the concept and use analogies if helpful."
    elif any(word in question_lower for word in ['compare', 'difference', 'vs']):
        return f"This is a comparison question. I'll analyze both sides and highlight the key differences and similarities."
    elif any(word in question_lower for word in ['write', 'create', 'code', 'program']):
        return f"This is a coding/creation task. I'll structure the solution logically and include necessary details."
    elif len(response) > 500:
        return f"This is a complex question requiring a detailed response. I'll organize my answer with clear sections and examples."
    else:
        return f"Analyzing the question: '{question[:60]}...' and formulating a helpful response."


def call_deepseek_api(prompt, max_tokens=150):
    """Call DeepSeek API and return response"""
    try:
        # Parse the prompt to extract conversation context
        # The prompt contains the full conversation history
        lines = prompt.strip().split('\n')
        
        # Build messages array for chat format
        messages = []
        current_role = None
        current_content = []
        
        for line in lines:
            if line.startswith('User:') or line.startswith('USER:'):
                if current_role and current_content:
                    messages.append({
                        "role": current_role,
                        "content": ' '.join(current_content).strip()
                    })
                current_role = "user"
                current_content = [line.split(':', 1)[1].strip() if ':' in line else line]
            elif line.startswith('Assistant:') or line.startswith('ASSISTANT:'):
                if current_role and current_content:
                    messages.append({
                        "role": current_role,
                        "content": ' '.join(current_content).strip()
                    })
                current_role = "assistant"
                current_content = [line.split(':', 1)[1].strip() if ':' in line else line]
            elif line.strip():
                current_content.append(line.strip())
        
        # Add the last message
        if current_role and current_content:
            messages.append({
                "role": current_role,
                "content": ' '.join(current_content).strip()
            })
        
        # If no structured messages found, treat entire prompt as user message
        if not messages:
            messages = [{"role": "user", "content": prompt}]
        
        print(f"Sending to DeepSeek: {messages}")  # Debug
        
        response = requests.post(
            DEEPSEEK_API_BASE,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9,
                "stream": False
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        print(f"DeepSeek API error: {e}")
        import traceback
        traceback.print_exc()
        return f"I apologize, but I encountered an error: {str(e)}"


def initialize_llm():
    """Initialize or reinitialize the LLM with DeepSeek backend"""
    global llm
    
    print(f"Initializing LLM with DeepSeek API...")
    print(f"Settings: {current_settings}")
    
    # Load tokenizer for token counting
    tokenizer = AutoTokenizer.from_pretrained("gpt2")
    
    # Create backend with DeepSeek API
    backend = APIChatBackend(
        tokenizer=tokenizer,
        send_callable=call_deepseek_api,
        name="deepseek-chat"
    )
    
    llm = CompleteFiniteMemoryLLM(
        backend=backend,
        memory_policy=current_settings['policy'],
        max_tokens=current_settings['max_tokens']
    )
    
    print("✓ LLM initialized with DeepSeek API!")


@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory('.', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('.', path)


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.json
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        if llm is None:
            initialize_llm()
        
        # For DeepSeek, we'll call the API directly with conversation history
        # to avoid the token concatenation issue
        try:
            # Build conversation messages from history
            messages = []
            
            # Add system message to force English
            messages.append({
                "role": "system",
                "content": "You are a helpful AI assistant. Always respond in English, regardless of the language used in the question."
            })
            
            for entry in llm.conversation_history[-10:]:  # Last 10 messages for context
                messages.append({
                    "role": entry["role"],
                    "content": entry["content"]
                })
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            print(f"Sending conversation to DeepSeek: {len(messages)} messages")
            
            # Call DeepSeek directly with higher token limit for full responses
            response_text = call_deepseek_direct(messages, max_tokens=2000)
            
            # Calculate tokens (rough estimate: ~4 chars per token)
            user_tokens = len(message) // 4
            assistant_tokens = len(response_text) // 4
            
            # Update conversation history
            llm.conversation_history.append({
                "role": "user", 
                "content": message, 
                "tokens": user_tokens
            })
            llm.conversation_history.append({
                "role": "assistant", 
                "content": response_text, 
                "tokens": assistant_tokens
            })
            
            # Update stats
            llm.stats.tokens_seen += user_tokens + assistant_tokens
            llm.stats.tokens_retained = sum(
                entry.get('tokens', 0) 
                for entry in llm.conversation_history
            )
            
            # Apply memory policy if needed
            if llm.stats.tokens_retained > llm.max_tokens:
                print(f"Memory limit reached: {llm.stats.tokens_retained}/{llm.max_tokens}")
                # Keep only recent messages within limit
                total_tokens = 0
                keep_from = len(llm.conversation_history)
                for i in range(len(llm.conversation_history) - 1, -1, -1):
                    total_tokens += llm.conversation_history[i].get('tokens', 0)
                    if total_tokens > llm.max_tokens:
                        keep_from = i + 1
                        break
                
                evicted = len(llm.conversation_history) - keep_from
                if evicted > 0:
                    llm.conversation_history = llm.conversation_history[keep_from:]
                    llm.stats.evictions += evicted
                    llm.stats.tokens_retained = total_tokens
                    print(f"Evicted {evicted} messages, retained {llm.stats.tokens_retained} tokens")
            
            stats = llm.stats
            
        except Exception as e:
            print(f"Direct API call failed, falling back to LLM: {e}")
            # Fallback to original method
            result = llm.chat(message)
            
            # Extract response text
            if isinstance(result, dict):
                response_text = result.get('response', str(result))
                stats = result.get('stats')
            else:
                response_text = str(result)
                stats = llm.stats
        
        # Format stats
        stats_dict = {
            'tokens_seen': stats.tokens_seen if hasattr(stats, 'tokens_seen') else 0,
            'tokens_retained': stats.tokens_retained if hasattr(stats, 'tokens_retained') else 0,
            'evictions': stats.evictions if hasattr(stats, 'evictions') else 0,
            'compression_ratio': stats.compression_ratio if hasattr(stats, 'compression_ratio') else 1.0,
            'policy_calls': stats.total_policy_calls if hasattr(stats, 'total_policy_calls') else 0
        }
        
        return jsonify({
            'response': response_text,
            'stats': stats_dict,
            'success': True
        })
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    """Get or update settings"""
    global current_settings
    
    if request.method == 'GET':
        return jsonify(current_settings)
    
    elif request.method == 'POST':
        try:
            data = request.json
            
            # Update settings
            if 'policy' in data:
                current_settings['policy'] = data['policy']
            if 'max_tokens' in data:
                current_settings['max_tokens'] = int(data['max_tokens'])
            if 'model' in data:
                current_settings['model'] = data['model']
            
            # Reinitialize LLM with new settings
            initialize_llm()
            
            return jsonify({
                'success': True,
                'settings': current_settings
            })
            
        except Exception as e:
            print(f"Error updating settings: {e}")
            return jsonify({
                'error': str(e),
                'success': False
            }), 500


@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset the conversation"""
    try:
        if llm:
            llm.reset()
        
        return jsonify({
            'success': True,
            'message': 'Conversation reset'
        })
        
    except Exception as e:
        print(f"Error resetting conversation: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@app.route('/api/memory', methods=['GET'])
def get_memory_status():
    """Get detailed memory status"""
    if llm is None:
        return jsonify({'error': 'LLM not initialized'}), 500
    
    return jsonify({
        'conversation_history_length': len(llm.conversation_history),
        'conversation_history': [
            {
                'role': entry.get('role'),
                'tokens': entry.get('tokens', 0),
                'content_preview': entry.get('content', '')[:50] + '...'
            }
            for entry in llm.conversation_history
        ],
        'stats': {
            'tokens_seen': llm.stats.tokens_seen,
            'tokens_retained': llm.stats.tokens_retained,
            'evictions': llm.stats.evictions,
            'compression_ratio': llm.stats.compression_ratio
        },
        'settings': {
            'max_tokens': llm.max_tokens,
            'policy': llm.memory_policy
        }
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get current LLM statistics"""
    try:
        if llm is None:
            return jsonify({'error': 'LLM not initialized'}), 500
        
        stats = llm.stats
        
        return jsonify({
            'tokens_seen': stats.tokens_seen if hasattr(stats, 'tokens_seen') else 0,
            'tokens_retained': stats.tokens_retained if hasattr(stats, 'tokens_retained') else 0,
            'evictions': stats.evictions if hasattr(stats, 'evictions') else 0,
            'compression_ratio': stats.compression_ratio if hasattr(stats, 'compression_ratio') else 1.0,
            'policy_calls': stats.total_policy_calls if hasattr(stats, 'total_policy_calls') else 0,
            'max_tokens': current_settings['max_tokens'],
            'policy': current_settings['policy']
        })
    except Exception as e:
        print(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Finite Memory AI - Chat Server")
    print("=" * 60)
    print("\nInitializing backend...")
    
    try:
        initialize_llm()
        print("\n" + "=" * 60)
        print("Server starting on http://localhost:8080")
        print("=" * 60)
        print("\nOpen your browser and navigate to:")
        print("  http://localhost:8080")
        print("\nPress Ctrl+C to stop the server")
        print("=" * 60 + "\n")
        
        app.run(debug=True, host='0.0.0.0', port=8080)
        
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\nError starting server: {e}")
        import traceback
        traceback.print_exc()
