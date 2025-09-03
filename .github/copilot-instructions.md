# Discord Bot (dcbot) - Gray Zone Warfare Wiki Bot

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

This is a Python Discord bot that provides Gray Zone Warfare Wiki functionality through interactive Discord channels. The bot creates temporary channels for users to browse game information, with automatic cleanup and comprehensive logging.

## Working Effectively

### Bootstrap and Setup
**CRITICAL**: Always run these setup commands in the repository root (`/home/runner/work/dcbot/dcbot`):

1. **Install Python dependencies** (takes ~30 seconds, NEVER CANCEL):
   ```bash
   pip3 install discord.py python-dotenv
   ```

2. **Install development tools** (takes ~20 seconds, NEVER CANCEL):
   ```bash
   pip3 install flake8
   ```

3. **Verify installation**:
   ```bash
   python3 -c "import discord; import dotenv; print('Dependencies installed successfully')"
   ```

### Environment Configuration
**CRITICAL**: The bot requires a Discord token in `.env` file:
- The `.env` file contains `DISCORD_TOKEN=<token>`
- **NEVER commit real Discord tokens to version control**
- For testing imports/syntax: use any placeholder value
- For actual bot operation: requires valid Discord bot token from Discord Developer Portal

### Running the Bot
**WARNING**: Bot runs indefinitely once started. Use timeouts for testing.

1. **Test bot imports and startup** (safe for validation):
   ```bash
   cd /home/runner/work/dcbot/dcbot
   timeout 10s python3 bot.py || echo "Expected timeout - bot runs indefinitely"
   ```

2. **Production run** (requires valid token and network access):
   ```bash
   cd /home/runner/work/dcbot/dcbot
   python3 bot.py
   ```
   - Bot will attempt to connect to Discord
   - Connection failures in sandboxed environments are expected
   - In production: bot runs until manually stopped

### Code Quality and Linting
**ALWAYS run linting before committing changes**:

```bash
cd /home/runner/work/dcbot/dcbot
flake8 bot.py --count --statistics
```

**Known linting issues** (do not fix unless related to your task):
- 245 total issues including line length violations (E501)
- Whitespace and formatting issues (W291, W293)
- Some unused imports and global variables
- Code functions correctly despite style violations

## Project Structure

### Repository Root (`/home/runner/work/dcbot/dcbot`)
```
.
├── .env                 # Discord token (sensitive)
├── .git/               # Git repository
├── .github/            # GitHub configuration (created for instructions)
│   └── copilot-instructions.md
├── bot.py              # Main bot code (787 lines)
├── config.json         # Bot configuration (log channel setup)
└── wiki.json           # Gray Zone Warfare game data
```

### Key Files
- **`bot.py`**: Main Discord bot implementation
  - 787 lines of Python code
  - Uses discord.py library with async/await patterns
  - Implements command handlers, UI interactions, logging
  - Contains temporary channel management and cleanup logic

- **`.env`**: Environment variables
  - Contains `DISCORD_TOKEN=<token>`
  - Required for bot authentication

- **`config.json`**: Bot runtime configuration
  - `LOG_CHANNEL_ID`: Discord channel for bot logs
  - `SETUP_COMPLETE`: Setup status flag

- **`wiki.json`**: Game data (2.7KB)
  - Contains categorized Gray Zone Warfare information
  - Weapons, missions, and other game content
  - Used by bot for wiki lookups

## Validation Scenarios

**ALWAYS test these scenarios after making changes to verify functionality**:

### 1. Basic Import and Startup Validation
```bash
cd /home/runner/work/dcbot/dcbot
python3 -c "
try:
    import bot
    print('✓ Bot imports successfully')
except Exception as e:
    print(f'✗ Import failed: {e}')
"
```

### 2. Dependency Validation
```bash
cd /home/runner/work/dcbot/dcbot
python3 -c "
import discord
import json
import os
from dotenv import load_dotenv
import asyncio
import logging
from collections import deque
print('✓ All dependencies available')
"
```

### 3. Configuration File Validation
```bash
cd /home/runner/work/dcbot/dcbot
python3 -c "
import json
with open('config.json', 'r') as f:
    config = json.load(f)
    print(f'✓ Config loaded: {config}')
with open('wiki.json', 'r') as f:
    wiki = json.load(f)
    print(f'✓ Wiki data loaded: {len(wiki[\"categories\"])} categories')
"
```

### 4. Bot Startup Test (Network-Safe)
```bash
cd /home/runner/work/dcbot/dcbot
timeout 10s python3 bot.py 2>&1 | head -10 || echo "✓ Bot startup process initiated"
```

