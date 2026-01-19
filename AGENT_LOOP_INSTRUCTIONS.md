# Tmux Agent Loop Instructions

Run a Claude agent in tmux that executes tasks from `prompt.md`, monitors for completion, and restarts automatically.

---

## When asked to "execute the loop" do this

### 1. Start the Agent

```bash
cd /Users/sukhdeepsingh/projects/ClaudeProjects/context-aware-whisper
PROMPT=$(cat prompt.md | tr '\n' ' ')
tmux new-session -d -s claude-agent "claude --dangerously-skip-permissions --model opus '$PROMPT'"
```

### 2. Monitor for Completion

Wait 1 minute (let agent start working), then check every 15 seconds for "TEA IS SERVED":

```bash
sleep 60; while true; do
  if tmux capture-pane -t claude-agent -p 2>/dev/null | grep -q "TEA IS SERVED"; then
    echo "Agent finished - TEA IS SERVED detected"
    break
  fi
  sleep 15
done
```

### 3. Kill and Restart

When agent finishes:

```bash
tmux kill-session -t claude-agent 2>/dev/null
sleep 1
PROMPT=$(cat prompt.md | tr '\n' ' ')
tmux new-session -d -s claude-agent "claude --dangerously-skip-permissions --model opus '$PROMPT'"
```

Then go back to step 2 (monitor).

---

## Useful Commands

| Command | Purpose |
|---------|---------|
| `tmux attach -t claude-agent` | Watch agent live |
| `tmux ls` | List tmux sessions |
| `tmux kill-session -t claude-agent` | Stop the agent |
| `ps aux \| grep claude` | Check running claude processes |

---

## Key Points

1. **Model**: Always use `--model opus`
2. **Prompt format**: Pass prompt as positional argument (no `-p` flag), flatten newlines with `tr '\n' ' '`
3. **Completion signal**: Agent prints "TEA IS SERVED" when done (configured in `prompt.md`)
4. **Initial wait**: Wait 60 seconds before monitoring to avoid false positives from previous session
5. **Check interval**: 15 seconds between checks

---

## Full Loop (Copy-Paste Ready)

```bash
cd /Users/sukhdeepsingh/projects/ClaudeProjects/context-aware-whisper

# Start agent
tmux kill-session -t claude-agent 2>/dev/null
PROMPT=$(cat prompt.md | tr '\n' ' ')
tmux new-session -d -s claude-agent "claude --dangerously-skip-permissions --model opus '$PROMPT'"
echo "Agent started"

# Monitor (run this, then repeat start+monitor when it finishes)
sleep 60; while true; do
  if tmux capture-pane -t claude-agent -p 2>/dev/null | grep -q "TEA IS SERVED"; then
    echo "Agent finished - ready to restart"
    break
  fi
  sleep 15
done
```

---

## Prompt File (`prompt.md`)

The agent reads tasks from `prompt.md`. Current format:

```
study (spec files)
study (plan files)

IMPORTANT
- implement the most important task from the implementation plan
- Generate tests
- run tests after implementation
- If test fails, fix them (don't remove)
- Run the app and check if working
- Review work
- Mark implementation done in plan and commit/push
- Once done print "TEA IS SERVED" as final words
```

Update `prompt.md` to change what the agent works on.
