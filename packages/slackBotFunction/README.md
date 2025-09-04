# Slack Bot Function

AWS Lambda function that handles Slack interactions for the EPS Assist Me bot. Provides AI-powered responses to user queries about the NHS EPS API using Amazon Bedrock Knowledge Base.

## Architecture

- **Slack Bolt Framework**: Handles Slack events and interactions
- **Amazon Bedrock**: RAG-based AI responses using knowledge base
- **DynamoDB**: Session management and feedback storage
- **Async Processing**: Self-invoking Lambda for long-running AI queries

## User Interaction Patterns

### Starting Conversations

**Public Channels** - Mention the bot:
```
#general channel:
User: "@eps-bot What is EPS API?"
Bot: "EPS API is the Electronic Prescription Service..."
```

**Direct Messages** - Send message directly:
```
DM to @eps-bot:
User: "How do I authenticate with EPS?"
Bot: "Authentication requires..."
```

### Follow-up Questions

**In Channel Threads** - No @mention needed after initial conversation:
```
#general channel thread:
User: "@eps-bot What is EPS API?" ← Initial mention required
Bot: "EPS API is..."
User: "Can you explain more about authentication?" ← No mention needed
Bot: "Authentication works by..."
User: "What about error handling?" ← Still no mention needed
```

**In DMs** - Continue messaging naturally:
```
DM conversation:
User: "How do I authenticate?"
Bot: "Use OAuth 2.0..."
User: "What scopes do I need?" ← Natural follow-up
Bot: "Required scopes are..."
```

### Providing Feedback

**Button Feedback** - Click Yes/No on bot responses:
```
Bot: "EPS API requires OAuth authentication..."
     [Yes] [No] ← Click buttons
```

**Text Feedback** - Use "feedback:" prefix anytime (applies to most recent bot response):
```
Bot: "EPS API requires OAuth authentication..."
User: "feedback: This was very helpful, thanks!"
User: "feedback: Could you add more error code examples?"
User: "feedback: The authentication section needs clarification"
```

## Handler Architecture

- **`mention_handler`**: Processes @mentions in public channels
- **`dm_message_handler`**: Handles direct messages to the bot  
- **`thread_message_handler`**: Manages follow-up replies in existing threads
- **`feedback_handler`**: Processes Yes/No button clicks

### Conversation Flow
```
Channel:
User: "@eps-bot What is EPS?"           ← mention_handler
Bot: "EPS is..." [Yes] [No]

├─ User clicks [Yes]                    ← feedback_handler
│  Bot: "Thank you for your feedback."
│
├─ User clicks [No]                     ← feedback_handler
│  Bot: "Please provide feedback:"
│  User: "feedback: Need more examples" ← thread_message_handler
│  Bot: "Thank you for your feedback."
│
└─ User: "Tell me more"                 ← thread_message_handler
   Bot: "More details..." [Yes] [No]

DM:
User: "How do I authenticate?"          ← dm_message_handler
Bot: "Use OAuth..." [Yes] [No]

├─ User clicks [Yes/No]                 ← feedback_handler
│  Bot: "Thank you for your feedback."
│  User: "feedback: Could be clearer"   ← dm_message_handler
│  Bot: "Thank you for your feedback."
└─ User: "What scopes?"                 ← dm_message_handler
```

## Conversation Flow Rules

1. **Public channels**: Must @mention bot to start conversation
2. **Threads**: After initial @mention, no further mentions needed
3. **DMs**: No @mention required, direct messaging
4. **Feedback restrictions**: 
   - Only available on most recent bot response
   - Cannot vote twice on same message (Yes/No)
   - Cannot rate old messages after conversation continues
5. **Text feedback**: Use "feedback:" prefix anytime in conversation (multiple comments allowed)
   - Feedback applies to the most recent bot message in the conversation

## Technical Implementation

### Event Processing Flow
```
Slack Event → Handler (3s timeout) → Async Lambda → Bedrock → Response
```

### Data Storage
- **Sessions**: 30-day TTL for conversation continuity
- **Q&A Pairs**: 90-day TTL for feedback correlation
- **Feedback**: 90-day TTL for analytics
- **Event Dedup**: 1-hour TTL for retry handling

### Privacy Features
- **Automatic cleanup**: Q&A pairs without feedback are deleted when new messages arrive (reduces data retention by 70-90%)
- **Data minimisation**: Configurable TTLs automatically expire old data
- **Secure credentials**: Slack tokens stored in AWS Parameter Store

### Feedback Protection
- **Latest message only**: Users can only rate the most recent bot response in each conversation
- **Duplicate prevention**: Users cannot vote twice on the same message (Yes/No buttons)
- **Multiple text feedback**: Users can provide multiple detailed comments using "feedback:" prefix

## Configuration

### Environment Variables
- `SLACK_BOT_TOKEN_PARAMETER`: Parameter Store path for bot token
- `SLACK_SIGNING_SECRET_PARAMETER`: Parameter Store path for signing secret
- `SLACK_BOT_STATE_TABLE`: DynamoDB table name
- `KNOWLEDGEBASE_ID`: Bedrock Knowledge Base ID
- `RAG_MODEL_ID`: Bedrock model ARN
- `GUARD_RAIL_ID`: Bedrock guardrail ID

### DynamoDB Schema
```
Primary Key: pk (partition key), sk (sort key)

Sessions:     pk="thread#C123#1234567890", sk="session"
Q&A Pairs:    pk="qa#thread#C123#1234567890#1234567891", sk="turn"
Feedback:     pk="feedback#thread#C123#1234567890#1234567891", sk="user#U123"
Text Notes:   pk="feedback#thread#C123#1234567890#1234567891", sk="user#U123#note#1234567892"
```

## Development

### Local Testing
```bash
# Install dependencies
npm install

# Run tests
npm test

# Deploy to dev environment
make cdk-deploy STACK_NAME=your-dev-stack
```

### Debugging
- Check CloudWatch logs for Lambda execution details
- Monitor DynamoDB for session and feedback data

## Monitoring

- **CloudWatch Logs**: `/aws/lambda/{stack-name}-SlackBotFunction`
- **DynamoDB Metrics**: Built-in AWS metrics for table operations

**Note**: No automated alerts configured. Uses AWS built-in metrics and manual log review.
