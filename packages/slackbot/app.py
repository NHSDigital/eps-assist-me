import logging
import os
import json
import requests

from langchain.memory import ChatMessageHistory
from langchain_core.messages import BaseMessage

from typing import Sequence
from eps_query import EPSQuery

# === Global constants ===
USER_FEEDBACK = "feedback:"
APP_VERSION = "1.0.5"

# === Logging setup ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# === Conversation storage ===
class InMemoryConversations:
    def __init__(self) -> None:
        self.conversations: dict[str, ChatMessageHistory] = {}

    def messages(self, thread_id: str) -> Sequence[BaseMessage]:
        return self.conversations[thread_id].messages

    def history(self, thread_id: str) -> ChatMessageHistory:
        return self.conversations[thread_id]

    def exists(self, thread_id: str) -> bool:
        return thread_id in self.conversations

    def start(self, thread_id: str) -> ChatMessageHistory:
        if self.conversations.get(thread_id):
            return self.conversations[thread_id]
        self.conversations[thread_id] = ChatMessageHistory()
        return self.conversations[thread_id]


# === Core logic ===
def _run_query_with_history(history: InMemoryConversations, thread_id, query):
    conversation = history.start(thread_id)
    ai_answer = eps_query.query(query, conversation)
    conversation.add_user_message(query)
    conversation.add_ai_message(ai_answer)
    return ai_answer


def file_handling(event, message_text, thread_id, token):
    files = event.get("files", [])
    if not files:
        return message_text

    headers = {"Authorization": f"Bearer {token}"}

    for file_info in files:
        file_url = file_info.get("url_private")
        file_type = file_info.get("filetype")

        response = requests.get(file_url, headers=headers)
        if response.status_code != 200:
            logger.error({
                "chatEvent": "Failed to fetch file",
                "filetype": file_type,
                "status": response.status_code,
                "thread_id": thread_id,
            })
            continue

        content = response.text

        if file_type == "json":
            try:
                json_data = json.loads(content)
                json_string = json.dumps(json_data, indent=4)
                message_text += f"\n\nJSON File Content:\n{json_string}"
                logger.info({
                    "chatEvent": "JSON file uploaded",
                    "content": json_string,
                    "thread_id": thread_id,
                })
            except json.JSONDecodeError:
                logger.error({
                    "chatEvent": "Invalid JSON",
                    "thread_id": thread_id,
                })

        elif file_type == "text":
            message_text += f"\n\nAttached file contents:\n{content}"
            logger.info({
                "chatEvent": "Text file uploaded",
                "content": content,
                "thread_id": thread_id,
            })

        else:
            logger.error({
                "chatEvent": "Unsupported filetype",
                "filetype": file_type,
                "thread_id": thread_id,
            })

    return message_text


# === Shared objects ===
eps_query = EPSQuery()
history = InMemoryConversations()


# === Mode handlers ===
def run_local_mode():
    thread_id = "this is a test"
    query = (
        "1.6.5 “For eRD prescriptions, the dispenser must see:\n"
        "• the current issue\n"
        "• the total number of authorised issues for both the prescription and line items on the prescription.\n"
        "There is nothing we can see at prescription level that defines the current issue or the number of "
        "authorised issues (we can only see it at MedicationRequest level) "
        "Eg: Prescription number: 8F4A22-C81007-000012"
    )
    response = _run_query_with_history(history, thread_id, query)
    print(response)


def run_slack_mode():
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")

    if not bot_token or not app_token:
        raise RuntimeError("Missing SLACK_BOT_TOKEN or SLACK_APP_TOKEN environment variables.")

    app = App(token=bot_token)

    @app.event("app_mention")
    def kick_off_event(event, say, client):
        message_text = event["text"].split(" ", 1)[-1]
        thread_id = event["ts"]

        logger.info({
            "chatEvent": "initialQuestion",
            "text": message_text,
            "thread_id": thread_id
        })

        client.reactions_add(
            channel=event["channel"],
            timestamp=thread_id,
            name="eyes"
        )

        if message_text.lower() == "info":
            say({"text": f"EPS AssistMe, version: {APP_VERSION}"})
            return

        message_text = file_handling(event, message_text, thread_id, bot_token)
        response = _run_query_with_history(history, thread_id, message_text)

        say({"text": f"{response} \n\nWas this helpful?", "thread_ts": thread_id})
        say({
            "text": "Was this helpful?",
            "thread_ts": thread_id,
            "blocks": [
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Yes"},
                            "value": "yes",
                            "action_id": "resolved_button"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "No"},
                            "value": "no",
                            "action_id": "unresolved_button"
                        },
                    ],
                }
            ],
        })

        logger.info({
            "chatEvent": "initialAnswer",
            "text": response,
            "thread_id": thread_id
        })

    @app.event("message")
    def answer_subsequent_questions(event, say, client):
        thread_id = event.get("thread_ts")
        if not thread_id or not history.exists(thread_id):
            return

        message_text = event["text"]
        if message_text.lower().startswith(USER_FEEDBACK):
            logger.info({
                "chatEvent": "userFeedback",
                "text": message_text,
                "thread_id": thread_id
            })
            return

        message_text = file_handling(event, message_text, thread_id, bot_token)
        response = _run_query_with_history(history, thread_id, message_text)

        logger.info({
            "chatEvent": "followupAnswer",
            "text": response,
            "thread_id": thread_id
        })

        say({"text": response, "thread_ts": thread_id})

    @app.action("unresolved_button")
    def handle_negative_action(ack, body, say):
        ack()
        thread_id = body["container"]["thread_ts"]
        say({
            "text": (
                f'Please let us know how the answer could be improved. '
                f'Start your message with "{USER_FEEDBACK}"'
            ),
            "thread_ts": thread_id
        })
        logger.info({"chatEvent": "suboptimalAnswer", "thread_id": thread_id})

    @app.action("resolved_button")
    def handle_positive_action(ack, body, say):
        ack()
        thread_id = body["container"]["thread_ts"]
        logger.info({"chatEvent": "optimalAnswer", "thread_id": thread_id})
        say({"text": "Thank you for your feedback", "thread_ts": thread_id})

    logger.info({"chatEvent": "startEPSAssist"})
    SocketModeHandler(app, app_token).start()


# === Entry point ===
if __name__ == "__main__":
    run_local = int(os.getenv("LOCAL_MODE", 0))
    print(f"Running in local mode: {run_local}")

    if run_local == 1:
        run_local_mode()
    else:
        run_slack_mode()
