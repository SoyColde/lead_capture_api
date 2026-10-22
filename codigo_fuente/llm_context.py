from collections import defaultdict
from codigo_fuente.models import ConversationMessage, Conversation
from fastapi import HTTPException
import logging

MAX_HISTORY_MESSAGES = 10

conversation_histories = defaultdict(list)

logger = logging.getLogger(__name__)

def get_or_create_conversation(db, conversation_id = None):
    # if id we look for the conversation
    if conversation_id is not None:
        conversation_id = str(conversation_id)
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

        if conversation is None:
            logger.warning("Solicitud de conversacion inexistente")
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )

        return conversation

    conversation = Conversation()

    try:
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        return conversation
    except:
        db.rollback()

def get_conversation_history(
        db,
        conversation_id: str,
        limit: int = MAX_HISTORY_MESSAGES
):
    messages = (
        db.query(ConversationMessage)
        .filter(
            ConversationMessage.conversation_id == conversation_id
        )
        .order_by(
            ConversationMessage.created_at.desc(),
            ConversationMessage.id.desc()
        )
        .limit(limit)
        .all()
    )

    # First we sort and get most recent data, then we deliver it as should be

    messages.reverse()

    return [
        {
            "role": message.role,
            "content": message.content
        }
        for message in messages
    ]

def save_conversation_turn(
        db,
        conversation_id: str,
        user_message: str,
        assistant_message: str
):
    db.add_all([
        ConversationMessage(
            conversation_id = conversation_id,
            role = "user",
            content = user_message
        ),
        ConversationMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_message
        )
    ])

    db.commit()