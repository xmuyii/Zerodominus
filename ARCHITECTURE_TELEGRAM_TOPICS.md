# Telegram Topics Architecture Guide - Trivia vs Fusion Separation

## Problem Statement
Running both Trivia and Fusion games in the same group chat causes messages to mix, making it difficult for players to track which game is which.

## Solution: Using Telegram Topics

### Option 1: **RECOMMENDED - Telegram Topics (Best Practice)**

Telegram Supergroups support **Topics** (also called Forums), which allows you to organize discussions into separate threads within a single group.

#### How to Set Up Topics:

1. **Enable Topics in Your Group:**
   - Supergroup settings → Topics → Enable Topics
   - Topics will automatically be created for categories

2. **Create Dedicated Topics:**
   - "🧠 Trivia" - For all trivia games and discussions
   - "🃏 Fusion" - For all fusion games and discussions
   - "📊 Leaderboards" - For score displays and rankings

3. **Bot Implementation with aiogram:**

```python
# Send messages to specific topics
from aiogram import types

async def send_to_trivia_topic(message_text: str):
    """Send message to Trivia topic."""
    await bot.send_message(
        chat_id=1003835925366_1,
        message_thread_id=36623,  # Topic ID for "Trivia"
        text=message_text,
        parse_mode="Markdown"
    )

async def send_to_fusion_topic(message_text: str):
    """Send message to Fusion topic."""
    await bot.send_message(
        chat_id=1003835925366_1,
        message_thread_id=36621,  # Topic ID for "Fusion"
        text=message_text,
        parse_mode="Markdown"
    )
```

#### Benefits:
✅ Complete separation of game messages  
✅ Topics persist in chat history organized by game  
✅ Each topic can have its own persistent messages  
✅ Easy for players to mute one topic but keep another active  
✅ Native Telegram feature, no external tools needed  
✅ Topics show unread count per game  

#### Implementation in Your Bot:

Add topic IDs to your configuration:

```python
# config.py or main.py
TRIVIA_TOPIC_ID = 36623  # Get from group settings
FUSION_TOPIC_ID = 36621  # Get from group settings
LEADERBOARDS_TOPIC_ID = 36626

# Update trivia_game_loop to use topic:
async def trivia_game_loop(chat_id: int):
    # ... existing code ...
    await bot.send_message(
        chat_id,
        "🧠 *TRIVIA GAME STARTING!*\n...",
        parse_mode="Markdown",
        message_thread_id=TRIVIA_TOPIC_ID  # Add this
    )
```

---

## Option 2: **Alternative - Separate Groups**

If you prefer not to use Topics, run the games in different groups:

- **Group 1:** "The64 - Trivia" (for trivia only)
- **Group 2:** "The64 - Fusion" (for fusion only)

#### Disadvantages:
❌ Players need to switch between groups  
❌ Fragmented community discussion  
❌ More complex bot management  
❌ Harder to announce game changes to everyone  

---

## Option 3: **Current Approach - Clean Chat Management (Current Implementation)**

Your bot currently:
1. ✅ **Deletes player answer messages** in trivia (keeps chat clean)
2. ✅ **Edits one persistent dashboard** instead of sending multiple messages
3. ✅ **Uses emojis to distinguish** Trivia (🧠) vs Fusion (🃏)

This mitigates the mixing problem but Topic-based separation is still cleaner.

---

## Getting Topic IDs

When Topics are enabled, you can get the topic ID from:

```python
# In your message handler:
if message.message_thread_id:
    print(f"Message sent to topic ID: {message.message_thread_id}")
```

Or retrieve them from Telegram:

```bash
# Get group info via Telegram Bot API
curl "https://api.telegram.org/bot<TOKEN>/getChat?chat_id=<GROUP_ID>"
```

---

## Recommended Final Architecture

```
The64 - Main Group (Supergroup with Topics)
├── Topic 1: 🧠 Trivia
│   ├── All trivia questions
│   ├── Trivia scoreboard (persistent/edited)
│   └── Trivia leaderboards (!weekly_trivia, !alltime_trivia)
├── Topic 2: 🃏 Fusion
│   ├── All fusion words/rounds
│   ├── Fusion scoreboard (persistent/edited)
│   └── Fusion leaderboards (!weekly_fusion, !alltime_fusion)
└── Topic 3: 📊 General Leaderboards
    ├── Combined rankings
    └── Admin announcements
```

