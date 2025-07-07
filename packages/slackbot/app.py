import logging
import os
import json
import requests

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from langchain.memory import ChatMessageHistory
from langchain_core.messages import BaseMessage

from typing import Sequence
from opencensus.ext.azure.log_exporter import AzureLogHandler
from eps_query import EPSQuery

USER_FEEDBACK = "feedback:"
APP_VERSION = "1.0.5"

# Grab the API keys
bot_token = os.environ["SLACK_BOT_TOKEN"]
app_token = os.environ["SLACK_APP_TOKEN"]
azure_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.addHandler(AzureLogHandler())


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


app = App(token=bot_token)
eps_query = EPSQuery()
history = InMemoryConversations()


@app.event("app_mention")
def kick_off_event(event, say, client):
    message_text = event["text"]
    index_of_space = message_text.find(" ")
    message_text = message_text[index_of_space + 1:]
    thread_id = event["ts"]

    logger.info(
        {"chatEvent": "initialQuestion", "text": message_text, "thread_id": thread_id}
    )

    client.reactions_add(
        channel=event["channel"],
        timestamp=thread_id,
        name="eyes"
    )

    if message_text.lower() == "info":
        say({"text": f"EPS AssistMe, version: {APP_VERSION}"})
        return

    message_text = file_handling(event, message_text, thread_id)

    response = _run_query_with_history(history, thread_id, message_text)

    # Push the answer back to the user.
    answer_text = f"{response} \n\nWas this helpful?"
    say({"text": answer_text, "thread_ts": thread_id})

    # Send a message with buttons asking for feedback
    say(
        {
            "text": "Was this helpful?",
            "thread_ts": thread_id,
            "blocks": [
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Yes",
                            },
                            "value": "yes",
                            "action_id": "resolved_button",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "No",
                            },
                            "value": "no",
                            "action_id": "unresolved_button",
                        },
                    ],
                },
            ],
        },
    )
    logger.info(
        {"chatEvent": "initialAnswer", "text": response, "thread_id": thread_id}
    )


@app.event("message")
def answer_subsequent_questions(event, say, client):
    if "thread_ts" not in event:
        return
    thread_id = event["thread_ts"]

    if not history.exists(thread_id):
        # this should ensure the bot doens't respond to threads it didn't start.
        return

    message_text: str = event["text"]
    if message_text.lower().startswith(USER_FEEDBACK):
        logger.info(
            {"chatEvent": "userFeedback", "text": message_text, "thread_id": thread_id}
        )
        return

    message_text = file_handling(event, message_text, thread_id)

    response = _run_query_with_history(history, thread_id, message_text)
    logger.info(
        {"chatEvent": "followupAnswer", "text": response, "thread_id": thread_id}
    )
    say(
        {
            "text": response,
            "thread_ts": thread_id,
        }
    )


@app.action("unresolved_button")
def handle_negative_action(ack, body, say):
    ack()
    thread_id = body["container"]["thread_ts"]
    say(
        {
            "text": f'Please let us know how the answer could be improved. Start your message with "{USER_FEEDBACK}"',
            "thread_ts": thread_id,
        }
    )

    logger.info({"chatEvent": "suboptimalAnswer", "thread_id": thread_id})


@app.action("resolved_button")
def handle_positive_action(ack, body, say):
    ack()
    thread_id = body["container"]["thread_ts"]
    logger.info({"chatEvent": "optimalAnswer", "thread_id": thread_id})
    say(
        {
            "text": "Thank you for your feedback",
            "thread_ts": thread_id,
        }
    )


def file_handling(event, message_text, thread_id):
    # Will require the 'files:read' scope adding to the Slack bot.
    files = event.get("files", [])
    if files:
        for file_info in files:
            # Handle JSON
            if file_info.get("filetype") == "json":
                file_url = file_info.get("url_private")
                headers = {"Authorization": f"Bearer {app.client.token}"}
                response = requests.get(file_url, headers=headers)
                if response.status_code == 200:
                    file_content = response.text
                    json_data = json.loads(file_content)
                    # Convert JSON data to string and add to the combined text
                    json_string = json.dumps(json_data, indent=4)
                    message_text += f"\n\nJSON File Content:\n{json_string}"
                    logger.info(
                        {
                            "chatEvent": "JSON file uploaded",
                            "content": json_string,
                            "thread_id": thread_id,
                        }
                    )
                else:
                    status_code_error = response.status_code
                    logger.error(
                        {
                            "chatEvent": "Failed to collect JSON file",
                            "response": status_code_error,
                            "thread_id": thread_id,
                        }
                    )
            # Handle txt files
            elif file_info.get("filetype") == "text":
                file_url = file_info.get("url_private")
                headers = {"Authorization": f"Bearer {app.client.token}"}
                response = requests.get(file_url, headers=headers)
                if response.status_code == 200:
                    file_content = response.text
                    message_text += f"Attached file contents: {file_content}"
                    logger.info(
                        {
                            "chatEvent": "Text file uploaded",
                            "content": file_content,
                            "thread_id": thread_id,
                        }
                    )
                else:
                    status_code_error = response.status_code
                    logger.error(
                        {
                            "chatEvent": "Failed to collect text file",
                            "response": status_code_error,
                            "thread_id": thread_id,
                        }
                    )
            # Fail on other file types
            else:
                filetype = file_info.get("filetype")
                logger.error(
                    {
                        "chatEvent": "Invalid file extension",
                        "extension": filetype,
                        "thread_id": thread_id,
                    }
                )
    return message_text


def _run_query_with_history(history: InMemoryConversations, thread_id, query):

    conversation = history.start(thread_id)

    ai_answer = eps_query.query(query, conversation)

    conversation.add_user_message(query)
    conversation.add_ai_message(ai_answer)

    return ai_answer


if __name__ == "__main__":

    run_local = os.getenv("LOCAL_MODE", 0)

    if int(run_local) == 1:
        eps_query = EPSQuery()
        history = InMemoryConversations()

        thread_id = "this is a test"

        query = """1.6.5 “For eRD prescriptions, the dispenser must see:
• the current issue
• the total number of authorised issues for both the prescription and line items on the prescription.
There is nothing we can see at prescription level that defines the current issue or the number of authorised issues (we can only see it at MedicationRequest level) Eg: Prescription number: 8F4A22-C81007-000012"""

        response = _run_query_with_history(history, thread_id, query)

        print(response)

    else:

        logger.info({"chatEvent": "startEPSAssist"})
        SocketModeHandler(app, app_token).start()
