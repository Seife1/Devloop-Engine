# 🚀 LearnLoop Universal Integration

**No more copying files!** LearnLoop now works in ANY IDE/terminal automatically.

## 🔧 One-Command Setup

```bash
# In your project directory
learnloop integrate --all
```

This automatically:
1. ✅ Detects your IDE (VS Code, Cursor, Claude, WindSurf, Zed)
2. ✅ Configures MCP settings
3. ✅ Adds LearnLoop rules
4. ✅ Creates terminal shortcuts
5. ✅ Sets up environment aliases

## 🎯 How It Works

### For IDEs:
```bash
# Auto-detects and configures
learnloop integrate --ide auto

# Or specify IDE
learnloop integrate --ide vscode
learnloop integrate --ide cursor
learnloop integrate --ide claude
```

### For Terminal:
```bash
# Creates shortcut commands
learnloop integrate --terminal

# Now use:
learnloop-tools briefing      # Get session update
learnloop-tools start-session # Start work session  
learnloop-tools review        # Review knowledge
learnloop-tools dashboard     # Open dashboard
```

### Environment Aliases:
```bash
# Source environment (adds aliases)
source .learn/environment.sh  # Linux/Mac
. .\learn\LearnLoop.ps1       # Windows

# Now use:
llb  # Get briefing (alias)
llr  # Start review
lld  # Open dashboard
```

## 📋 IDE Support

| IDE | Auto-detection | MCP Config | Rules Integration |
|-----|----------------|------------|-------------------|
| VS Code | ✅ | ✅ | ✅ |
| Cursor | ✅ | ✅ | ✅ |
| Claude Desktop | ✅ | ✅ | ✅ |
| WindSurf | ✅ | ✅ | ✅ |
| Zed | ✅ | ✅ | ✅ |
| Any Terminal | ✅ | ✅ | ✅ |

## 🚀 Quick Start (Any Project)

```bash
# 1. Navigate to your project
cd your-project

# 2. Initialize LearnLoop
learnloop init --integrate

# OR manually:
learnloop init
learnloop integrate --all

# 3. Work with AI as usual
#    - AI writes code
#    - You commit: git commit -m "AI did X"
#    - LearnLoop tracks automatically

# 4. Get insights
learnloop-tools briefing    # Terminal
llb                         # Alias (after sourcing)
# OR use IDE's AI with MCP integration
```

## 🔍 What Gets Created

### IDE Configuration:
- **VS Code/Zed**: `.vscode/settings.json` with MCP config
- **Cursor**: `.cursorrules` with LearnLoop rules
- **Claude**: `CLAUDE.md` with LearnLoop rules
- **WindSurf**: `.windsurfrules` with LearnLoop rules
- **Generic**: `.learnloop_rules.md` (works anywhere)

### Terminal Tools:
- `learnloop-tools` - Command wrapper (Linux/Mac/Windows)
- `.learn/environment.sh` - Shell aliases
- `.learn/LearnLoop.ps1` - PowerShell aliases

## 🎮 Usage Examples

### From Terminal:
```bash
# Start work session
learnloop-tools start-session "Implement auth" "auth.py,models.py"

# Get daily update
learnloop-tools briefing

# Review what you've learned
learnloop-tools review

# Register knowledge
echo '{"key":"jwt-auth","title":"JWT Authentication","summary":"Implement JWT auth in FastAPI","files":["auth.py"]}' | learnloop-tools register
```

### From IDE (after integration):
1. **Session Start**: AI calls `get_session_briefing` automatically
2. **Architecture**: AI calls `get_project_tour` for walkthroughs
3. **Work**: AI calls `start_skill_session` before coding
4. **Decisions**: AI calls `log_decision` for alternatives
5. **After Commits**: AI calls `ingest_queue` to track work

## 🔄 Update Integration

```bash
# Update if LearnLoop changes
learnloop integrate --force

# Add new IDE support
learnloop integrate --ide new-ide

# Just terminal tools
learnloop integrate --terminal
```

## ❓ Troubleshooting

**IDE not detecting?**
```bash
# Force specific IDE
learnloop integrate --ide vscode --force

# Check if config created
ls -la .vscode/settings.json  # VS Code
cat .cursorrules              # Cursor
```

**Terminal tools not working?**
```bash
# Make executable (Linux/Mac)
chmod +x .learn/tools.sh

# Add to PATH temporarily
export PATH="$PATH:$(pwd)/.learn"

# Or use full path
./.learn/tools.sh briefing
```

**MCP not working in IDE?**
1. Restart IDE after integration
2. Check IDE supports MCP servers
3. Verify `learnloop` command works in terminal

## 🎯 The Goal

**Zero friction, maximum learning.** You focus on building with AI, LearnLoop handles:
- Tracking what AI builds
- Reinforcing what you learn
- Showing progress
- Preparing you to explain your code

No manual file copying. No complex setup. Just `learnloop integrate --all` and start learning! 🚀
