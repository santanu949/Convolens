import sys
import json
sys.path.append('backend')
from app import create_app

app = create_app()
with app.app_context():
    from storage import db
    from services.persona import extract_persona_for_conversation
    from services.synthesizer import synthesize_answer
    from services.retriever import retriever
    
    # Force retriever to build index if empty
    if not retriever.is_ready:
        retriever.build_index()

    print("\n--- Persona for Conversation 0 ---")
    try:
        persona = extract_persona_for_conversation(0)
        print(json.dumps(persona, indent=2))
    except Exception as e:
        print("Error getting persona:", e)
        persona = None
        
    print("\n--- Chatbot Answer ---")
    try:
        retrieved = retriever.search('What kind of person is this user?', conversation_id=0)
        ans = synthesize_answer('What kind of person is this user?', retrieved, persona)
        print(ans['answer'])
    except Exception as e:
        print("Error getting chat:", e)