---

## Implementation Steps

### Step 1: Create Topics (Manual)
1. Go to group → Info → Topics
2. Create "🧠 Trivia", "🃏 Fusion", "📊 Leaderboards"
3. Note the Topic IDs from the URL or bot API

### Step 2: Update Your Config
```python
# config.py
GAME_TOPICS = {
    "trivia": 36623,      # Topic ID for trivia
    "fusion": 36621,      # Topic ID for fusion
    "leaderboards": 36626  # Topic ID for leaderboards
}
```
TRIVIA_TOPIC_ID = 36623  # Get from group settings
FUSION_TOPIC_ID = 36621  # Get from group settings
LEADERBOARDS_TOPIC_ID = 36626
### Step 3: Update Bot Functions
```python
async def send_trivia_message(chat_id, text):
    await bot.send_message(
        chat_id, text,
        message_thread_id=GAME_TOPICS["trivia"],
        parse_mode="Markdown"
    )

async def send_fusion_message(chat_id, text):
    await bot.send_message(
        chat_id, text,
        message_thread_id=GAME_TOPICS["fusion"],
        parse_mode="Markdown"
    )
```

---

## Advantages of Topics Over Current Implementation

| Feature | Current | With Topics |
|---------|---------|-------------|
| Message separation | ⚠️ Emoji-based, can still mix | ✅ Complete isolation |
| History organization | 🔄 All messages in one thread | ✅ Organized by game type |
| Unread tracking | 🔄 Single notification | ✅ Per-topic notifications |
| Player preference | ❌ Can't mute specific game | ✅ Can mute one topic, watch another |
| Persistent messages | ✅ Working well | ✅ Even more organized |
| Scalability | 🔄 OK for 2 games | ✅ Scales to many games |

---

## Next Steps

1. **Enable Topics in your group** (Supergroup only, not regular groups)
2. **Create 2-3 dedicated topics** for different games
3. **Update bot to use `message_thread_id`** parameter
4. **Test game flows** in each topic separately
5. **Update help text** to inform players about topics

---

## Troubleshooting

**"Topics not showing up?"**
- Make sure group is a **Supergroup** (not regular group)
- Request admin rights in group settings
- Topics → Enable

**"What if I don't have admin rights?"**
- Ask group owner to enable Topics
- Request admin role for bot
- Bot needs `manage_topics` permission

**"Can I still use one message handler?"**
- Yes! Your current `on_group_message` handler works fine with topics
- Just add `message_thread_id` to `send_message()` calls

---

## Example: Updated Trivia Game Loop with Topics

```python
TRIVIA_TOPIC_ID = 12

async def trivia_game_loop(chat_id: int):
    # ... existing setup ...
    
    # Send intro message to trivia topic
    await bot.send_message(
        chat_id,
        "🧠 *TRIVIA GAME STARTING!*\n...",
        parse_mode="Markdown",
        message_thread_id=TRIVIA_TOPIC_ID
    )
    
    # Send persistent scoreboard to trivia topic
    placeholder_msg = await bot.send_message(
        chat_id,
        "📊 *SCOREBOARD*\n...",
        parse_mode="Markdown",
        message_thread_id=TRIVIA_TOPIC_ID
    )
    
    # Edit scoreboard after each question
    await bot.edit_message_text(
        board_text,
        chat_id=chat_id,
        message_id=dashboard_message_id,
        parse_mode="Markdown"
        # message_thread_id not needed for edits (already in topic)
    )
```

---

## Summary

**Best Practice Answer:**
> Use **Telegram Topics** for complete separation. Enable Topics in your Supergroup, create "🧠 Trivia" and "🃏 Fusion" topics, then send game messages to their respective topics using `message_thread_id`. This is the cleanest, most scalable solution that leverages native Telegram features.

---

**For More Info:**
- [Telegram Topics Documentation](https://telegram.org/blog/topics)
- [aiogram send_message with message_thread_id](https://docs.aiogram.dev/en/latest/api/types/message.html)