**Expected outcomes**:
- Bot should attempt Discord login
- Network connection failures are normal in sandboxed environments
- Bot would run indefinitely with proper network access
- PyNaCl warning about voice support is expected and normal

## Bot Functionality Overview

### Core Features
1. **Wiki Commands**:
   - `!wiki` - Opens category selection menu in temporary channel
   - `!wiki ara <query>` or `!wiki search <query>` - Search wiki content

2. **Temporary Channel Management**:
   - Creates private channels for each user's wiki session
   - Automatic cleanup after 3 minutes of inactivity
   - Manual cleanup via "Kapat" (Close) button

3. **Discord Logging**:
   - Sends bot activity logs to configured Discord channel
   - Automatic log buffering and periodic sending
   - Color-coded log levels with ANSI formatting

4. **Server Setup**:
   - Automatic setup flow for new Discord servers
   - Log channel creation and configuration
   - `!setlogchannel` command for manual setup

### User Interaction Flow
1. User runs `!wiki` command
2. Bot creates temporary private channel
3. Bot sends category selection menu
4. User selects category → item selection menu appears
5. User selects item → detailed information displayed
6. Channel auto-deletes after 3 minutes OR user clicks close button

## Common Development Tasks

### Adding New Wiki Content
1. Edit `wiki.json` with new categories/items
2. Follow existing JSON structure:
   ```json
   {
     "categories": [
       {
         "name": "Category Name",
         "description": "Category description",
         "items": [
           {
             "title": "Item Title",
             "description": "Item description",
             "data": [["Key", "Value"], ["Key2", "Value2"]]
           }
         ]
       }
     ]
   }
   ```
3. Test with validation scenario #3 above

### Modifying Bot Commands
1. Locate command handlers in `bot.py` (search for `@bot.command` or `@bot.group`)
2. Commands use discord.py's commands extension
3. Always test import validation after changes
4. Run linting to check for new issues

### Debugging Bot Issues
1. **Check logs**: Bot sends detailed logs to configured Discord channel
2. **Console output**: Run bot with timeout to see startup logs
3. **Configuration**: Verify `config.json` and `.env` files exist and are valid
4. **Permissions**: Bot needs channel creation/management permissions in Discord

### Code Style Guidelines
- Current code has 245 linting violations (do not fix unless required)
- Line length limit: 79 characters (frequently violated in existing code)
- Use async/await patterns for Discord operations
- Follow existing naming conventions (Turkish comments/messages)

## Technical Notes

### Dependencies
- **Python 3.12.3**: Tested and working
- **discord.py 2.6.3**: Main Discord library
- **python-dotenv 1.1.1**: Environment variable loading
- **flake8 7.3.0**: Code linting (development)

### Performance Characteristics
- **Import time**: < 1 second
- **Dependency installation**: ~30 seconds
- **Bot startup**: < 5 seconds to login attempt
- **Runtime**: Indefinite (until stopped)
- **Memory usage**: Minimal for a Discord bot

### Network Requirements
- Bot requires internet access to Discord API
- Fails in sandboxed environments (expected)
- Uses discord.com:443 for all Discord communication

### Security Considerations
- Discord token in `.env` is sensitive
- Bot has channel creation/deletion permissions
- Temporary channels are private to requesting user
- Automatic cleanup prevents channel spam

## Error Handling

### Common Issues and Solutions

1. **Import Error**: Missing dependencies
   ```bash
   pip3 install discord.py python-dotenv
   ```

2. **Connection Error**: Network restrictions (in sandbox)
   - Expected behavior in restricted environments
   - Verify token and network access in production

3. **Permission Error**: Bot lacks Discord permissions
   - Verify bot has "Manage Channels" permission
   - Check role hierarchy in Discord server

4. **JSON Error**: Corrupted config/wiki files
   - Validate JSON syntax
   - Restore from git if needed

### Expected Warnings
- "PyNaCl is not installed, voice will NOT be supported" - NORMAL
- DNS/Connection errors in sandboxed environments - EXPECTED
- Flake8 linting violations - KNOWN ISSUES (245 total)

## Timing and Timeout Guidelines

**CRITICAL**: Always use appropriate timeouts for testing:
- **Dependency installation**: Set timeout to 60+ seconds, typically takes 30 seconds
- **Bot startup testing**: Use 10-15 second timeout, bot runs indefinitely otherwise
- **Import validation**: Should complete in < 5 seconds
- **File operations**: Immediate (< 1 second)

**NEVER CANCEL** long-running operations without explicit timeout handling.

Remember: This bot is designed to run continuously in production - all testing should use timeouts to prevent indefinite execution during development.